"""Point d'entree autonome GitHub Actions -- remplace l'endpoint Flask /rafraichir-indicateurs. Rafraichit les indicateurs reglementaires (CRE/ANAH) puis publie un article dedie SI un changement reel est detecte."""
import sys
from datetime import datetime
from pipeline import (
    rafraichir_indicateurs_reglementaires, publier_actualites_reglementaires,
    init_bigquery, CONFIG, WP_CONFIG
)

if __name__ == "__main__":
    try:
        client_bq = init_bigquery()
        nb = rafraichir_indicateurs_reglementaires(client_bq)
        print(f"Indicateurs rafraichis : {nb} lignes")
        run_id = datetime.now().strftime("%Y%m%d_%H%M")
        publier_actualites_reglementaires(client_bq, CONFIG, WP_CONFIG, run_id)
    except Exception as e:
        print(f"Erreur : {e}")
        sys.exit(1)
