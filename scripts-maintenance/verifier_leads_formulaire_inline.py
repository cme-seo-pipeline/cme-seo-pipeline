"""
CME — Verification live du mini-formulaire integre aux articles
(wordpress-mu-plugins/cme-cta-progressifs.php, chantier du 22/10/2026).

L'operateur confirme recevoir des lignes dans l'onglet Google Sheets
"Leads Formulaire Article" apres un test reel. Ce script verifie
l'AUTRE moitie du double-ecriture (cme_relayer_log_lead() dans
cme-tracking-conversion.php republie vers Cloud Run ET, separement,
vers l'Apps Script Sheets) : confirme que la meme soumission arrive
aussi dans BigQuery (leads_convertis, tool='contact-expert-inline'),
pour s'assurer que les deux destinations recoivent bien la meme donnee
et qu'aucune des deux n'est en silence.

LECTURE SEULE. Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("=" * 70)
    print("Leads 'contact-expert-inline' -- 48 dernieres heures")
    print("=" * 70)
    df = client.query(f"""
        SELECT timestamp, prenom, telephone, email, code_postal, source_page, source_post_id, details
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE tool = 'contact-expert-inline'
          AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 48 HOUR)
        ORDER BY timestamp DESC
        LIMIT 20
    """).to_dataframe()

    if df.empty:
        print("   (0 ligne -- soit aucun test recent, soit le relais Cloud Run ne recoit plus rien)")
    else:
        print(df.to_string())
        print(f"\n   {len(df)} ligne(s) trouvee(s).")


if __name__ == "__main__":
    main()
