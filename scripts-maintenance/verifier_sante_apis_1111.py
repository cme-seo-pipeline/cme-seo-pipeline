"""
CME — Verification de l'etat reel des APIs utilisees par le pipeline,
avec un focus sur Mode Actualite (publier_actualites_reglementaires,
declenche par sync-indicateurs.yml), demande explicite de l'operateur
le 11/11/2026 suite au chantier CTA/formulaires : "est ce que ce systeme
fonctionne encore et est-ce que les APIs fonctionnent toujours".

Mode Actualite n'appelle QUE : BigQuery (lecture indicateurs + anti-
doublon), Anthropic (redaction), l'API REST WordPress (publication), et
OpenAI (image mise en avant, generer_featured_images) -- CONTOURNE
deliberement SearchApi.io (pas de scraping concurrent, voir le docblock
de publier_actualites_reglementaires). SearchApi.io n'est donc PAS une
dependance de ce mode precis, mais reste testee ici pour le contexte
general du pipeline (cause confirmee des echecs de publication-
quotidienne.yml du 02 au 09/11).

Chaque test est un appel minimal, non destructif, au cout le plus bas
possible (pas d'ecriture, pas de generation couteuse).

LECTURE SEULE (aucune ecriture nulle part, aucune publication).
"""
import os

import requests
from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"


def tester_bigquery():
    print("=" * 70)
    print("BigQuery")
    print("=" * 70)
    try:
        client = bigquery.Client(project=PROJECT_ID)
        df = client.query("SELECT 1 AS ok").to_dataframe()
        print(f"  ✅ Requete SELECT 1 : OK ({df.iloc[0]['ok']})")
    except Exception as e:
        print(f"  ❌ Erreur : {e}")


def tester_anthropic():
    print()
    print("=" * 70)
    print("Anthropic API (api.anthropic.com)")
    print("=" * 70)
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        print("  ❌ ANTHROPIC_API_KEY absente de l'environnement")
        return
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Reponds juste: OK"}],
            },
            timeout=30,
        )
        print(f"  HTTP {r.status_code}")
        if r.status_code == 200:
            texte = r.json()["content"][0]["text"]
            print(f"  ✅ Reponse recue : {texte!r}")
        else:
            print(f"  ❌ Corps : {r.text[:500]}")
    except Exception as e:
        print(f"  ❌ Exception : {e}")


def tester_openai():
    print()
    print("=" * 70)
    print("OpenAI API (images mises en avant)")
    print("=" * 70)
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        print("  ❌ OPENAI_API_KEY absente de l'environnement")
        return
    try:
        # Appel le moins cher possible : lister les modeles (pas de
        # generation d'image reelle, juste une verification d'auth/quota).
        r = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        )
        print(f"  HTTP {r.status_code}")
        if r.status_code == 200:
            n = len(r.json().get("data", []))
            print(f"  ✅ Authentification OK ({n} modeles listes)")
        else:
            print(f"  ❌ Corps : {r.text[:500]}")
    except Exception as e:
        print(f"  ❌ Exception : {e}")


def tester_wordpress():
    print()
    print("=" * 70)
    print("API REST WordPress (publication)")
    print("=" * 70)
    user = os.environ.get("WP_USERNAME", "")
    pwd = os.environ.get("WP_APP_PASSWORD", "")
    if not user or not pwd:
        print("  ❌ WP_USERNAME / WP_APP_PASSWORD absents de l'environnement")
        return
    try:
        # Lecture seule : verifie l'authentification Application Password
        # sans rien publier ni modifier (endpoint /users/me).
        r = requests.get(
            "https://www.comprendre-mon-energie.fr/wp-json/wp/v2/users/me",
            auth=(user, pwd),
            timeout=30,
        )
        print(f"  HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  ✅ Authentifie en tant que : {data.get('name')} (id={data.get('id')})")
        else:
            print(f"  ❌ Corps : {r.text[:500]}")
    except Exception as e:
        print(f"  ❌ Exception : {e}")


def tester_searchapi():
    print()
    print("=" * 70)
    print("SearchApi.io (contexte general -- PAS utilise par Mode Actualite)")
    print("=" * 70)
    key = os.environ.get("SEARCH_API_KEY", "")
    if not key:
        print("  ❌ SEARCH_API_KEY absente de l'environnement")
        return
    try:
        r = requests.get(
            "https://www.searchapi.io/api/v1/search",
            params={"engine": "google", "q": "test", "api_key": key, "num": 1},
            timeout=30,
        )
        print(f"  HTTP {r.status_code}")
        if r.status_code == 200:
            print("  ✅ Requete de recherche OK (quota disponible)")
        else:
            print(f"  ❌ Corps : {r.text[:500]}")
    except Exception as e:
        print(f"  ❌ Exception : {e}")


if __name__ == "__main__":
    tester_bigquery()
    tester_anthropic()
    tester_openai()
    tester_wordpress()
    tester_searchapi()
