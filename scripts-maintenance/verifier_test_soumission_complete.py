"""
CME — Verifie le test de soumission reelle du mini-formulaire effectue
par l'operateur le 29/10/2026 au soir (confirmation empirique que
l'evenement 'termine' se declenche bien dans interactions_contenu,
suite au constat que l'instrumentation n'avait jamais ete testee en
conditions reelles depuis son deploiement le 28/10 15h19 UTC).

Verifie, sur les 20 dernieres minutes :
  1. La nouvelle ligne dans leads_convertis (tool='contact-expert-inline').
  2. La sequence complete dans interactions_contenu pour la session
     correspondante (form_vu, form_etape 0, puis etape suivante, et
     surtout 'termine').

LECTURE SEULE.
USAGE : python3 verifier_test_soumission_complete.py
"""
import json
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("=" * 80)
    print("1) Dernieres lignes leads_convertis (20 dernieres minutes)")
    print("=" * 80)
    df_leads = client.query(f"""
        SELECT timestamp, tool, prenom, nom, telephone, source_page, source_post_id, details
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 20 MINUTE)
        ORDER BY timestamp DESC
    """).to_dataframe()
    print(df_leads.to_string(index=False) if not df_leads.empty else "⚠️ Aucune ligne.")

    print("\n" + "=" * 80)
    print("2) Dernieres lignes interactions_contenu (20 dernieres minutes)")
    print("=" * 80)
    df_int = client.query(f"""
        SELECT timestamp, type_evenement, etape, silo, session_id, source_post_id
        FROM `{PROJECT_ID}.04_pipeline_seo.interactions_contenu`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 20 MINUTE)
        ORDER BY timestamp
    """).to_dataframe()
    print(df_int.to_string(index=False) if not df_int.empty else "⚠️ Aucune ligne.")

    print("\n" + "=" * 80)
    print("3) Verdict")
    print("=" * 80)
    if not df_int.empty and (df_int["etape"] == "termine").any():
        print("✅ 'termine' detecte -- l'instrumentation fonctionne bien de bout en bout.")
    else:
        print("❌ Aucun 'termine' trouve dans la fenetre -- a investiguer plus avant.")


if __name__ == "__main__":
    main()
