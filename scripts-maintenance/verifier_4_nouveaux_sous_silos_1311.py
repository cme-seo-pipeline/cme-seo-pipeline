"""
CME — Verification en lecture seule de 4 categories WordPress que
l'operateur veut ajouter au quota quotidien (demande du 13/11/2026,
meme soir que l'ajout des 2 sous-silos "Compteur") :
  https://www.comprendre-mon-energie.fr/gaz/contrat-gaz/
  https://www.comprendre-mon-energie.fr/gaz/chauffage-gaz/
  https://www.comprendre-mon-energie.fr/electricite/chauffage-electricite/
  https://www.comprendre-mon-energie.fr/electricite/demenagement/

Meme logique que verifier_nouveaux_sous_silos_compteur.py : confirmer
slug/parent/name WordPress exact (libelle Sous-Silo a utiliser dans
QUOTAS_SOUS_SILO) et l'etat actuel (nb articles deja publies,
description de categorie) avant toute modification de pipeline.py.

LECTURE SEULE -- aucune ecriture.
Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.

USAGE :
  python3 verifier_4_nouveaux_sous_silos_1311.py
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
    ("contrat-gaz", "gaz"),
    ("chauffage-gaz", "gaz"),
    ("chauffage-electricite", "electricite"),
    ("demenagement", "electricite"),
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
