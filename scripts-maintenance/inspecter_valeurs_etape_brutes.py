"""
CME — Inspection brute (lecture seule) des valeurs de la colonne 'etape'
pour type_evenement='form_etape' dans interactions_contenu.

Contexte (29/10/2026, suite) : diagnostiquer_entonnoir_par_silo.py montre
etape='1' et etape='termine' quasi absents, alors que des soumissions
reelles ont eu lieu dans la meme fenetre (leads_convertis). Avant de
conclure a un probleme de timing sendBeacon, on verifie d'abord si les
valeurs existent sous une forme inattendue (casse, espaces, type) plutot
que d'etre simplement absentes.

LECTURE SEULE.
USAGE : python3 inspecter_valeurs_etape_brutes.py
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.interactions_contenu"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("1) Valeurs brutes de 'etape' pour type_evenement='form_etape' :")
    df = client.query(f"""
        SELECT etape, COUNT(*) AS nb
        FROM `{TABLE}`
        WHERE type_evenement = 'form_etape'
        GROUP BY etape
        ORDER BY nb DESC
    """).to_dataframe()
    print(df.to_string(index=False))

    print("\n2) Dernieres 15 lignes form_etape (tous champs utiles) :")
    df2 = client.query(f"""
        SELECT timestamp, etape, silo, position_contenu, session_id, source_post_id
        FROM `{TABLE}`
        WHERE type_evenement = 'form_etape'
        ORDER BY timestamp DESC
        LIMIT 15
    """).to_dataframe()
    print(df2.to_string(index=False))

    print("\n3) Sessions ayant au moins un etape='0' MAIS aucun etape<>'0' pour la meme session_id :")
    df3 = client.query(f"""
        WITH par_session AS (
          SELECT session_id,
                 COUNTIF(etape = '0') AS nb_etape0,
                 COUNTIF(etape != '0') AS nb_autres_etapes,
                 MIN(timestamp) AS premiere,
                 MAX(timestamp) AS derniere
          FROM `{TABLE}`
          WHERE type_evenement = 'form_etape'
          GROUP BY session_id
        )
        SELECT COUNT(*) AS nb_sessions_bloquees_etape0,
               (SELECT COUNT(*) FROM par_session) AS nb_sessions_total
        FROM par_session
        WHERE nb_etape0 > 0 AND nb_autres_etapes = 0
    """).to_dataframe()
    print(df3.to_string(index=False))


if __name__ == "__main__":
    main()
