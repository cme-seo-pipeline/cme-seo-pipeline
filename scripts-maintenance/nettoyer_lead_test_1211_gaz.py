"""
CME — Nettoyage (DRY-RUN par defaut, --apply pour ecrire) d'un lead de test
signale par l'operateur le 12/11/2026, visible dans l'onglet Sheets
"Leads Formulaire Article" :

  11/12/2026 11:04:25 | test | 0695410020 | (email vide) | (CP vide) | gaz
  | position 1 | .../gaz/facture-gaz/facture-gaz-novembre-2026/
  | contact-expert-inline

Meme numero de test que tous les incidents precedents ("Lionel"/"QA-TEST"/
popup header, voir CLAUDE.md) : 0695410020. L'operateur nettoie le Sheet
correspondant lui-meme (pas d'acces API Sheets depuis ce sandbox, meme
precedent).

Cible par telephone + tool + article (pas par timestamp exact, inconnu
precisement cote BigQuery -- le Sheet affiche l'heure locale Europe/Paris,
le timestamp stocke en base est en UTC) pour rester robuste, tout en
restant tres specifique (numero de test + URL d'article precise).

USAGE :
  python3 nettoyer_lead_test_1211_gaz.py                  # dry-run
  python3 nettoyer_lead_test_1211_gaz.py --apply --attendu=1
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE_LEADS = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"
ARTICLE_URL = (
    "https://www.comprendre-mon-energie.fr/gaz/facture-gaz/"
    "facture-gaz-novembre-2026/"
)

FILTRE = f"""
    telephone = '0695410020' AND tool = 'contact-expert-inline'
    AND source_page = '{ARTICLE_URL}'
    AND DATE(timestamp) = '2026-11-12'
"""


def parse_args():
    apply_ = "--apply" in sys.argv
    attendu = None
    for arg in sys.argv:
        if arg.startswith("--attendu="):
            attendu = int(arg.split("=", 1)[1])
    return apply_, attendu


def main():
    apply_, attendu = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print("📋 Lignes candidates dans leads_convertis :")
    df = client.query(f"""
        SELECT timestamp, tool, prenom, telephone, source_page, details
        FROM `{TABLE_LEADS}` WHERE {FILTRE}
        ORDER BY timestamp
    """).to_dataframe()
    print(df.to_string(index=False) if len(df) else "  (aucune)")
    nb = len(df)
    print(f"\nTotal : {nb} ligne(s) candidate(s) a la suppression.")

    if not apply_:
        print("\n(dry-run -- aucune ecriture. Relancer avec --apply --attendu=N pour "
              "supprimer les N lignes.)")
        return

    if attendu is None or nb != attendu:
        sys.exit(f"❌ Garde-fou : {nb} lignes trouvees, --attendu={attendu} -- "
                 f"abandon sans ecrire.")

    print(f"\n✍️ Suppression de {nb} ligne(s) dans leads_convertis...")
    job = client.query(f"DELETE FROM `{TABLE_LEADS}` WHERE {FILTRE}")
    job.result()
    print(f"✅ {job.num_dml_affected_rows} ligne(s) supprimee(s) dans leads_convertis.")


if __name__ == "__main__":
    main()
