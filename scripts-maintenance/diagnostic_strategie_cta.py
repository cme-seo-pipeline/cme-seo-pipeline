"""
CME — Diagnostic de donnees (lecture seule) pour nourrir une strategie
d'augmentation des clics sur les CTA de conversion (numero header +
"Contactez un expert"), demandee par l'operateur le 22/10/2026.

Ne modifie rien. Objectif : remplacer les recommandations generiques par
des chiffres reels du site -- volumetrie de trafic par page/silo, devices,
et historique de conversion des 3 anciens simulateurs (avant leur
remplacement par /contactez-un-expert/ en oct. 2026) pour avoir un ordre
de grandeur de CTR avant/apres.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")


def run(client_bq, titre, sql):
    print("=" * 70)
    print(titre)
    print("=" * 70)
    try:
        df = client_bq.query(sql).to_dataframe()
        if df.empty:
            print("   (0 ligne)")
        else:
            print(df.to_string())
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")
    print()


def main():
    client_bq = init_bigquery()

    run(client_bq, "0a. Schema de 01_raw.ga4_pages", f"""
        SELECT column_name, data_type
        FROM `{PROJECT_ID}.01_raw`.INFORMATION_SCHEMA.COLUMNS
        WHERE table_name = 'ga4_pages'
        ORDER BY ordinal_position
    """)

    run(client_bq, "0b. Schema de leads_convertis", f"""
        SELECT column_name, data_type
        FROM `{PROJECT_ID}.{DATASET_ID}`.INFORMATION_SCHEMA.COLUMNS
        WHERE table_name = 'leads_convertis'
        ORDER BY ordinal_position
    """)

    run(client_bq, "1. Volume de clics/leads par outil et par mois (tout l'historique)", f"""
        SELECT FORMAT_TIMESTAMP('%Y-%m', timestamp) AS mois, tool, COUNT(*) AS nb
        FROM `{PROJECT_ID}.{DATASET_ID}.leads_convertis`
        GROUP BY mois, tool
        ORDER BY mois, tool
    """)

    run(client_bq, "2. Sessions/pages vues totales par mois (GA4, si colonne date/sessions dispo)", f"""
        SELECT FORMAT_DATE('%Y-%m', date) AS mois,
               SUM(sessions) AS sessions_totales,
               SUM(IFNULL(conversions, 0)) AS conversions_ga4
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        GROUP BY mois
        ORDER BY mois
    """)

    run(client_bq, "3. Top 20 pages par trafic (30 derniers jours, GA4)", f"""
        SELECT page_path, SUM(sessions) AS sessions, SUM(IFNULL(conversions,0)) AS conversions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        GROUP BY page_path
        ORDER BY sessions DESC
        LIMIT 20
    """)

    run(client_bq, "4. Repartition device (30 derniers jours) si colonne device dispo", f"""
        SELECT device_category, SUM(sessions) AS sessions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        GROUP BY device_category
        ORDER BY sessions DESC
    """)

    run(client_bq, "5. Trafic sur /contactez-un-expert/ (30 derniers jours)", f"""
        SELECT date, SUM(sessions) AS sessions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE page_path LIKE '%contactez-un-expert%'
          AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        GROUP BY date
        ORDER BY date
    """)

    run(client_bq, "6. Toutes les lignes leads_convertis depuis le 01/09 (detail)", f"""
        SELECT timestamp, tool, source_page
        FROM `{PROJECT_ID}.{DATASET_ID}.leads_convertis`
        WHERE timestamp >= '2026-09-01'
        ORDER BY timestamp DESC
        LIMIT 100
    """)


if __name__ == "__main__":
    main()
