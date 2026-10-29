"""
CME — Decompose l'entonnoir du mini-formulaire PAR SILO (lecture seule),
pour distinguer, silo par silo :
  1. form_vu    : le formulaire est-il VU (IntersectionObserver, seuil 50%) ?
  2. form_etape : progression (etape 0 = nom/prenom, etape 1 = telephone,
     'termine' = soumis).
  3. form_abandon : vu + engage mais jamais termine.

Objectif (demande operateur du 29/10/2026, suite au constat 0% conversion
sur le silo Aide energetique malgre 349 sessions/mois) : separer deux
hypotheses distinctes avant de decider d'une solution --
  (a) le formulaire n'est meme pas VU sur ce silo (probleme d'exposition :
      articles plus courts, moins de points d'insertion, structure HTML
      incompatible...) ;
  (b) le formulaire est vu et engage mais abandonne/jamais rempli
      (probleme d'adequation du message/valeur percue de la CTA avec
      l'intention de recherche du silo -- hypothese de l'operateur).
Ces deux diagnostics appellent des corrections tres differentes.

LECTURE SEULE -- aucune ecriture.
Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 diagnostiquer_entonnoir_par_silo.py
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

    print("=" * 90)
    print("Entonnoir du mini-formulaire par silo (depuis le debut de la collecte, 28/10)")
    print("=" * 90)
    df = client.query(f"""
        SELECT
            silo,
            COUNTIF(type_evenement = 'form_vu') AS vus,
            COUNTIF(type_evenement = 'form_etape' AND etape = '0') AS etape_0_nom,
            COUNTIF(type_evenement = 'form_etape' AND etape = '1') AS etape_1_tel,
            COUNTIF(type_evenement = 'form_etape' AND etape = 'termine') AS soumis,
            COUNTIF(type_evenement = 'form_abandon') AS abandons,
            COUNT(DISTINCT session_id) AS sessions_distinctes
        FROM `{TABLE}`
        WHERE silo IS NOT NULL AND silo != ''
        GROUP BY silo
        ORDER BY vus DESC
    """).to_dataframe()

    if df.empty:
        print("⚠️ Aucune donnee.")
        return

    print(df.to_string(index=False))

    print("\n" + "=" * 90)
    print("Taux d'engagement relatifs (sur la base des 'vus')")
    print("=" * 90)
    for _, row in df.iterrows():
        vus = row["vus"]
        if vus == 0:
            print(f"  {row['silo']:<25} : 0 vue -- rien a calculer (probleme d'EXPOSITION)")
            continue
        taux_etape1 = row["etape_1_tel"] / vus * 100
        taux_soumis = row["soumis"] / vus * 100
        print(f"  {row['silo']:<25} : vu={vus:>5} | atteint etape tel={taux_etape1:5.1f}% | soumis={taux_soumis:5.1f}% | abandons={row['abandons']}")


if __name__ == "__main__":
    main()
