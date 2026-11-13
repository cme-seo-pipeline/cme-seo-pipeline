"""
CME — Verification en lecture seule de la categorie WordPress
"demenagement-gaz" (silo Gaz), avant de l'echanger contre "Aides
chauffe-eau thermodynamique" (silo Aide Energetique) dans
QUOTAS_SOUS_SILO (demande operateur du 13/11/2026, meme volume total,
juste un changement de repartition).

URL donnee par l'operateur :
  https://www.comprendre-mon-energie.fr/gaz/demenagement-gaz/

A ne pas confondre avec "Déménagement" (silo Electricite, slug
"demenagement", deja au quota depuis ce soir meme -- voir CLAUDE.md,
section "Quota — elargissement a 20/jour") : categorie DIFFERENTE, slug
different, silo different.

LECTURE SEULE -- aucune ecriture.
Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.

USAGE :
  python3 verifier_demenagement_gaz.py
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
    by_slug = {c["slug"]: c for c in categories}

    print(f"✅ {len(categories)} categories recuperees\n")

    c = by_slug.get("demenagement-gaz")
    if not c:
        print("❌ Slug 'demenagement-gaz' INTROUVABLE parmi les categories WordPress")
        return
    parent = by_id.get(c["parent"]) if c["parent"] else None
    parent_slug = parent["slug"] if parent else None
    ok_parent = (parent_slug == "gaz")
    print(f"--- /{parent_slug}/{c['slug']}/ (id={c['id']}, count={c['count']}) ---")
    print(f"Name WordPress (a utiliser comme Sous-Silo) : {c['name']!r}")
    print(f"Parent attendu 'gaz' : {'OK' if ok_parent else f'⚠️ MISMATCH (parent reel = {parent_slug!r})'}")
    desc = (c.get("description") or "").strip()
    print(f"Description actuelle ({len(desc)} car.) : {desc!r}")


if __name__ == "__main__":
    main()
