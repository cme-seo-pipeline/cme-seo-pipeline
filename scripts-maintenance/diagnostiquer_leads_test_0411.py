"""
CME — Diagnostic (lecture seule) des leads de test generes le 04/11/2026
lors de la validation en conditions reelles du nouveau formulaire a un
seul ecran (wordpress-mu-plugins/cme-cta-progressifs.php, voir CLAUDE.md).
Meme numero de test que les precedents incidents ("Lionel"/"QA-TEST"/
popup header) : 0695410020.

Affiche TOUTES les lignes leads_convertis dont le telephone correspond
(peu importe le format de stockage -- zero initial ou non, voir piege
documente dans CLAUDE.md pour le popup header du 01/11), pour verifier :
- que les 3 soumissions de test sont bien capturees avec les bons champs
  (tool, prenom, telephone, details -- position/silo) ;
- qu'aucune autre ligne legitime ne partage ce numero par coincidence.

LECTURE SEULE -- aucune ecriture. Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 diagnostiquer_leads_test_0411.py
"""
from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"
TABLE_LEADS = f"{PROJECT_ID}.{DATASET_ID}.leads_convertis"
TABLE_INTERACTIONS = f"{PROJECT_ID}.{DATASET_ID}.interactions_contenu"

NUMERO_TEST = "0695410020"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("=" * 90)
    print(f"1/ Lignes leads_convertis avec telephone LIKE %{NUMERO_TEST[-9:]}%")
    print("=" * 90)
    df1 = client.query(f"""
        SELECT timestamp, tool, prenom, nom, telephone, details, source_page, source_post_id
        FROM `{TABLE_LEADS}`
        WHERE telephone LIKE '%{NUMERO_TEST[-9:]}%'
        ORDER BY timestamp
    """).to_dataframe()
    if df1.empty:
        print("  (aucune ligne trouvee)")
    else:
        for _, r in df1.iterrows():
            print(f"  {r['timestamp']} | tool={r['tool']:<24} | prenom={r['prenom']!r} | tel={r['telephone']!r} | details={r['details']} | post_id={r['source_post_id']}")
    print(f"\n  Total : {len(df1)} ligne(s).")

    print("\n" + "=" * 90)
    print("2/ Evenements form_etape='termine' du 04/11 (pour corroborer, meme fenetre)")
    print("=" * 90)
    df2 = client.query(f"""
        SELECT timestamp, cible, position_contenu, silo, source_post_id
        FROM `{TABLE_INTERACTIONS}`
        WHERE DATE(timestamp) = '2026-11-04'
          AND type_evenement = 'form_etape' AND etape = 'termine'
        ORDER BY timestamp
    """).to_dataframe()
    if df2.empty:
        print("  (aucun evenement termine le 04/11)")
    else:
        for _, r in df2.iterrows():
            print(f"  {r['timestamp']} | variante={r['cible']} | pos={r['position_contenu']} | {r['silo']} | post_id={r['source_post_id']}")
    print(f"\n  Total : {len(df2)} evenement(s).")


if __name__ == "__main__":
    main()
