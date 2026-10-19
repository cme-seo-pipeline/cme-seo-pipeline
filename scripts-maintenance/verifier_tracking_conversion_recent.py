"""
CME — Verification live du tracking de conversion (formulaire contact +
clic telephone), suite au deploiement de
wordpress-mu-plugins/cme-tracking-conversion.php confirme en prod le
19/10/2026 (script present dans le <head>/<body> de
/contactez-un-expert/, verifie via curl+grep).

Objectif : confirmer que le chemin serveur fonctionne reellement de bout
en bout (clic/soumission -> POST /api/log-lead -> table BigQuery), pas
seulement que le JS est bien injecte dans la page. LECTURE SEULE.

Ne prouve rien si 0 ligne : signifie soit qu'aucun visiteur n'a encore
soumis le formulaire / clique sur le numero depuis le deploiement, soit
que le tracking ne fonctionne pas -- a re-executer apres un test manuel
(soumettre le formulaire une fois, cliquer une fois sur le numero en
header) pour lever l'ambiguite.

Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
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
    print("Evenements 'contact-expert-formulaire' / 'appel-telephone' -- 7 derniers jours")
    print("=" * 70)
    try:
        df = client.query(f"""
            SELECT timestamp, tool, source_page, telephone, email
            FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
            WHERE tool IN ('contact-expert-formulaire', 'appel-telephone')
              AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
            ORDER BY timestamp DESC
            LIMIT 50
        """).to_dataframe()
        if df.empty:
            print("⚠️ Aucune ligne sur les 7 derniers jours pour ces deux outils.")
            print("   -> Normal si personne n'a encore soumis le formulaire ni clique sur")
            print("      le numero depuis le deploiement du mu-plugin. Pas concluant seul :")
            print("      faire un test manuel (soumettre le formulaire une fois, cliquer")
            print("      une fois sur le tel: du header) puis relancer ce script.")
        else:
            print(f"✅ {len(df)} evenement(s) trouve(s) :")
            print(df.to_string())
    except Exception as e:
        print(f"⚠️ Erreur : {e}")

    print("\n" + "=" * 70)
    print("Pour comparaison -- dernieres lignes toutes sources confondues (verifie que la table repond)")
    print("=" * 70)
    try:
        df2 = client.query(f"""
            SELECT timestamp, tool
            FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
            ORDER BY timestamp DESC
            LIMIT 5
        """).to_dataframe()
        print(df2.to_string())
    except Exception as e:
        print(f"⚠️ Erreur : {e}")


if __name__ == "__main__":
    main()
