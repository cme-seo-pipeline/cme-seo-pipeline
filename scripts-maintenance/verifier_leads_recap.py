"""
CME — Recap general des leads dans BigQuery (leads_convertis).

Demande operateur du 24/10/2026 : verification generale des leads cote
BigQuery en debut de session, sans cibler un outil en particulier. Ce
script donne une vue d'ensemble plutot qu'un check mono-outil comme
verifier_leads_formulaire_inline.py (contact-expert-inline uniquement) ou
verifier_tracking_conversion_recent.py (contact-expert-formulaire /
appel-telephone uniquement) :

1. Volume quotidien par outil sur les 14 derniers jours (detecte un canal
   qui se serait tu silencieusement, ex. regression IAM comme l'incident
   du 19/10 documente dans CLAUDE.md).
2. Dernieres 15 lignes toutes sources confondues (verifie que la table
   repond et que les champs cles ne sont pas vides en ecriture recente).
3. Qualite des champs recents pour les leads du nouveau formulaire inline
   (contact-expert-inline) : taux de remplissage de source_page et
   source_post_id, pour s'assurer que le correctif du 22/10 (ajout de
   source_page) tient dans le temps.

LECTURE SEULE. Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement
(fourni par le runner GitHub Actions via maintenance-a-la-demande.yml).
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("=" * 70)
    print("1) Volume par outil et par jour -- 14 derniers jours")
    print("=" * 70)
    try:
        df = client.query(f"""
            SELECT DATE(timestamp) AS jour, tool, COUNT(*) AS nb
            FROM `{TABLE}`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 14 DAY)
            GROUP BY jour, tool
            ORDER BY jour DESC, tool
        """).to_dataframe()
        if df.empty:
            print("⚠️ Aucune ligne sur les 14 derniers jours, toutes sources confondues.")
        else:
            print(df.to_string(index=False))
    except Exception as e:
        print(f"⚠️ Erreur requete (1) : {e}")

    print("\n" + "=" * 70)
    print("2) Dernieres 15 lignes toutes sources confondues")
    print("=" * 70)
    try:
        df2 = client.query(f"""
            SELECT timestamp, tool, telephone, email, source_page, source_post_id
            FROM `{TABLE}`
            ORDER BY timestamp DESC
            LIMIT 15
        """).to_dataframe()
        print(df2.to_string(index=False))
    except Exception as e:
        print(f"⚠️ Erreur requete (2) : {e}")

    print("\n" + "=" * 70)
    print("3) Qualite des champs -- contact-expert-inline, 7 derniers jours")
    print("=" * 70)
    try:
        df3 = client.query(f"""
            SELECT
                COUNT(*) AS nb_total,
                COUNTIF(source_page IS NOT NULL AND source_page != '') AS nb_source_page_ok,
                COUNTIF(source_post_id IS NOT NULL AND source_post_id != '') AS nb_source_post_id_ok,
                MIN(timestamp) AS premiere,
                MAX(timestamp) AS derniere
            FROM `{TABLE}`
            WHERE tool = 'contact-expert-inline'
              AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        """).to_dataframe()
        print(df3.to_string(index=False))
    except Exception as e:
        print(f"⚠️ Erreur requete (3) : {e}")


if __name__ == "__main__":
    main()
