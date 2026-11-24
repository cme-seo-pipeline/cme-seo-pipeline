"""
CME — Diagnostic lecture seule : pourquoi le filtre strict de
nettoyer_lead_test_2411_demenagement.py n'a trouve aucune ligne (24/11/2026).
Elargit la recherche progressivement (tool seul, puis + suffixe telephone
large, puis fenetre temporelle large) pour voir les vraies valeurs stockees
sans supposer le format exact. Aucune adresse email utilisee ni affichee.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE_REF = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("=== Toutes les lignes contact-expert-inline des dernieres 3 heures ===")
    q1 = f"""
    SELECT timestamp, tool, telephone, source_post_id, source_page, details
    FROM `{TABLE_REF}`
    WHERE tool = 'contact-expert-inline'
      AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 HOUR)
    ORDER BY timestamp DESC
    """
    for l in client.query(q1).result():
        print(f"  - {l.timestamp} | tel='{l.telephone}' | post_id={l.source_post_id} | "
              f"page={l.source_page} | details={l.details}")

    print("\n=== Toutes les lignes (tout tool) contenant '695410020' dans le telephone ===")
    q2 = f"""
    SELECT timestamp, tool, telephone, source_post_id, source_page
    FROM `{TABLE_REF}`
    WHERE telephone LIKE '%695410020%'
    ORDER BY timestamp DESC
    """
    for l in client.query(q2).result():
        print(f"  - {l.timestamp} | tool={l.tool} | tel='{l.telephone}' | "
              f"post_id={l.source_post_id} | page={l.source_page}")

    print("\n=== Toutes les lignes avec source_page contenant 'electricite-demenagement-checklist' ===")
    q3 = f"""
    SELECT timestamp, tool, telephone, source_post_id, source_page
    FROM `{TABLE_REF}`
    WHERE source_page LIKE '%electricite-demenagement-checklist%'
    ORDER BY timestamp DESC
    """
    for l in client.query(q3).result():
        print(f"  - {l.timestamp} | tool={l.tool} | tel='{l.telephone}' | "
              f"post_id={l.source_post_id} | page={l.source_page}")


if __name__ == "__main__":
    main()
