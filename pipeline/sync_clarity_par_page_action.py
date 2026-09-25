"""Point d'entree autonome -- remplace /synchroniser-clarity-par-page."""
import sys
from pipeline import rafraichir_clarity_par_page, init_bigquery

if __name__ == "__main__":
    try:
        client_bq = init_bigquery()
        nb = rafraichir_clarity_par_page(client_bq)
        print(f"Sync Clarity par page terminee : {nb} lignes")
    except Exception as e:
        print(f"Erreur : {e}")
        sys.exit(1)
