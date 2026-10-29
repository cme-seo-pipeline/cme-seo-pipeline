"""
CME — Liste complete et detaillee des leads dans BigQuery (leads_convertis).

Demande operateur du 29/10/2026 : voir la liste complete des leads (pas
seulement un recap agrege par outil/jour comme verifier_leads_recap.py),
avec tous les champs utiles, avant de donner le feu vert sur les chantiers
en attente. Objectif : permettre a l'operateur de distinguer lui-meme les
vrais leads des lignes de test avant toute action.

LECTURE SEULE -- aucune ecriture, aucune suppression.
Necessite GOOGLE_APPLICATION_CREDENTIALS (fourni par le runner GitHub
Actions via maintenance-a-la-demande.yml).

USAGE :
  python3 lister_tous_les_leads.py                  # toutes les lignes (table entiere)
  python3 lister_tous_les_leads.py --jours=30        # limite a une fenetre
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"


def parse_args():
    jours = None
    for arg in sys.argv:
        if arg.startswith("--jours="):
            jours = int(arg.split("=", 1)[1])
    return jours


def main():
    jours = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    filtre_jours = (
        f"WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {jours} DAY)"
        if jours else ""
    )

    print("=" * 100)
    print(f"LISTE COMPLETE DES LIGNES -- leads_convertis" + (f" (derniers {jours}j)" if jours else " (table entiere)"))
    print("=" * 100)
    df = client.query(f"""
        SELECT
            timestamp, tool, prenom, nom, telephone, email,
            code_postal, adresse, source_page, source_post_id, details
        FROM `{TABLE}`
        {filtre_jours}
        ORDER BY timestamp DESC
    """).to_dataframe()

    if df.empty:
        print("⚠️ Aucune ligne.")
        return

    print(f"\nTotal : {len(df)} lignes\n")
    print("-" * 100)
    print("Repartition par outil (table entiere consultee) :")
    print(df["tool"].value_counts().to_string())
    print("-" * 100)

    for _, row in df.iterrows():
        nom_complet = " ".join(x for x in [row["prenom"], row["nom"]] if x).strip() or "(vide)"
        print(f"\n[{row['timestamp']}] outil={row['tool'] or '(vide)'}")
        print(f"  nom/prenom     : {nom_complet}")
        print(f"  telephone      : {row['telephone'] or '(vide)'}")
        print(f"  email          : {row['email'] or '(vide)'}")
        print(f"  code_postal    : {row['code_postal'] or '(vide)'}  | adresse : {row['adresse'] or '(vide)'}")
        print(f"  source_page    : {row['source_page'] or '(vide)'}")
        print(f"  source_post_id : {row['source_post_id'] or '(vide)'}")
        if row["details"] and row["details"] != "{}":
            print(f"  details        : {row['details']}")


if __name__ == "__main__":
    main()
