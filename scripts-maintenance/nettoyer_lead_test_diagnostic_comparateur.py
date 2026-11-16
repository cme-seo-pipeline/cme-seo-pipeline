"""
CME — Nettoyage du lead de test cree par tester_lead_reel_comparateur_energie.py
(16/11/2026). Cible par prenom='TEST-DIAGNOSTIC' + telephone='0600000000',
tool='comparateur-energie' -- meme pattern que les nettoyages de test
precedents de ce projet (dry-run par defaut, --apply pour ecrire).
"""
import sys

from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"
APPLY = "--apply" in sys.argv


def main():
    client = bigquery.Client(project=PROJECT_ID)
    table = f"`{PROJECT_ID}.{DATASET_ID}.leads_convertis`"

    df = client.query(f"""
        SELECT timestamp, tool, prenom, telephone
        FROM {table}
        WHERE tool = 'comparateur-energie' AND prenom = 'TEST-DIAGNOSTIC' AND telephone = '0600000000'
    """).to_dataframe()
    print(f"Lignes de test trouvées : {len(df)}")
    for _, r in df.iterrows():
        print(f"  {dict(r)}")

    if df.empty:
        print("Rien à supprimer.")
        return

    if not APPLY:
        print("\nDRY-RUN -- relancer avec --apply pour supprimer réellement.")
        return

    job = client.query(f"""
        DELETE FROM {table}
        WHERE tool = 'comparateur-energie' AND prenom = 'TEST-DIAGNOSTIC' AND telephone = '0600000000'
    """)
    job.result()
    print(f"✅ {job.num_dml_affected_rows} ligne(s) supprimée(s).")


if __name__ == "__main__":
    main()
