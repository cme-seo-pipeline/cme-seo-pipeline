"""Point d'entree autonome pour GitHub Actions -- remplace l'endpoint Flask /run de server.py pour l'execution planifiee. Meme fonction sous-jacente (run_pipeline), execution synchrone directe (pas de thread, pas de serveur HTTP), adaptee a un job qui doit se terminer proprement et remonter un code d'erreur clair en cas d'echec."""
import sys
from pipeline import run_pipeline

if __name__ == "__main__":
    force = "--force" in sys.argv
    try:
        run_pipeline(force=force)
    except Exception as e:
        print(f"Erreur pipeline : {e}")
        sys.exit(1)
