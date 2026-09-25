"""Point d'entree autonome -- remplace /synchroniser-clarity."""
import sys
from pipeline import rafraichir_clarity_insights, init_bigquery

if __name__ == "__main__":
    try:
        client_bq = init_bigquery()
        nb = rafraichir_clarity_insights(client_bq)
        print(f"Sync Clarity terminee : {nb} metriques")
    except Exception as e:
        print(f"Erreur : {e}")
        sys.exit(1)
