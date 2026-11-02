"""
CME — Diagnostic : l'operateur a teste TOUS les formulaires de conversion
ce soir (02-03/11/2026), apres validation du correctif telephone/code_postal
(commit 5b0bcfd) -- demande explicite : lister les leads de test dans
leads_convertis pour qu'il puisse les identifier et nettoyer manuellement
cote Google Sheets, et preparer leur nettoyage cote BigQuery.

Fenetre large (3h) pour couvrir toute la session de test de ce soir, tous
tools confondus (contact-expert-formulaire, contact-expert-inline,
appel-expert-inline, appel-header-formulaire, appel-telephone).

LECTURE SEULE -- n'effectue aucune suppression.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("📥 leads_convertis des 3 dernieres heures, tous tools...\n")
    df = client.query(f"""
        SELECT timestamp, tool, prenom, nom, telephone, email, code_postal,
               source_page, source_post_id, details
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 HOUR)
        ORDER BY timestamp
    """).to_dataframe()

    if df.empty:
        print("⚠️ Aucune ligne sur les 3 dernieres heures.")
        return

    print(f"✅ {len(df)} ligne(s) trouvee(s) :\n")
    print("=" * 115)
    for i, row in df.iterrows():
        print(f"\n  #{i}  {row['timestamp']}  tool={row['tool']!r}")
        print(f"      prenom={row['prenom']!r}  telephone={row['telephone']!r}  email={row['email']!r}  code_postal={row['code_postal']!r}")
        print(f"      source_page={row['source_page']!r}  source_post_id={row['source_post_id']!r}")
        print(f"      details={row['details']!r}")

    print("\n" + "=" * 115)
    print(f"Total : {len(df)} ligne(s) sur la fenetre -- a comparer avec les tools/telephones")
    print("reellement utilises ce soir pour decider lesquelles supprimer.")


if __name__ == "__main__":
    main()
