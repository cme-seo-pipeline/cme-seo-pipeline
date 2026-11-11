"""
CME — Test (lecture seule) de la nouvelle cle SEARCH_API_KEY (rotee le
11/11/2026, cote GitHub Actions secret + Google Secret Manager version 11).

Appelle directement searchapi.io avec une requete anodine, exactement
comme le fait scraper_concurrents() dans pipeline/pipeline.py, pour
confirmer que la nouvelle cle est valide avant de relancer quoi que ce
soit d'autre qui en depend.

LECTURE SEULE -- aucune ecriture, aucun appel WordPress/BigQuery.

USAGE :
  python3 tester_nouvelle_cle_search_api.py
"""
import os
import sys

import requests

SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")
if not SEARCH_API_KEY:
    sys.exit("❌ SEARCH_API_KEY manquant dans l'environnement (ne jamais le coder en dur ici)")


def main():
    params = {
        "engine": "google",
        "q": "prix du gaz 2026",
        "gl": "fr",
        "hl": "fr",
        "api_key": SEARCH_API_KEY,
    }
    try:
        resp = requests.get("https://www.searchapi.io/api/v1/search", params=params, timeout=20)
    except requests.RequestException as e:
        sys.exit(f"❌ Erreur reseau : {e}")

    print(f"HTTP status : {resp.status_code}")
    try:
        donnees = resp.json()
    except ValueError:
        print(f"❌ Reponse non-JSON : {resp.text[:300]}")
        return

    if resp.status_code != 200:
        print(f"❌ Erreur API : {donnees.get('error', donnees)}")
        return

    resultats = donnees.get("organic_results", [])
    print(f"✅ Cle valide -- {len(resultats)} resultat(s) organique(s) recu(s).")
    if resultats:
        print(f"   1er resultat : {resultats[0].get('title', '')[:100]}")
    credits = donnees.get("search_metadata", {}).get("api_key_credits_used")
    if credits is not None:
        print(f"   Credits utilises pour cette requete : {credits}")


if __name__ == "__main__":
    main()
