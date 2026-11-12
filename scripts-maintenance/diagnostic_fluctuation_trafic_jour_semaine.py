"""
CME -- Diagnostic lecture seule (12/11/2026) : l'operateur observe une
chute de trafic le week-end/les jours feries par rapport au milieu de
semaine, et demande si c'est du a un probleme technique (actualite des
articles deja publies, perte de classement) plutot qu'a un phenomene de
demande normal.

Ce script mesure, sur TOUT LE SITE (pas une seule page) :
  1. GSC (clics/impressions/position) par jour de semaine, 90 derniers
     jours -- si le motif est un pur effet de DEMANDE (moins de gens
     cherchent "resilier mon contrat d'electricite" le dimanche), les
     IMPRESSIONS baissent aussi le week-end (Google montre moins le site
     parce qu'on lui pose moins la question), sans que la POSITION
     moyenne ne se degrade. Si au contraire la position se degrade le
     week-end sans que les impressions ne bougent, ce serait le signe
     d'un probleme technique cote crawl/fraicheur.
  2. GA4 (sessions) par jour de semaine, meme fenetre.
  3. Detail jour par jour sur les 21 derniers jours (pour voir les jours
     feries specifiques -- Toussaint 01/11, Armistice 11/11 -- a cote des
     week-ends ordinaires).

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
    except Exception as e:
        print(f"  ERREUR SQL : {e}")


def main():
    client_bq = init_bigquery()

    run_sql(client_bq, "1. GSC (site entier) par jour de semaine -- 90 derniers jours", f"""
        SELECT FORMAT_DATE('%A', date) AS jour,
               EXTRACT(DAYOFWEEK FROM date) AS num_jour,
               SUM(clics) AS clics_totaux,
               SUM(impressions) AS impressions_totales,
               ROUND(AVG(position), 1) AS position_moyenne,
               COUNT(DISTINCT date) AS nb_dates
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
        GROUP BY jour, num_jour
        ORDER BY num_jour
    """)

    run_sql(client_bq, "2. GA4 (site entier) par jour de semaine -- 90 derniers jours", f"""
        SELECT FORMAT_DATE('%A', date) AS jour,
               EXTRACT(DAYOFWEEK FROM date) AS num_jour,
               SUM(sessions) AS sessions_totales,
               ROUND(AVG(sessions), 1) AS sessions_moy_par_jour_ouvre,
               COUNT(DISTINCT date) AS nb_dates
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
        GROUP BY jour, num_jour
        ORDER BY num_jour
    """)

    run_sql(client_bq, "3. Detail jour par jour -- 21 derniers jours (GSC, site entier)", f"""
        SELECT date, FORMAT_DATE('%A', date) AS jour,
               SUM(clics) AS clics, SUM(impressions) AS impressions,
               ROUND(AVG(position), 1) AS position_moyenne
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 21 DAY)
        GROUP BY date, jour
        ORDER BY date
    """)

    run_sql(client_bq, "4. Detail jour par jour -- 21 derniers jours (GA4, site entier)", f"""
        SELECT date, FORMAT_DATE('%A', date) AS jour,
               SUM(sessions) AS sessions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 21 DAY)
        GROUP BY date, jour
        ORDER BY date
    """)

    section("FIN")


if __name__ == "__main__":
    main()
