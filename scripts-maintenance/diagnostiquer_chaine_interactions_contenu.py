"""
CME — Diagnostic ponctuel (lecture seule) : pourquoi interactions_contenu
est vide (0 ligne) alors que le mecanisme a ete documente comme "deploye
et valide" le 26/10/2026. Verifie les 3 maillons de la chaine, dans
l'ordre, sans rien ecrire :

  1. Le code JS live sur le site contient-il bien les nouveaux trackers
     (journaliserInteraction/prefixeSilo) -- confirme ou infirme que le
     mu-plugin cPanel a vraiment ete mis a jour depuis le 26/10 (rappel :
     ce fichier n'est PAS versionne automatiquement sur le serveur, cf.
     CLAUDE.md -- upload cPanel manuel requis apres chaque modification).
  2. Le relais WordPress /wp-json/cme/v1/log-interaction repond-il (existe
     -- cote PHP, versionne par le MEME fichier que le point 1).
  3. L'endpoint Cloud Run /api/log-interaction repond-il (existe cote
     service deploye -- rappel : pas de CI/CD Cloud Run dans ce repo,
     gcloud run deploy est une action operateur manuelle).

Lecture seule -- aucune ecriture, aucune donnee de test envoyee.

USAGE :
  python3 diagnostiquer_chaine_interactions_contenu.py
"""
import re
import sys

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
CLOUD_RUN_URL = "https://cme-tracking-api-217943559750.europe-west1.run.app"


def main():
    print("="*70)
    print("MAILLON 1 — Code JS live sur un article (mu-plugin cPanel a jour ?)")
    print("="*70)
    try:
        # Un article recent connu pour avoir le mini-formulaire + le tracker clics
        r = requests.get(f"{WP_URL}/solaire/kit-solaire/kit-solaire-vs-panneau-solaire-seul-comparatif/", timeout=20)
        html = r.text
        for fonction in ["journaliserInteraction", "prefixeSilo", "viderInteractions", "CME_POST_ID"]:
            present = fonction in html
            print(f"  {'✅' if present else '❌'} '{fonction}' {'trouve' if present else 'ABSENT'} dans le HTML live")
    except Exception as e:
        print(f"  ⚠️ Erreur de lecture de la page : {e}")

    print(f"\n{'='*70}")
    print("MAILLON 2 — Relais WordPress /wp-json/cme/v1/log-interaction")
    print(f"{'='*70}")
    try:
        # GET volontaire (la route n'accepte que POST) : on veut juste savoir
        # si la route EXISTE (404 = absente, autre code = presente).
        r = requests.get(f"{WP_URL}/wp-json/cme/v1/log-interaction", timeout=20)
        print(f"  GET -> HTTP {r.status_code}")
        if r.status_code == 404:
            print("  ❌ Route absente -- le mu-plugin cPanel ne contient probablement pas ce relais")
        else:
            print("  ✅ Route presente (404 attendu uniquement si absente)")
        print(f"  Corps (200 premiers caracteres) : {r.text[:200]}")
    except Exception as e:
        print(f"  ⚠️ Erreur : {e}")

    print(f"\n{'='*70}")
    print("MAILLON 3 — Endpoint Cloud Run /api/log-interaction")
    print(f"{'='*70}")
    try:
        r = requests.get(f"{CLOUD_RUN_URL}/api/log-interaction", timeout=20)
        print(f"  GET -> HTTP {r.status_code}")
        if r.status_code == 404:
            print("  ❌ Route absente sur le service Cloud Run deploye -- /api/log-interaction")
            print("     n'a probablement jamais ete redeploye (gcloud run deploy, action operateur)")
        else:
            print("  ✅ Route presente (404 attendu uniquement si absente)")
        print(f"  Corps (200 premiers caracteres) : {r.text[:200]}")
    except Exception as e:
        print(f"  ⚠️ Erreur : {e}")

    print(f"\n{'='*70}")
    print("MAILLON 3bis — Comparaison avec une route Cloud Run connue fonctionnelle")
    print(f"{'='*70}")
    try:
        r = requests.get(f"{CLOUD_RUN_URL}/api/log-lead", timeout=20)
        print(f"  GET {CLOUD_RUN_URL}/api/log-lead -> HTTP {r.status_code} (reference, route confirmee en prod)")
    except Exception as e:
        print(f"  ⚠️ Erreur : {e}")


if __name__ == "__main__":
    main()
