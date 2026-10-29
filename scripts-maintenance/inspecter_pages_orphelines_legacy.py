"""
CME — Suite de inspecter_pages_orphelines.py (lecture seule) : les 2 pages
orphelines "legacy" (post_id=4354 et 699, anterieures au pipeline actuel,
absentes de historique_publications) n'ont pas de sous_silo_strategique
propre a elles-memes -- on cherche donc les candidats directement par
silo + mot-cle thematique dans le titre, parmi les articles DU PIPELINE
(qui ont un historique) et qui sont les plus a meme de les citer.

Cible 1 : post_id=4354, /electricite/compteur/consommation-electrique-mesure-optimisation/
  -> candidats attendus : sous-silo "Compteur" (lecture/fonctionnement du
     compteur), silo Électricité.
Cible 2 : post_id=699, /electricite/facture-electricite/justificatif-de-domicile/
  -> candidats attendus : sous-silo "Facture Électricité", + recherche du
     mot "attestation" (lien thematique direct avec justificatif de
     domicile) dans le titre.

LECTURE SEULE -- aucune ecriture.
USAGE : python3 inspecter_pages_orphelines_legacy.py
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("=" * 100)
    print("CIBLE 1 : consommation-electrique-mesure-optimisation (post_id=4354)")
    print("=" * 100)
    df1 = client.query(f"""
        SELECT post_id, titre, url_wp, date_publication, sous_silo_strategique
        FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
        WHERE silo LIKE '%lectricit%'
          AND sous_silo_strategique LIKE 'Compteur%'
        ORDER BY date_publication DESC
        LIMIT 10
    """).to_dataframe()
    print(df1.to_string(index=False) if not df1.empty else "  (aucun resultat)")

    print()
    print("=" * 100)
    print("CIBLE 2 : justificatif-de-domicile (post_id=699)")
    print("=" * 100)
    print("\n  → Sous-silo 'Facture Électricité' (recents) :")
    df2 = client.query(f"""
        SELECT post_id, titre, url_wp, date_publication
        FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
        WHERE silo LIKE '%lectricit%'
          AND sous_silo_strategique LIKE 'Facture %lectricit%'
        ORDER BY date_publication DESC
        LIMIT 8
    """).to_dataframe()
    print(df2.to_string(index=False) if not df2.empty else "  (aucun resultat)")

    print("\n  → Titres contenant 'attestation' ou 'justificatif' (tous silos) :")
    df3 = client.query(f"""
        SELECT post_id, titre, url_wp, silo, sous_silo_strategique, date_publication
        FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
        WHERE LOWER(titre) LIKE '%attestation%' OR LOWER(titre) LIKE '%justificatif%'
        ORDER BY date_publication DESC
        LIMIT 10
    """).to_dataframe()
    print(df3.to_string(index=False) if not df3.empty else "  (aucun resultat)")


if __name__ == "__main__":
    main()
