"""
CME — Verification en lecture seule des 2 nouvelles categories WordPress
"compteur" (silo Electricite) et "compteur-gaz" (silo Gaz), creees par
l'operateur le 13/11/2026, avant de les ajouter a QUOTAS_SOUS_SILO
(pipeline/pipeline.py).

URLs donnees par l'operateur :
  https://www.comprendre-mon-energie.fr/electricite/compteur/
  https://www.comprendre-mon-energie.fr/gaz/compteur-gaz/

Verifie : la categorie existe bien, son parent est le bon silo racine,
et recupere son "name" WordPress exact -- c'est ce libelle qui doit
etre utilise comme Sous-Silo dans QUOTAS_SOUS_SILO (meme convention que
les autres entrees, ex. "Aide isolation", pas une reconstruction a la
main depuis le slug).

LECTURE SEULE -- aucune ecriture.
Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.

USAGE :
  python3 verifier_nouveaux_sous_silos_compteur.py
"""
import os
import sys

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")

AUTH = (WP_USERNAME, WP_APP_PASSWORD)

CIBLES = [
    ("compteur", "electricite"),
    ("compteur-gaz", "gaz"),
]


def main():
    categories = []
    page = 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/categories",
            params={"per_page": 100, "page": page, "context": "edit"},
            auth=AUTH,
            timeout=15,
        )
        if r.status_code == 400:
            break
        if r.status_code != 200:
            sys.exit(f"❌ HTTP {r.status_code} page {page} : {r.text[:300]}")
        lot = r.json()
        if not lot:
            break
        categories.extend(lot)
        if len(lot) < 100:
            break
        page += 1

    by_id = {c["id"]: c for c in categories}
    by_slug = {c["slug"]: c for c in categories}

    print(f"✅ {len(categories)} categories recuperees\n")

    for slug_cible, slug_parent_attendu in CIBLES:
        c = by_slug.get(slug_cible)
        if not c:
            print(f"❌ Slug '{slug_cible}' INTROUVABLE parmi les categories WordPress")
            continue
        parent = by_id.get(c["parent"]) if c["parent"] else None
        parent_slug = parent["slug"] if parent else None
        ok_parent = (parent_slug == slug_parent_attendu)
        print(f"--- /{parent_slug}/{c['slug']}/ (id={c['id']}, count={c['count']}) ---")
        print(f"Name WordPress (a utiliser comme Sous-Silo) : {c['name']!r}")
        print(f"Parent attendu '{slug_parent_attendu}' : {'OK' if ok_parent else f'⚠️ MISMATCH (parent reel = {parent_slug!r})'}")
        desc = (c.get("description") or "").strip()
        print(f"Description actuelle ({len(desc)} car.) : {desc!r}")
        print()


if __name__ == "__main__":
    main()
