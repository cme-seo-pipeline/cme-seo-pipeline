"""Point d'entree autonome -- remplace /synchroniser-leads-app. Lit depuis Firestore, ecrit vers BigQuery."""
import sys
from pipeline import rafraichir_leads_app_authentifies, init_bigquery

if __name__ == "__main__":
    try:
        client_bq = init_bigquery()
        nb = rafraichir_leads_app_authentifies(client_bq)
        print(f"Sync leads app terminee : {nb} leads")
    except Exception as e:
        print(f"Erreur : {e}")
        sys.exit(1)
