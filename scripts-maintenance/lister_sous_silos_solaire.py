"""
CME — Liste les sous-silos reels du silo Solaire (clarification demandee par
l'operateur le 26/10/2026 : le chantier page-pilier + 2 nouveaux articles
porte sur les SOUS-silos de Solaire, pas sur les 5 silos principaux du
site). Derive le sous-silo directement depuis wp_url_mapping (2e segment
d'URL apres /solaire/), pour couvrir TOUS les articles solaire publies, pas
seulement ceux ayant des donnees GSC.

LECTURE SEULE. Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    sql = f"""
    WITH solaire AS (
      SELECT
        post_id, url,
        REGEXP_EXTRACT(LOWER(url), r'/solaire/([a-z0-9-]+)/') AS sous_silo
      FROM `{PROJECT_ID}.02_cleaned.wp_url_mapping`
      WHERE REGEXP_CONTAINS(LOWER(url), r'/solaire/')
    )
    SELECT sous_silo, COUNT(*) AS nb_articles, ARRAY_AGG(url ORDER BY url LIMIT 5) AS exemples
    FROM solaire
    GROUP BY sous_silo
    ORDER BY nb_articles DESC
    """
    print("=" * 90)
    print("Sous-silos reels du silo Solaire (2e segment d'URL, wp_url_mapping)")
    print("=" * 90)
    try:
        df = client.query(sql).to_dataframe()
        print(df.to_string(index=False))
    except Exception as e:
        print(f"❌ Erreur SQL : {e}")


if __name__ == "__main__":
    main()
