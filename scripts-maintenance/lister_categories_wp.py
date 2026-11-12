"""
CME — Liste exhaustive des categories WordPress (id, slug, nom, parent).

Lecture seule. Ecrit pour verifier les VRAIS slugs de sous-silo avant
d'etendre `cme-cta-progressifs.php` (mapping message CTA) du niveau
silo (5 prefixes) au niveau sous-silo (14 cibles), demande operateur du
12/11/2026 ("cartographier des messages CTA plus personnalises").

Pourquoi ce script plutot que de deviner les slugs via to_slug() (meme
fonction que pipeline.py) : plusieurs categories "Aide Énergétique" ont
ete creees MANUELLEMENT par l'operateur en wp-admin (Aide pompe à
chaleur, Aide isolation) -- rien ne garantit que WordPress sanitize_title()
produit exactement le meme slug que to_slug() sur un nom avec apostrophe
ou accent (ex. "MaPrimeRénov'"). Le mapping cote JS (pathname.split('/'))
doit matcher le slug REEL tel que WordPress le genere, pas une
approximation -- sinon le message sous-silo ne s'affiche jamais pour ce
cas precis (fallback silencieux sur le message de silo, pas un crash,
mais ca rate l'objectif de personnalisation).

USAGE :
  python3 lister_categories_wp.py

Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.
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
        try:
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/categories",
                params={"per_page": 100, "page": page, "orderby": "id"},
                auth=AUTH,
                timeout=15,
            )
        except Exception as e:
            sys.exit(f"❌ Erreur réseau page {page} : {e}")
        if r.status_code == 400:
            break  # page au-dela du total -- fin de pagination WP standard
        if r.status_code != 200:
            sys.exit(f"❌ HTTP {r.status_code} page {page} : {r.text[:300]}")
        lot = r.json()
        if not lot:
            break
        categories.extend(lot)
        if len(lot) < 100:
            break
        page += 1

    print(f"✅ {len(categories)} categories recuperees\n")

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

    print(f"{'ID':>6} | {'parent':>6} | {'count':>5} | {'slug':40s} | {'nom':40s} | chemin")
    print("-" * 160)
    for c in sorted(categories, key=lambda c: chemin(c)):
        print(f"{c['id']:>6} | {c.get('parent', 0):>6} | {c.get('count', 0):>5} | "
              f"{c['slug']:40s} | {c['name']:40s} | {chemin(c)}")


if __name__ == "__main__":
    main()
