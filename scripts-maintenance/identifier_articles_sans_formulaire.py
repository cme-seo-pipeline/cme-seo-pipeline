"""
CME — Identification des articles publies pour lesquels le mini-formulaire
progressif (cme-cta-progressifs.php) ne s'afficherait PAS, demande
operateur du 28/10/2026.

Piege methodologique evite ici : le formulaire est injecte cote CLIENT
par du JavaScript (fonction demarrer()/creer() dans cme-cta-progressifs.php),
jamais dans le contenu stocke de l'article -- un simple `requests.get` +
parsing HTML NE VOIT PAS le formulaire, puisque requests n'execute aucun
JS. Executer un vrai navigateur (Playwright) sur 850+ pages depuis un
runner GitHub Actions serait lourd et lent pour ce besoin.

A la place, ce script REPRODUIT FIDELEMENT en Python la logique de
decision de demarrer() (meme algorithme, mots-outils/constantes copies
a l'identique de cme-cta-progressifs.php) directement sur le contenu
stocke (content.raw, via l'API REST WordPress) :
  1. Prefixe d'URL connu de PAR_PREFIXE (gaz/electricite/aide-energetique/
     renovation-energetique/solaire) -- sinon AUCUN formulaire (le JS
     s'arrete explicitement, voir ligne ~248 du mu-plugin).
  2. Parcours des enfants directs du contenu, cumul de mots par bloc
     P/UL/OL/TABLE/FIGURE/BLOCKQUOTE jusqu'a MOTS_PAR_BOUTON (230) mots,
     en respectant MOTS_FIN_MIN (120 mots restants minimum) -- replique
     exactement la double boucle avant/arriere du JS.

Un article est signale "sans formulaire" si cette simulation calcule 0
position possible. Lecture seule -- ne modifie rien, ne verifie pas le
rendu reel (qui necessiterait un navigateur), mais la logique est
deterministe et identique a celle executee par le navigateur du visiteur.

USAGE :
  python3 identifier_articles_sans_formulaire.py
  python3 identifier_articles_sans_formulaire.py --limite=50

Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.
"""
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)

# Constantes copiees A L'IDENTIQUE de wordpress-mu-plugins/cme-cta-progressifs.php
PREFIXES_CONNUS = {"gaz", "electricite", "aide-energetique", "renovation-energetique", "solaire"}
MOTS_PAR_BOUTON = 230
MOTS_FIN_MIN = 120
MAX_BOUTONS = 30
TAGS_AUTORISES = {"P", "UL", "OL", "TABLE", "FIGURE", "BLOCKQUOTE"}


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


def mots(el):
    t = el.get_text().strip()
    return len(t.split()) if t else 0


def est_cta(el):
    return el.name == "div" and "linear-gradient" in (el.get("style") or "")


def est_vide(el):
    return el.name == "div" and len(list(el.children)) == 0 and not el.get_text().strip()


def simuler_poses(contenu_html):
    """Reproduit fidelement demarrer()/la double boucle avant-arriere du JS."""
    soup = BeautifulSoup(contenu_html, "html.parser")
    enfants = [c for c in soup.contents if getattr(c, "name", None)]
    n = len(enfants)
    if n == 0:
        return 0

    apres = [0] * n
    acc = 0
    for i in range(n - 1, -1, -1):
        apres[i] = acc
        if est_cta(enfants[i]):
            acc = 0
        else:
            acc += mots(enfants[i])

    cumul = 0
    poses = 0
    for i in range(n):
        el = enfants[i]
        if est_cta(el):
            cumul = 0
            continue
        cumul += mots(el)
        if cumul < MOTS_PAR_BOUTON:
            continue
        if poses >= MAX_BOUTONS:
            break
        if el.name.upper() not in TAGS_AUTORISES:
            continue
        suivant_el = enfants[i + 1] if i + 1 < n else None
        if suivant_el is None or est_cta(suivant_el) or est_vide(suivant_el):
            continue
        if apres[i] < MOTS_FIN_MIN:
            continue
        poses += 1
        cumul = 0
    return poses


def main():
    limite = parse_args()
    print("📥 Recuperation des articles publies (API REST WordPress)...")
    posts = lister_tous_les_posts(limite)
    print(f"  ✅ {len(posts)} articles\n")

    sans_prefixe = []
    sans_formulaire = []

    for i, post in enumerate(posts):
        url = post["link"]
        prefixe = url.replace(WP_URL, "").strip("/").split("/")[0] if url.startswith(WP_URL) else ""
        if prefixe not in PREFIXES_CONNUS:
            sans_prefixe.append((post["id"], url, prefixe))
            continue
        contenu = post["content"]["raw"] if "raw" in post.get("content", {}) else post["content"]["rendered"]
        poses = simuler_poses(contenu)
        nb_mots = len(BeautifulSoup(contenu, "html.parser").get_text().split())
        if poses == 0:
            sans_formulaire.append((post["id"], url, nb_mots))
        if (i + 1) % 100 == 0:
            print(f"  ... {i+1}/{len(posts)} analyses")
        time.sleep(0.05)

    print(f"\n{'='*70}")
    print(f"RAPPORT — COUVERTURE DU MINI-FORMULAIRE ({len(posts)} articles)")
    print(f"{'='*70}")

    print(f"\n⚠️ Prefixe d'URL non reconnu par PAR_PREFIXE ({len(sans_prefixe)}) "
          f"-- PAR_PREFIXE ne couvre que gaz/electricite/aide-energetique/"
          f"renovation-energetique/solaire :")
    for pid, url, prefixe in sans_prefixe[:30]:
        print(f"  post_id={pid} | prefixe='{prefixe}' | {url}")

    print(f"\n⚠️ Formulaire non insere -- contenu trop court ou mal structure "
          f"pour atteindre {MOTS_PAR_BOUTON} mots cumules + {MOTS_FIN_MIN} mots "
          f"restants ({len(sans_formulaire)}) :")
    for pid, url, nb_mots in sorted(sans_formulaire, key=lambda x: x[2]):
        print(f"  post_id={pid} | ~{nb_mots} mots au total | {url}")

    total_sans = len(sans_prefixe) + len(sans_formulaire)
    print(f"\n📊 TOTAL sans formulaire : {total_sans}/{len(posts)} "
          f"({100*total_sans/len(posts):.1f}%)")


if __name__ == "__main__":
    main()
