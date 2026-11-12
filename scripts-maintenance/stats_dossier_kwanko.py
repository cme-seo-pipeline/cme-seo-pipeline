"""
CME — Stats de synthese pour le dossier Kwanko (demande operateur du
12/11/2026 : presentation entreprise + KPIs + LP a transmettre a un charge
de partenariat Kwanko pour validation de compte).

Calcule 3 chiffres defendables, a date, plutot que d'extrapoler depuis une
mesure partielle anterieure (fenetre 11 jours du doc "objectif-100-leads-mois") :
  - nombre total d'articles publies (historique_publications)
  - sessions GA4 des 30 derniers jours (01_raw.ga4_pages, tous silos)
  - leads reels des 30 derniers jours (04_pipeline_seo.leads_convertis)

LECTURE SEULE -- aucune ecriture.
Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 stats_dossier_kwanko.py
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("📥 Nombre total d'articles publies (historique_publications)...")
    nb_articles = list(client.query(f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
    """).result())[0]["n"]

    print("📥 Sessions GA4 des 30 derniers jours (01_raw.ga4_pages)...")
    sessions_30j = list(client.query(f"""
        SELECT SUM(sessions) AS n
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    """).result())[0]["n"] or 0

    print("📥 Leads reels des 30 derniers jours (leads_convertis)...")
    leads_30j = list(client.query(f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.{DATASET_ID}.leads_convertis`
        WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    """).result())[0]["n"]

    print("\n" + "=" * 60)
    print("SYNTHESE -- DOSSIER KWANKO")
    print("=" * 60)
    print(f"Articles publies (total)       : {nb_articles}")
    print(f"Sessions GA4 (30 derniers jours): {sessions_30j}")
    print(f"Leads reels (30 derniers jours) : {leads_30j}")


if __name__ == "__main__":
    main()
