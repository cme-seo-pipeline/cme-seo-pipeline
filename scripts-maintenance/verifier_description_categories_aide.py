"""
CME — Verification en lecture seule des descriptions de categories WordPress
pour le sous-silo "Aide isolation" et ses voisins (silo Aide Energetique).

Demande operateur du 13/11/2026 : "je veux une description pour le sous
silo aide-isolation". Avant de rediger quoi que ce soit, verifie l'etat
actuel (la categorie a-t-elle deja une description ? vide ?) et releve
les descriptions deja en place sur des categories comparables (meme
silo, notamment "Aide pompe a chaleur" qui partage le meme angle
editorial transactionnel, cf. CLAUDE.md 12/11/2026) pour caler longueur
et ton si une convention existe deja.

LECTURE SEULE -- aucune ecriture.
Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.

USAGE :
  python3 verifier_description_categories_aide.py
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

SLUGS_A_VERIFIER = [
    "aide-isolation",
    "aide-pompe-a-chaleur",
    "maprimerenov",
    "cheque-energie",
    "aides-chauffe-eau-thermodynamique",
]


def main():
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories",
        params={"per_page": 100, "context": "edit"},
        auth=AUTH,
        timeout=15,
    )
    if r.status_code != 200:
        sys.exit(f"❌ HTTP {r.status_code} : {r.text[:300]}")
    categories = r.json()
    by_slug = {c["slug"]: c for c in categories}

    print(f"✅ {len(categories)} categories recuperees\n")
    for slug in SLUGS_A_VERIFIER:
        c = by_slug.get(slug)
        if not c:
            print(f"⚠️  Slug '{slug}' introuvable")
            continue
        desc = (c.get("description") or "").strip()
        print(f"--- {slug} (id={c['id']}, parent={c['parent']}, count={c['count']}) ---")
        print(f"Description actuelle ({len(desc)} car.) : {desc!r}")
        print()


if __name__ == "__main__":
    main()
