"""Point d'entree autonome GitHub Actions -- remplace l'endpoint Flask /auditer-articles. Audite tous les articles publies et corrige automatiquement toute citation reglementaire devenue obsolete."""
import sys
from pipeline import auditer_et_corriger_articles, init_bigquery, CONFIG, WP_CONFIG

if __name__ == "__main__":
    try:
        client_bq = init_bigquery()
        resultat = auditer_et_corriger_articles(client_bq, CONFIG, WP_CONFIG)
        print(f"Audit articles termine : {resultat}")
    except Exception as e:
        print(f"Erreur : {e}")
        sys.exit(1)
