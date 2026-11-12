"""
CME -- Diagnostic 360 degres de la perte de trafic sur la page PILIER du
sous-silo "Contrat Electricite" :
  https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/attestation-de-contrat-delectricite/

Demande operateur explicite (12/11/2026) : comprendre pourquoi cette page a
perdu du trafic. C'est la page pilier reference dans LIENS_PILIERS_SOUS_SILO
(pipeline.py) -- chaque nouvel article "Contrat Electricite" est cense lui
inserer un lien en tout debut de contenu via inserer_lien_pilier().

LECTURE SEULE -- aucune ecriture, aucune correction. Regroupe en un seul
script (pour un seul aller-retour via le pont GitHub Actions) :
  1. Identite de la page (historique_publications) + verification que l'URL
     vivante correspond bien a celle stockee (pas de changement de slug).
  2. Statut technique live (code HTTP, redirections, noindex, canonical).
  3. Tendance GSC (clics/impressions/position) mensuelle sur 12 mois puis
     hebdomadaire sur les 16 dernieres semaines, pour reperer QUAND la
     chute a eu lieu et si elle est brutale ou progressive.
  4. Tendance GA4 (sessions) sur la meme fenetre.
  5. Top requetes de la page AVANT (semaines -16 a -9) vs APRES (semaines
     -8 a -1) pour isoler la/les requetes qui ont decroche.
  6. Cannibalisation : pour les requetes historiques de la page, toutes les
     pages du site qui s'y disputent le classement, et leur part respective
     avant/apres -- une autre page du site a-t-elle pris le relais ?
  7. Etat d'indexation Google si une ligne existe pour cette URL
     (04_pipeline_seo.indexation_google -- rempli manuellement, peut etre
     absent/perime).
  8. Maillage interne : combien d'articles publies pointent reellement vers
     cette page (scan de TOUT le contenu publie, pas un echantillon), avec
     un focus sur les articles "Contrat Electricite" qui devraient tous le
     faire via inserer_lien_pilier().
"""
import sys
import os
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"Import de pipeline/pipeline.py impossible : {e}")

WP_URL = "https://www.comprendre-mon-energie.fr"
PAGE_URL = f"{WP_URL}/electricite/contrat-electricite/attestation-de-contrat-delectricite/"
PAGE_PATH = "/electricite/contrat-electricite/attestation-de-contrat-delectricite/"
LIKE_PATTERN = "%attestation-de-contrat-delectricite%"
TIMEOUT = 20


def section(titre):
    print("\n" + "=" * 100)
    print(titre)
    print("=" * 100)


def run_sql(client_bq, titre, sql, params=None):
    section(titre)
    try:
        job_config = None
        if params:
            from google.cloud import bigquery
            job_config = bigquery.QueryJobConfig(query_parameters=params)
        df = client_bq.query(sql, job_config=job_config).to_dataframe()
        if df.empty:
            print("  (0 ligne)")
        else:
            print(df.to_string(index=False))
        return df
    except Exception as e:
        print(f"  ERREUR SQL : {e}")
        return None


# ----------------------------------------------------------------------
# 1. Identite + historique_publications
# ----------------------------------------------------------------------
def etape_1_identite(client_bq):
    df = run_sql(
        client_bq,
        "1. Identite de la page (historique_publications)",
        f"""
        SELECT post_id, date_publication, silo, sous_silo_strategique,
               titre, mot_cle, url_wp, run_id, image_id
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE url_wp LIKE '{LIKE_PATTERN}'
        ORDER BY date_publication
        """,
    )
    if df is not None and not df.empty:
        print(f"\n  -> {len(df)} ligne(s) trouvee(s) pour cette URL dans historique_publications.")
        if len(df) > 1:
            print("  ATTENTION : plusieurs lignes pour la meme URL -- a examiner (republication/doublon ?).")
    else:
        print("\n  ATTENTION : aucune ligne dans historique_publications pour cette URL -- "
              "vérifier si elle a été publiée par un autre mécanisme (pilier historique, page manuelle).")
    return df


# ----------------------------------------------------------------------
# 2. Statut technique live
# ----------------------------------------------------------------------
def etape_2_technique():
    section("2. Statut technique live (requete directe depuis le runner GitHub Actions)")
    try:
        r = requests.get(PAGE_URL, timeout=TIMEOUT, allow_redirects=True)
        print(f"  URL demandee   : {PAGE_URL}")
        print(f"  Statut final   : {r.status_code}")
        print(f"  URL finale     : {r.url}")
        if r.history:
            print(f"  Redirections   : {' -> '.join(str(h.status_code) for h in r.history)}")
        html = r.text
        import re as re_local
        m_title = re_local.search(r"<title>(.*?)</title>", html, re_local.IGNORECASE | re_local.DOTALL)
        print(f"  <title>        : {m_title.group(1).strip() if m_title else '(absent)'}")
        m_robots = re_local.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']*)["\']', html, re_local.IGNORECASE)
        print(f"  meta robots    : {m_robots.group(1) if m_robots else '(absent -- donc indexable par defaut)'}")
        m_canon = re_local.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']*)["\']', html, re_local.IGNORECASE)
        canon = m_canon.group(1) if m_canon else None
        print(f"  canonical      : {canon or '(absent)'}")
        if canon and canon.rstrip('/') != PAGE_URL.rstrip('/'):
            print("  ATTENTION : le canonical ne pointe PAS vers cette URL elle-meme -- "
                  "Google peut consolider le classement sur une autre page.")
        print(f"  Longueur HTML  : {len(html)} caracteres")
    except Exception as e:
        print(f"  ERREUR requete live : {e}")


# ----------------------------------------------------------------------
# 3. Tendance GSC
# ----------------------------------------------------------------------
def etape_3_gsc_tendance(client_bq):
    run_sql(
        client_bq,
        "3a. Tendance GSC mensuelle (12 derniers mois) pour cette page",
        f"""
        SELECT FORMAT_DATE('%Y-%m', date) AS mois,
               SUM(clics) AS clics,
               SUM(impressions) AS impressions,
               ROUND(SAFE_DIVIDE(SUM(clics), SUM(impressions)) * 100, 2) AS ctr_pct,
               ROUND(AVG(position), 1) AS position_moyenne
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE page LIKE '{LIKE_PATTERN}'
          AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
        GROUP BY mois
        ORDER BY mois
        """,
    )
    run_sql(
        client_bq,
        "3b. Tendance GSC hebdomadaire (16 dernieres semaines) pour cette page",
        f"""
        SELECT DATE_TRUNC(date, ISOWEEK) AS semaine,
               SUM(clics) AS clics,
               SUM(impressions) AS impressions,
               ROUND(AVG(position), 1) AS position_moyenne
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE page LIKE '{LIKE_PATTERN}'
          AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 112 DAY)
        GROUP BY semaine
        ORDER BY semaine
        """,
    )


# ----------------------------------------------------------------------
# 4. Tendance GA4
# ----------------------------------------------------------------------
def etape_4_ga4_tendance(client_bq):
    run_sql(
        client_bq,
        "4a. Tendance GA4 mensuelle (12 derniers mois) pour cette page",
        f"""
        SELECT FORMAT_DATE('%Y-%m', date) AS mois,
               SUM(sessions) AS sessions,
               SUM(IFNULL(conversions, 0)) AS conversions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE page_path LIKE '{LIKE_PATTERN}'
          AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
        GROUP BY mois
        ORDER BY mois
        """,
    )
    run_sql(
        client_bq,
        "4b. Tendance GA4 hebdomadaire (16 dernieres semaines) pour cette page",
        f"""
        SELECT DATE_TRUNC(date, ISOWEEK) AS semaine,
               SUM(sessions) AS sessions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE page_path LIKE '{LIKE_PATTERN}'
          AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 112 DAY)
        GROUP BY semaine
        ORDER BY semaine
        """,
    )


# ----------------------------------------------------------------------
# 5. Top requetes avant / apres
# ----------------------------------------------------------------------
def etape_5_requetes_avant_apres(client_bq):
    run_sql(
        client_bq,
        "5. Comparaison par requete -- avant (S-16 a S-9) vs apres (S-8 a S-1)",
        f"""
        WITH avant AS (
            SELECT query, SUM(clics) AS clics_avant, SUM(impressions) AS impressions_avant,
                   AVG(position) AS position_avant
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE page LIKE '{LIKE_PATTERN}'
              AND date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 112 DAY)
                            AND DATE_SUB(CURRENT_DATE(), INTERVAL 57 DAY)
            GROUP BY query
        ),
        apres AS (
            SELECT query, SUM(clics) AS clics_apres, SUM(impressions) AS impressions_apres,
                   AVG(position) AS position_apres
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE page LIKE '{LIKE_PATTERN}'
              AND date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 56 DAY)
                            AND CURRENT_DATE()
            GROUP BY query
        )
        SELECT COALESCE(a.query, p.query) AS query,
               IFNULL(a.clics_avant, 0) AS clics_avant, IFNULL(p.clics_apres, 0) AS clics_apres,
               IFNULL(a.impressions_avant, 0) AS impr_avant, IFNULL(p.impressions_apres, 0) AS impr_apres,
               ROUND(a.position_avant, 1) AS position_avant, ROUND(p.position_apres, 1) AS position_apres
        FROM avant a
        FULL OUTER JOIN apres p ON a.query = p.query
        ORDER BY (IFNULL(a.clics_avant,0) + IFNULL(a.impressions_avant,0)) DESC
        LIMIT 25
        """,
    )


# ----------------------------------------------------------------------
# 6. Cannibalisation sur les requetes historiques de la page
# ----------------------------------------------------------------------
def etape_6_cannibalisation(client_bq):
    df_top = run_sql(
        client_bq,
        "6a. Top 8 requetes historiques de la page (180 jours, toutes periodes confondues)",
        f"""
        SELECT query, SUM(impressions) AS impressions, SUM(clics) AS clics
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE page LIKE '{LIKE_PATTERN}'
          AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
        GROUP BY query
        ORDER BY impressions DESC
        LIMIT 8
        """,
    )
    if df_top is None or df_top.empty:
        print("\n  Pas de requete historique -> pas de verification de cannibalisation possible.")
        return
    requetes = df_top["query"].tolist()
    requetes_sql = ", ".join("'" + q.replace("'", "\\'") + "'" for q in requetes)
    run_sql(
        client_bq,
        "6b. Pour ces requetes, TOUTES les pages du site en concurrence, avant (S-16 a S-9) vs apres (S-8 a S-1)",
        f"""
        WITH avant AS (
            SELECT query, page, SUM(clics) AS clics_avant, SUM(impressions) AS impressions_avant,
                   AVG(position) AS position_avant
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE query IN ({requetes_sql})
              AND date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 112 DAY)
                            AND DATE_SUB(CURRENT_DATE(), INTERVAL 57 DAY)
            GROUP BY query, page
        ),
        apres AS (
            SELECT query, page, SUM(clics) AS clics_apres, SUM(impressions) AS impressions_apres,
                   AVG(position) AS position_apres
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE query IN ({requetes_sql})
              AND date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 56 DAY)
                            AND CURRENT_DATE()
            GROUP BY query, page
        )
        SELECT COALESCE(a.query, p.query) AS query,
               COALESCE(a.page, p.page) AS page,
               IFNULL(a.clics_avant, 0) AS clics_avant, IFNULL(p.clics_apres, 0) AS clics_apres,
               IFNULL(a.impressions_avant, 0) AS impr_avant, IFNULL(p.impressions_apres, 0) AS impr_apres,
               ROUND(a.position_avant, 1) AS position_avant, ROUND(p.position_apres, 1) AS position_apres
        FROM avant a
        FULL OUTER JOIN apres p ON a.query = p.query AND a.page = p.page
        ORDER BY query, (IFNULL(a.impressions_avant,0) + IFNULL(p.impressions_apres,0)) DESC
        """,
    )


# ----------------------------------------------------------------------
# 7. Indexation Google (si dispo)
# ----------------------------------------------------------------------
def etape_7_indexation(client_bq):
    run_sql(
        client_bq,
        "7. Etat d'indexation Google connu (04_pipeline_seo.indexation_google -- rempli manuellement, peut etre absent/perime)",
        f"""
        SELECT post_id, url, coverage_state, verdict, robots_txt_state,
               indexing_state, page_fetch_state, last_crawl_time, crawled_as, checked_at
        FROM `{PROJECT_ID}.04_pipeline_seo.indexation_google`
        WHERE url LIKE '{LIKE_PATTERN}'
        """,
    )


# ----------------------------------------------------------------------
# 8. Maillage interne reel (scan complet du contenu publie)
# ----------------------------------------------------------------------
def etape_8_maillage(client_bq):
    section("8a. Scan complet du contenu publie -- qui pointe vraiment vers cette page ?")
    posts = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                params={"per_page": 100, "page": page, "status": "publish",
                        "_fields": "id,link,content"},
                timeout=TIMEOUT,
            )
        except Exception as e:
            print(f"  erreur page {page} : {e}")
            break
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        posts.extend(data)
        page += 1
        time.sleep(0.15)
    print(f"  {len(posts)} article(s) publie(s) recupere(s).")

    chemin_rel = PAGE_PATH
    sources = []
    for post in posts:
        contenu = post.get("content", {}).get("rendered", "") or ""
        if PAGE_URL in contenu or PAGE_URL.rstrip("/") in contenu or chemin_rel in contenu or chemin_rel.rstrip("/") in contenu:
            sources.append(post.get("link"))

    print(f"\n  TOTAL : {len(sources)} article(s) pointent reellement vers la page pilier.")
    for s in sources[:30]:
        print(f"    - {s}")
    if len(sources) > 30:
        print(f"    ... (+{len(sources) - 30} autres)")

    # Combien d'articles "Contrat Electricite" existent, pour comparer au
    # nombre qui lient reellement (inserer_lien_pilier() devrait couvrir 100%
    # des articles publies APRES l'introduction de ce mecanisme).
    run_sql(
        client_bq,
        "8b. Nombre total d'articles publies dans le sous-silo 'Contrat Electricite' (pour comparer au nb de liens trouves ci-dessus)",
        f"""
        SELECT COUNT(*) AS nb_articles,
               MIN(date_publication) AS premiere_publication,
               MAX(date_publication) AS derniere_publication
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE sous_silo_strategique LIKE 'Contrat Électricité%'
        """,
    )


def main():
    client_bq = init_bigquery()
    print(f"Diagnostic 360 -- {PAGE_URL}")
    print(f"Execute le {datetime.now(timezone.utc).isoformat()}")

    etape_1_identite(client_bq)
    etape_2_technique()
    etape_3_gsc_tendance(client_bq)
    etape_4_ga4_tendance(client_bq)
    etape_5_requetes_avant_apres(client_bq)
    etape_6_cannibalisation(client_bq)
    etape_7_indexation(client_bq)
    etape_8_maillage(client_bq)

    section("FIN DU DIAGNOSTIC")


if __name__ == "__main__":
    main()
