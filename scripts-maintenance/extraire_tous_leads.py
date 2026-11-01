"""
CME — Extraction complete de tous les leads de leads_convertis (lecture
seule), demande operateur du 01/11/2026, pour comparaison manuelle avec
le classeur Google Sheets de suivi (SPREADSHEET_ID
1LBgHQPioaT0buv9rev5egywRDtE8hKIFHFVwjNqw00o, un onglet par source --
Leads Formulaire Article, et les onglets des 3 anciens simulateurs/
espace client, cf. CLAUDE.md).

Imprime TOUTES les colonnes de la table (lues dynamiquement via
INFORMATION_SCHEMA, pas une liste figee -- le schema peut evoluer),
une ligne par lead, au format pipe-delimited (`|`) precede d'une ligne
d'en-tete, pour un parsing fiable cote sandbox malgre des champs texte
pouvant contenir des virgules.

LECTURE SEULE -- aucune ecriture.
Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 extraire_tous_leads.py
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

    df_cols = client.query(f"""
        SELECT column_name
        FROM `{PROJECT_ID}.{DATASET_ID}`.INFORMATION_SCHEMA.COLUMNS
        WHERE table_name = 'leads_convertis'
        ORDER BY ordinal_position
    """).to_dataframe()
    colonnes = df_cols["column_name"].tolist()
    print(f"# Colonnes ({len(colonnes)}) : {colonnes}")

    df = client.query(f"""
        SELECT {', '.join(colonnes)}
        FROM `{PROJECT_ID}.{DATASET_ID}.leads_convertis`
        ORDER BY timestamp
    """).to_dataframe()

    print(f"# Total lignes : {len(df)}")
    if df.empty:
        return
    print(f"# Plage de dates : {df['timestamp'].min()} -> {df['timestamp'].max()}")

    print("\n=== DEBUT EXPORT ===")
    print("|".join(colonnes))
    for _, row in df.iterrows():
        valeurs = []
        for c in colonnes:
            v = row[c]
            v = "" if v is None else str(v)
            v = v.replace("|", "/").replace("\n", " ").replace("\r", " ")
            valeurs.append(v)
        print("|".join(valeurs))
    print("=== FIN EXPORT ===")


if __name__ == "__main__":
    main()
