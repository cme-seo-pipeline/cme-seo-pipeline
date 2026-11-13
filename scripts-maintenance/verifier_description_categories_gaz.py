"""
CME — Verification en lecture seule des descriptions de categories
WordPress du silo Gaz, avant redaction d'une description pour le
nouveau sous-silo "compteur" (gaz/compteur/..., cree par l'operateur le
13/11/2026).

Meme logique que verifier_description_categories_aide.py (13/11/2026) :
relever les descriptions deja en place sur les sous-silos voisins du
meme silo pour caler longueur/ton avant de rediger, plutot que deviner.

LECTURE SEULE -- aucune ecriture.
Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.

USAGE :
  python3 verifier_description_categories_gaz.py
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

    def chemin(cat):
        segments = [cat["slug"]]
        courant = cat
        while courant.get("parent"):
            courant = by_id.get(courant["parent"])
            if not courant:
                break
            segments.insert(0, courant["slug"])
        return "/" + "/".join(segments) + "/"

    print(f"✅ {len(categories)} categories recuperees\n")

    # Repere le silo "Gaz" (categorie racine) et tous ses enfants directs
    racine_gaz = next((c for c in categories if c["parent"] == 0 and "gaz" in c["slug"].lower()), None)
    if not racine_gaz:
        print("⚠️  Categorie racine 'gaz' introuvable, affichage de toutes les categories contenant 'gaz'/'compteur' :")
        cibles = [c for c in categories if "gaz" in c["slug"].lower() or "compteur" in c["slug"].lower()]
    else:
        print(f"Racine Gaz : {racine_gaz['slug']} (id={racine_gaz['id']})\n")
        cibles = [c for c in categories if c["parent"] == racine_gaz["id"]] + [racine_gaz]

    for c in sorted(cibles, key=lambda c: chemin(c)):
        desc = (c.get("description") or "").strip()
        print(f"--- {chemin(c)} (slug={c['slug']}, id={c['id']}, count={c['count']}) ---")
        print(f"Description actuelle ({len(desc)} car.) : {desc!r}")
        print()


if __name__ == "__main__":
    main()
