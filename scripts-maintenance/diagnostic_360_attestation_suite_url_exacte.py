"""
CME -- Suite du diagnostic 360 (meme jour, 12/11/2026) sur la page pilier
attestation-de-contrat-delectricite. Le premier passage
(diagnostic_360_attestation_contrat_electricite.py) a mis en evidence DEUX
URLs live pour le MEME post_id (2218) :
  - longue  : /electricite/contrat-electricite/attestation-de-contrat-delectricite/
              (celle que pointent les 50 liens internes + LIENS_PILIERS_SOUS_SILO)
  - courte  : /attestation-de-contrat-delectricite/
              (celle marquee canonical par la longue, et "Submitted and
              indexed" dans indexation_google)

Ce script re-interroge GSC et GA4 par URL EXACTE (pas de LIKE agregeant les
deux) pour savoir sans ambiguite laquelle des deux porte reellement les
impressions/clics/sessions, et depuis quand.

LECTURE SEULE.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"Import de pipeline/pipeline.py impossible : {e}")

URL_LONGUE = "https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/attestation-de-contrat-delectricite/"
URL_COURTE = "https://www.comprendre-mon-energie.fr/attestation-de-contrat-delectricite/"
PATH_LONGUE = "/electricite/contrat-electricite/attestation-de-contrat-delectricite/"
PATH_COURTE = "/attestation-de-contrat-delectricite/"


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
    except Exception as e:
        print(f"  ERREUR SQL : {e}")


def main():
    client_bq = init_bigquery()

    run_sql(client_bq, "1. GSC mensuel (12 mois) -- URL LONGUE exacte uniquement", f"""
        SELECT FORMAT_DATE('%Y-%m', date) AS mois, SUM(clics) AS clics,
               SUM(impressions) AS impressions, ROUND(AVG(position),1) AS position_moy
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE page = '{URL_LONGUE}' AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
        GROUP BY mois ORDER BY mois
    """)

    run_sql(client_bq, "2. GSC mensuel (12 mois) -- URL COURTE exacte uniquement", f"""
        SELECT FORMAT_DATE('%Y-%m', date) AS mois, SUM(clics) AS clics,
               SUM(impressions) AS impressions, ROUND(AVG(position),1) AS position_moy
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE page = '{URL_COURTE}' AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
        GROUP BY mois ORDER BY mois
    """)

    run_sql(client_bq, "3. GA4 mensuel (12 mois) -- page_path LONG exact uniquement", f"""
        SELECT FORMAT_DATE('%Y-%m', date) AS mois, SUM(sessions) AS sessions,
               SUM(IFNULL(conversions,0)) AS conversions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE page_path = '{PATH_LONGUE}' AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
        GROUP BY mois ORDER BY mois
    """)

    run_sql(client_bq, "4. GA4 mensuel (12 mois) -- page_path COURT exact uniquement", f"""
        SELECT FORMAT_DATE('%Y-%m', date) AS mois, SUM(sessions) AS sessions,
               SUM(IFNULL(conversions,0)) AS conversions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE page_path = '{PATH_COURTE}' AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
        GROUP BY mois ORDER BY mois
    """)

    run_sql(client_bq, "5. Premiere et derniere date GSC vue pour chacune des 2 URLs exactes (tout l'historique)", f"""
        SELECT page, MIN(date) AS premiere_date, MAX(date) AS derniere_date, COUNT(*) AS nb_lignes
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE page IN ('{URL_LONGUE}', '{URL_COURTE}')
        GROUP BY page
    """)

    section("FIN")


if __name__ == "__main__":
    main()
