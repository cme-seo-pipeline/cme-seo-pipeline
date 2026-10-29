"""
CME — Nettoyage (DRY-RUN par defaut, --apply pour ecrire) du test de
soumission reelle effectue par l'operateur le 29/10/2026 au soir, pour
valider que l'instrumentation form_etape/'termine' fonctionne de bout en
bout (confirme par verifier_test_soumission_complete.py).

Supprime :
  1. leads_convertis : la ligne test diagnostic (prenom='test diagnostic',
     telephone='0695410020', timestamp 2026-10-29 22:26:53.724890 UTC).
  2. interactions_contenu : toutes les lignes de la session correspondante
     (session_id='mvu44pcwrpbvze', 16 lignes attendues).

Garde-fous : filtre precis sur l'horodatage exact pour leads_convertis
(comme pour les nettoyages precedents de ce type), et sur le session_id
exact pour interactions_contenu -- refuse d'ecrire si le nombre de lignes
trouvees ne correspond pas a --attendu-leads/--attendu-interactions.

USAGE :
  python3 nettoyer_test_soumission_complete.py                                    # dry-run
  python3 nettoyer_test_soumission_complete.py --apply --attendu-leads=1 --attendu-interactions=16
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE_LEADS = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"
TABLE_INTERACTIONS = f"{PROJECT_ID}.04_pipeline_seo.interactions_contenu"

FILTRE_LEAD = """
    TIMESTAMP(timestamp) = TIMESTAMP('2026-10-29 22:26:53.724890')
    AND tool = 'contact-expert-inline'
    AND LOWER(prenom) = 'test diagnostic'
    AND telephone = '0695410020'
"""
SESSION_ID_TEST = "mvu44pcwrpbvze"


def parse_args():
    apply_ = "--apply" in sys.argv
    attendu_leads = attendu_interactions = None
    for arg in sys.argv:
        if arg.startswith("--attendu-leads="):
            attendu_leads = int(arg.split("=", 1)[1])
        if arg.startswith("--attendu-interactions="):
            attendu_interactions = int(arg.split("=", 1)[1])
    return apply_, attendu_leads, attendu_interactions


def main():
    apply_, attendu_leads, attendu_interactions = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print("📋 1) Ligne candidate dans leads_convertis :")
    df_leads = client.query(f"""
        SELECT timestamp, prenom, telephone, source_post_id
        FROM `{TABLE_LEADS}` WHERE {FILTRE_LEAD}
    """).to_dataframe()
    print(df_leads.to_string(index=False))
    nb_leads = len(df_leads)

    print(f"\n📋 2) Lignes candidates dans interactions_contenu (session_id='{SESSION_ID_TEST}') :")
    df_int = client.query(f"""
        SELECT timestamp, type_evenement, etape
        FROM `{TABLE_INTERACTIONS}` WHERE session_id = '{SESSION_ID_TEST}'
        ORDER BY timestamp
    """).to_dataframe()
    print(df_int.to_string(index=False))
    nb_int = len(df_int)

    print(f"\nTotal : {nb_leads} ligne(s) leads_convertis, {nb_int} ligne(s) interactions_contenu")

    if not apply_:
        print("\n(dry-run -- aucune ecriture. Relancer avec --apply --attendu-leads=N --attendu-interactions=M.)")
        return

    if attendu_leads is None or nb_leads != attendu_leads:
        sys.exit(f"❌ Garde-fou leads : {nb_leads} trouvees, --attendu-leads={attendu_leads} -- abandon.")
    if attendu_interactions is None or nb_int != attendu_interactions:
        sys.exit(f"❌ Garde-fou interactions : {nb_int} trouvees, --attendu-interactions={attendu_interactions} -- abandon.")

    print(f"\n✍️ Suppression de {nb_leads} ligne(s) leads_convertis...")
    job1 = client.query(f"DELETE FROM `{TABLE_LEADS}` WHERE {FILTRE_LEAD}")
    job1.result()
    print(f"✅ {job1.num_dml_affected_rows} ligne(s) supprimee(s) dans leads_convertis.")

    print(f"✍️ Suppression de {nb_int} ligne(s) interactions_contenu...")
    job2 = client.query(f"DELETE FROM `{TABLE_INTERACTIONS}` WHERE session_id = '{SESSION_ID_TEST}'")
    job2.result()
    print(f"✅ {job2.num_dml_affected_rows} ligne(s) supprimee(s) dans interactions_contenu.")


if __name__ == "__main__":
    main()
