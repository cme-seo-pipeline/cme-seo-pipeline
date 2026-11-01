"""
CME — Diagnostic LECTURE SEULE : pourquoi nettoyer_leads_test_popup_header.py
(filtre telephone='695410020') n'a trouve aucune ligne le 01/11/2026 alors
que les 2 leads de test sont bien visibles dans l'onglet Sheets "Leads
Formulaire Article". Hypothese a verifier : le numero stocke cote BigQuery
contient un 0 initial ("0695410020") que Google Sheets affiche sans (colonne
Telephone probablement interpretee comme un nombre, qui supprime les zeros
de tete a l'affichage) -- auquel cas le filtre exact du script de nettoyage
doit etre corrige.

Liste TOUTES les lignes leads_convertis du 01/11/2026, sans filtre sur le
telephone, pour voir la valeur exacte stockee.

USAGE : python3 diagnostiquer_leads_0111.py
"""
from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"


def main():
    client = bigquery.Client(project=PROJECT_ID)
    df = client.query(f"""
        SELECT timestamp, tool, prenom, telephone, source_post_id, source_page
        FROM `{TABLE}`
        WHERE DATE(timestamp) = '2026-11-01'
        ORDER BY timestamp
    """).to_dataframe()
    print(df.to_string(index=False) if len(df) else "(aucune ligne le 01/11/2026)")


if __name__ == "__main__":
    main()
