"""
CME -- Diagnostic lecture seule (12/11/2026) : l'operateur demande si le
fait de NE PAS publier de nouvel article pendant plus d'une semaine peut
impacter le flux de trafic organique du site.

Plutot que de repondre uniquement par la theorie SEO generale, ce script
cherche s'il existe un VRAI precedent dans l'historique du site :
  1. Liste toutes les dates de publication distinctes
     (historique_publications) et calcule l'ecart entre dates
     consecutives -- signale tout ecart > 7 jours (une vraie pause de
     plus d'une semaine sans aucun nouvel article).
  2. Pour chaque pause trouvee (ou, a defaut, pour l'incident SearchApi du
     08-10/11 qui a fait perdre 3 jours de publication consecutifs),
     compare le trafic SITE ENTIER (GSC impressions/clics/position, GA4
     sessions) AVANT / PENDANT / APRES la pause -- pour voir si le flux
     organique (qui vient a plus de 99% des >1000 articles DEJA publies
     et DEJA indexes, pas des nouveaux) a reellement decroche, ou s'il a
     continue sans a-coup.

LECTURE SEULE.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"Import de pipeline/pipeline.py impossible : {e}")


def section(titre):
    print("\n" + "=" * 100)
    print(titre)
    print("=" * 100)


def run_sql(client_bq, titre, sql):
    section(titre)
    try:
        df = client_bq.query(sql).to_dataframe()
        if df.empty:
            print("  (0 ligne)")
        else:
            print(df.to_string(index=False))
        return df
    except Exception as e:
        print(f"  ERREUR SQL : {e}")
        return None


def main():
    client_bq = init_bigquery()

    df_gaps = run_sql(client_bq, "1. Ecarts > 3 jours entre deux dates de publication consecutives (tout l'historique)", f"""
        WITH dates_pub AS (
            SELECT DISTINCT DATE(date_publication) AS jour
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        ),
        avec_precedent AS (
            SELECT jour,
                   LAG(jour) OVER (ORDER BY jour) AS jour_precedent,
                   DATE_DIFF(jour, LAG(jour) OVER (ORDER BY jour), DAY) AS ecart_jours
            FROM dates_pub
        )
        SELECT jour_precedent, jour, ecart_jours
        FROM avec_precedent
        WHERE ecart_jours > 3
        ORDER BY jour
    """)

    run_sql(client_bq, "2. Nombre d'articles publies par semaine (tout l'historique) -- pour voir le rythme global", f"""
        SELECT DATE_TRUNC(DATE(date_publication), ISOWEEK) AS semaine,
               COUNT(*) AS nb_articles
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        GROUP BY semaine
        ORDER BY semaine
    """)

    # Fenetre d'interet pour le vrai incident SearchApi (08-10/11, 0 article
    # publie ces 3 jours) : trafic site entier avant / pendant / apres.
    run_sql(client_bq, "3. Trafic SITE ENTIER jour par jour (GSC) autour de l'incident SearchApi du 08-10/11 (0 article publie ces 3 jours)", f"""
        SELECT date, FORMAT_DATE('%A', date) AS jour,
               SUM(clics) AS clics, SUM(impressions) AS impressions,
               ROUND(AVG(position), 1) AS position_moyenne
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date BETWEEN '2026-11-01' AND CURRENT_DATE()
        GROUP BY date, jour
        ORDER BY date
    """)

    run_sql(client_bq, "4. Trafic SITE ENTIER jour par jour (GA4) autour du meme incident", f"""
        SELECT date, FORMAT_DATE('%A', date) AS jour,
               SUM(sessions) AS sessions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE date BETWEEN '2026-11-01' AND CURRENT_DATE()
        GROUP BY date, jour
        ORDER BY date
    """)

    # Part du trafic qui vient d'articles publies il y a >30 jours, pour
    # objectiver "le flux organique vient majoritairement de l'ancien
    # contenu, pas des publications toutes fraiches".
    run_sql(client_bq, "5. Repartition des clics GSC (30 derniers jours) par anciennete de l'article (si post_id retrouvable via url_wp)", f"""
        WITH gsc_30j AS (
            SELECT page, SUM(clics) AS clics, SUM(impressions) AS impressions
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            GROUP BY page
        ),
        pub AS (
            SELECT url_wp, DATE(MIN(date_publication)) AS date_pub
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            GROUP BY url_wp
        )
        SELECT
            CASE
                WHEN DATE_DIFF(CURRENT_DATE(), p.date_pub, DAY) <= 7 THEN '0-7 jours'
                WHEN DATE_DIFF(CURRENT_DATE(), p.date_pub, DAY) <= 30 THEN '8-30 jours'
                WHEN DATE_DIFF(CURRENT_DATE(), p.date_pub, DAY) <= 90 THEN '31-90 jours'
                ELSE '90+ jours'
            END AS anciennete_article,
            SUM(g.clics) AS clics_30j,
            SUM(g.impressions) AS impressions_30j,
            COUNT(DISTINCT g.page) AS nb_pages
        FROM gsc_30j g
        JOIN pub p ON g.page LIKE CONCAT('%', p.url_wp)
        GROUP BY anciennete_article
        ORDER BY anciennete_article
    """)

    section("FIN")


if __name__ == "__main__":
    main()
