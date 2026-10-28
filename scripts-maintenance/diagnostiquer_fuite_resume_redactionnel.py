"""
CME — Diagnostic (lecture seule) : l'operateur a trouve, dans plusieurs
articles publies, un bloc de texte Markdown brut (non enveloppe en HTML)
ajoute par l'IA de redaction A LA FIN du contenu -- typiquement un
"Resume redactionnel" / "Respect des regles" auto-evaluant sa propre
conformite au prompt (nombre de mots, structure, verification des
regles...). Ce texte n'a rien a faire dans l'article publie : il pollue
visuellement la page (markdown brut non rendu : **gras**, listes, ✅).

Root cause identifiee par lecture de code (rediger_article(), pipeline.py
~ligne 3894-3910) : le nettoyage post-generation (retrait des ```html,
<!DOCTYPE>, <html>, <head>, <body> et troncature de tout ce qui PRECEDE
le premier tag de contenu) ne traite QUE le DEBUT du texte genere par
l'IA -- rien ne nettoie la FIN, donc un bloc de commentaire ajoute apres
la FAQ/les points cles passe integralement tel quel dans le payload
WordPress.

Ce script recherche, dans le contenu stocke de chaque article publie,
les marqueurs textuels les plus probables de cette fuite (variantes
avec/sans accents, le modele ne les formule pas toujours a l'identique).

Lecture seule -- aucune ecriture.

USAGE :
  python3 diagnostiquer_fuite_resume_redactionnel.py
  python3 diagnostiquer_fuite_resume_redactionnel.py --limite=50

Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.
"""
import os
import re
import sys

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)

MARQUEURS = [
    r"r[ée]sum[ée]\s+[ée]ditorial",
    r"r[ée]sum[ée]\s+r[ée]dactionnel",
    r"respect\s+des\s+r[èe]gles\s*:",
    r"r[èe]gles\s+respect[ée]es\s*:",
    r"✅.{0,40}(html|maillage|apostrophe|cta|chiffre)",  # checkmark ✅ suivi d'un mot-cle de regle
]
PATTERN = re.compile("|".join(MARQUEURS), re.IGNORECASE)


def parse_args():
    limite = None
    for arg in sys.argv:
        if arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])
    return limite


def lister_tous_les_posts(limite=None):
    posts = []
    page = 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            auth=AUTH,
            params={"per_page": 100, "page": page, "status": "publish", "context": "edit"},
            timeout=30,
        )
        if r.status_code != 200:
            print(f"  ⚠️ Arret pagination a la page {page} : HTTP {r.status_code}")
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if limite and len(posts) >= limite:
            return posts[:limite]
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
    return posts


def main():
    limite = parse_args()
    print("📥 Recuperation des articles publies (API REST WordPress)...")
    posts = lister_tous_les_posts(limite)
    print(f"  ✅ {len(posts)} articles\n")

    touches = []
    for post in posts:
        contenu = post["content"]["raw"] if "raw" in post.get("content", {}) else post["content"]["rendered"]
        m = PATTERN.search(contenu)
        if m:
            idx = m.start()
            extrait = contenu[max(0, idx - 30):idx + 150].replace("\n", " ")
            touches.append((post["id"], post["link"], extrait))

    print(f"{'='*70}")
    print(f"RAPPORT — FUITE 'RESUME REDACTIONNEL' ({len(touches)}/{len(posts)} articles)")
    print(f"{'='*70}")
    for pid, url, extrait in touches:
        print(f"\n  post_id={pid} | {url}")
        print(f"    ...{extrait}...")


if __name__ == "__main__":
    main()
