"""
CME — Etat des lieux en lecture seule des descriptions de categories
WordPress pour le silo Solaire (5 sous-silos) + re-confirmation de
"Aide isolation" et "Aide pompe a chaleur" (silo Aide Energetique).

Demande operateur du 13/11/2026, 22h31 : etendre la strategie de
description de categorie (deja en place sur Gaz/bouteilles,
Gaz/facture-gaz, Gaz/contrat-gaz, et les equivalents Electricite) a
l'ensemble du silo Solaire, et verifier Aide isolation/Aide pompe a
chaleur -- objectif explicite : "gagner de l'autorite" en unifiant ce
traitement sur tous les sous-silos qui rapportent du trafic.

LECTURE SEULE -- aucune ecriture.
Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.

USAGE :
  python3 verifier_descriptions_solaire_et_aide.py
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

    racine_solaire = next((c for c in categories if c["parent"] == 0 and "solaire" in c["slug"].lower()), None)

    print("=" * 90)
    print("SILO SOLAIRE")
    print("=" * 90)
    if racine_solaire:
        cibles = [racine_solaire] + [c for c in categories if c["parent"] == racine_solaire["id"]]
    else:
        cibles = [c for c in categories if "solaire" in c["slug"].lower()]
    for c in sorted(cibles, key=lambda c: chemin(c)):
        desc = (c.get("description") or "").strip()
        print(f"--- {chemin(c)} (slug={c['slug']}, id={c['id']}, count={c['count']}) ---")
        print(f"Description actuelle ({len(desc)} car.) : {desc!r}")
        print()

    print("=" * 90)
    print("RE-CONFIRMATION — Aide isolation / Aide pompe a chaleur")
    print("=" * 90)
    for slug in ("aide-isolation", "aide-pompe-a-chaleur"):
        c = next((c for c in categories if c["slug"] == slug), None)
        if not c:
            print(f"⚠️  Slug '{slug}' introuvable")
            continue
        desc = (c.get("description") or "").strip()
        print(f"--- {chemin(c)} (slug={c['slug']}, id={c['id']}, count={c['count']}) ---")
        print(f"Description actuelle ({len(desc)} car.) : {desc!r}")
        print()


if __name__ == "__main__":
    main()
