"""
CME — Diagnostic des 5 URLs signalees introuvables par l'operateur le
25/11/2026 :
  1. /aide-energetique/aides-renovation-toiture/isolation-toiture-aides-financieres-demarches/
  2. /gaz/chauffage-gaz/fonctionnement-chaudiere-gaz-0902-2/
  3. /gaz/demenagement-gaz/compteur-gaz-intelligent-linky-fonctionnement/
  4. /electricite/heures-pleines-creuses/heures-pleines-creuses-fonctionnement-0905/
  5. /electricite/heures-pleines-creuses/heures-creuses-electricite-fonctionnement-0905/

Meme methodologie que l'audit 404 externe du 02/11/2026 (voir CLAUDE.md,
sections "Audit 404 externe du 02/11/2026" et "Root cause confirmee +
correctif structurel — liens internes morts"), avec la lecon de ce
precedent deja integree des le depart (ne JAMAIS se limiter a un
echantillon choisi a la main pour le scan de maillage interne -- le
premier passage du 02/11 avait conclu a tort a un backlink externe avant
qu'un scan EXHAUSTIF ne revele les vrais liens internes coupables) :

Pour chaque URL :
  1. Statut HTTP reel en live (runner GitHub Actions, acces reseau complet,
     contrairement au sandbox Claude Code).
  2. historique_publications (BigQuery) par correspondance de slug.
  3. Recherche WP directe par slug, TOUS statuts (publish/draft/trash/
     pending/future/private) -- authentifie.
  4. 01_raw.gsc_queries (LIKE sur `page`) -- Google a-t-il deja vu cette URL.
  5. 02_cleaned.wp_url_mapping -- dernier snapshot complet des URLs publiees.
  6. Sitemap XML live (tous les sous-sitemaps post).
  7. Scan EXHAUSTIF du contenu de TOUS les articles publies (pas un
     echantillon) pour un lien interne (absolu ou relatif) pointant vers
     une des 5 URLs.

LECTURE SEULE. Necessite WP_APP_PASSWORD (+ WP_USERNAME optionnel).
"""
import os
import sys
import re
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

import requests

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)
TIMEOUT = 20
PER_PAGE = 100

URLS_404 = [
    "https://www.comprendre-mon-energie.fr/aide-energetique/aides-renovation-toiture/isolation-toiture-aides-financieres-demarches/",
    "https://www.comprendre-mon-energie.fr/gaz/chauffage-gaz/fonctionnement-chaudiere-gaz-0902-2/",
    "https://www.comprendre-mon-energie.fr/gaz/demenagement-gaz/compteur-gaz-intelligent-linky-fonctionnement/",
    "https://www.comprendre-mon-energie.fr/electricite/heures-pleines-creuses/heures-pleines-creuses-fonctionnement-0905/",
    "https://www.comprendre-mon-energie.fr/electricite/heures-pleines-creuses/heures-creuses-electricite-fonctionnement-0905/",
]
CHEMINS_RELATIFS = [u.replace(WP_URL, "") for u in URLS_404]
SLUGS = [u.rstrip("/").rsplit("/", 1)[-1] for u in URLS_404]


def statut_http(url):
    try:
        r = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        chain = " -> ".join(str(h.status_code) for h in r.history) + (" -> " if r.history else "")
        return f"{chain}{r.status_code}", r.url
    except Exception as e:
        return f"ERREUR({e})", None


def chercher_post_wp_par_slug(slug):
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={"slug": slug, "status": "publish,draft,trash,pending,future,private",
                    "context": "edit"},
            auth=AUTH, timeout=TIMEOUT,
        )
        if r.status_code == 200 and r.json():
            return r.json()
    except Exception as e:
        return [{"erreur": str(e)}]
    return []


def lister_tous_les_posts():
    posts = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                params={"per_page": PER_PAGE, "page": page, "status": "publish",
                        "_fields": "id,link,content"},
                timeout=TIMEOUT,
            )
        except Exception as e:
            print(f"  ⚠️ erreur page {page} : {e}")
            break
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        posts.extend(data)
        page += 1
        time.sleep(0.15)
    return posts


def verifier_sitemap():
    trouve = {url: False for url in URLS_404}
    try:
        r = requests.get(f"{WP_URL}/sitemap_index.xml", timeout=TIMEOUT)
        sous_sitemaps = re.findall(r'<loc>([^<]+)</loc>', r.text) if r.status_code == 200 else []
    except Exception as e:
        print(f"  ⚠️ Erreur sitemap_index.xml : {e}")
        return trouve
    print(f"  sitemap_index.xml -> HTTP {r.status_code}, {len(sous_sitemaps)} sous-sitemap(s)")
    sitemap_posts = [s for s in sous_sitemaps if 'post-sitemap' in s or 'sitemap.xml' in s.lower()]
    for sm in sitemap_posts[:15]:
        try:
            r2 = requests.get(sm, timeout=TIMEOUT)
            if r2.status_code != 200:
                continue
            for url in URLS_404:
                if url in r2.text or url.rstrip("/") in r2.text:
                    trouve[url] = True
        except Exception:
            continue
        time.sleep(0.1)
    return trouve


def main():
    client_bq = init_bigquery()

    print("=" * 110)
    print("ETAPE 1-5 : statut live, historique_publications, statuts WP, GSC, wp_url_mapping")
    print("=" * 110)

    for url, slug in zip(URLS_404, SLUGS):
        print(f"\n### {url}")
        print(f"    slug = {slug!r}")

        statut, url_finale = statut_http(url)
        print(f"    HTTP live : {statut}" + (f" (redirige vers {url_finale})" if url_finale and url_finale != url else ""))

        df = client_bq.query(f"""
            SELECT post_id, date_publication, silo, sous_silo_strategique,
                   titre, mot_cle, run_id, type_publication, url_wp
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE url_wp LIKE '%{slug}%' OR url_wp LIKE '%{slug}/'
            ORDER BY date_publication
        """).to_dataframe()
        if len(df) == 0:
            print("    historique_publications : AUCUNE ligne pour ce slug")
        else:
            for _, r in df.iterrows():
                print(f"    historique_publications : post_id={r['post_id']} | {r['date_publication']} | "
                      f"silo={r['silo']} | sous_silo={r['sous_silo_strategique']} | mot_cle={r['mot_cle']!r}")
                print(f"        titre={str(r['titre'])[:90]!r} | run_id={r['run_id']!r} | "
                      f"type_publication={r['type_publication']!r} | url_wp={r['url_wp']!r}")

        posts_wp = chercher_post_wp_par_slug(slug)
        if posts_wp:
            for p in posts_wp:
                if "erreur" in p:
                    print(f"    Recherche WP par slug (tous statuts) : erreur -> {p['erreur']}")
                else:
                    print(f"    Recherche WP par slug (tous statuts) : id={p.get('id')}, "
                          f"status={p.get('status')!r}, slug reel={p.get('slug')!r}, link={p.get('link')!r}")
        else:
            print("    Recherche WP par slug (tous statuts) : AUCUN post, meme en corbeille/brouillon")

        df_gsc = client_bq.query(f"""
            SELECT COUNT(*) AS n, SUM(impressions) AS impressions, SUM(clics) AS clics,
                   MIN(date) AS premiere_date, MAX(date) AS derniere_date
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE page LIKE '%{slug}%'
        """).to_dataframe()
        n_gsc = int(df_gsc.iloc[0]["n"])
        if n_gsc == 0:
            print("    01_raw.gsc_queries : AUCUNE ligne (meme partielle/LIKE) pour ce slug")
        else:
            r = df_gsc.iloc[0]
            print(f"    01_raw.gsc_queries : {n_gsc} ligne(s), impressions={r['impressions']}, "
                  f"clics={r['clics']}, periode {r['premiere_date']} -> {r['derniere_date']}")

        df_map = client_bq.query(f"""
            SELECT post_id, url
            FROM `{PROJECT_ID}.02_cleaned.wp_url_mapping`
            WHERE url LIKE '%{slug}%'
        """).to_dataframe()
        if len(df_map) == 0:
            print("    02_cleaned.wp_url_mapping : AUCUNE ligne pour ce slug")
        else:
            for _, r in df_map.iterrows():
                print(f"    02_cleaned.wp_url_mapping : post_id={r['post_id']} | url={r['url']!r}")

    print("\n" + "=" * 110)
    print("ETAPE 6 : sitemap XML live")
    print("=" * 110)
    presence_sitemap = verifier_sitemap()
    for url, present in presence_sitemap.items():
        print(f"    {'PRESENT' if present else 'absent'} dans un sitemap post : {url}")

    print("\n" + "=" * 110)
    print("ETAPE 7 : scan EXHAUSTIF du maillage interne (TOUS les articles publies, pas un echantillon)")
    print("=" * 110)
    print("Recuperation de tous les articles publies (contenu complet)...")
    posts = lister_tous_les_posts()
    print(f"{len(posts)} article(s) recupere(s).\n")

    trouvailles = {url: [] for url in URLS_404}
    for post in posts:
        contenu = post.get("content", {}).get("rendered", "") or ""
        for url, chemin_rel in zip(URLS_404, CHEMINS_RELATIFS):
            if url in contenu or url.rstrip("/") in contenu or chemin_rel in contenu or chemin_rel.rstrip("/") in contenu:
                trouvailles[url].append(post.get("link"))

    total = 0
    for url, sources in trouvailles.items():
        if sources:
            total += len(sources)
            print(f"\n*** {url} ***")
            print(f"    LIE DEPUIS {len(sources)} article(s) :")
            for s in sources:
                print(f"        - {s}")
        else:
            print(f"\n{url} : aucun lien interne trouve dans les {len(posts)} articles publies")

    print(f"\n{'=' * 110}")
    print(f"TOTAL : {total} lien(s) interne(s) trouve(s) vers les 5 URLs, sur {len(posts)} articles scannes.")
    print("=" * 110)


if __name__ == "__main__":
    main()
