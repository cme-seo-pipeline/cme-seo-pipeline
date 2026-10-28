"""
CME — Localisation (lecture seule) de la ligne parasite inseree par
erreur dans leads_convertis le 28/10/2026 vers 15h45 UTC : un POST de
diagnostic (corps vide, pour verifier l'existence de la route
/log-lead) a declenche une insertion reelle, faute de garde-fou cote
serveur (tracking-api/server.py insert toujours une ligne, meme vide).

Ne supprime rien -- se contente d'identifier la/les ligne(s) candidates
avec precision (tool vide, tous les champs identite vides, timestamp
dans la fenetre du test) pour validation par l'operateur avant toute
suppression.

USAGE :
  python3 localiser_ligne_test_leads_convertis.py
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
    df = client.query(f"""
        SELECT timestamp, tool, prenom, nom, email, telephone, source_page
        FROM `{PROJECT_ID}.{DATASET_ID}.leads_convertis`
        WHERE timestamp >= TIMESTAMP('2026-10-28 15:30:00')
        ORDER BY timestamp DESC
    """).to_dataframe()

    if df.empty:
        print("✅ Aucune ligne dans cette fenetre -- rien a nettoyer.")
        return

    print(f"⚠️ {len(df)} ligne(s) trouvee(s) depuis 15h30 UTC le 28/10 :\n")
    for _, r in df.iterrows():
        vide = not any([r['tool'], r['prenom'], r['nom'], r['email'], r['telephone']])
        marqueur = " <-- CANDIDATE (tous champs identite vides)" if vide else ""
        print(f"  {r['timestamp']} | tool='{r['tool']}' | prenom='{r['prenom']}' | "
              f"nom='{r['nom']}' | email='{r['email']}' | tel='{r['telephone']}' | "
              f"source_page='{r['source_page']}'{marqueur}")


if __name__ == "__main__":
    main()
