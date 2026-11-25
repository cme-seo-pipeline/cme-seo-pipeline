"""
CME — Complement au diagnostic diagnostiquer_5_urls_404_2511.py (25/11/2026).

Les 5 URLs signalees par l'operateur se sont revelees INTROUVABLES partout
(aucun post WP meme en corbeille, aucune ligne historique_publications,
aucune trace GSC, absentes du sitemap, et surtout : ZERO lien interne dans
l'integralite des 1154 articles publies, contrairement au precedent du
02/11/2026 ou un scan exhaustif avait justement REVELE des liens internes
caches). Egalement absentes de la totalite de l'historique Git du repo
(recherche "pickaxe" sur chaque slug) -- ces URLs n'ont jamais ete produites
par ce pipeline, ni par aucun script de maintenance, ni par aucune table de
maillage pilier/CTA.

Ce script liste les articles REELLEMENT publies dans les 4 categories
concernees (chauffage-gaz, demenagement-gaz, heures-pleines-creuses,
aides-renovation-toiture), pour identifier le meilleur candidat de
redirection 301 par proximite thematique reelle -- meme methode que
l'audit 404 externe du 02/11/2026 (tableau de propositions de cibles).

LECTURE SEULE -- API publique WordPress, pas d'authentification necessaire.
"""
import sys
import time

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
TIMEOUT = 20

# (nom affiche, slug de categorie WP) -- slugs confirmes par les sections
# CLAUDE.md du 12-13/11/2026 (quotas / lister_categories_wp.py)
CATEGORIES = [
    ("Chauffage Gaz", "chauffage-gaz"),
    ("Déménagement gaz", "demenagement-gaz"),
    ("Heures pleines/creuses (Électricité)", "heures-pleines-creuses"),
    ("Aides rénovation toiture", "aides-renovation-toiture"),
]


def trouver_categorie_id(slug):
    try:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories",
                          params={"slug": slug, "_fields": "id,name,slug,count"},
                          timeout=TIMEOUT)
        if r.status_code == 200 and r.json():
            return r.json()[0]
    except Exception as e:
        print(f"    ⚠️ erreur categorie {slug} : {e}")
    return None


def lister_articles(cat_id, per_page=50):
    articles = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                params={"categories": cat_id, "per_page": per_page, "page": page,
                        "orderby": "date", "order": "desc",
                        "_fields": "id,link,title,date"},
                timeout=TIMEOUT,
            )
        except Exception as e:
            print(f"    ⚠️ erreur page {page} : {e}")
            break
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        articles.extend(data)
        page += 1
        time.sleep(0.15)
    return articles


def main():
    for nom, slug in CATEGORIES:
        print("=" * 100)
        print(f"CATEGORIE : {nom}  (slug={slug!r})")
        print("=" * 100)
        cat = trouver_categorie_id(slug)
        if not cat:
            print("  ⚠️ Categorie introuvable via l'API publique -- verifier le slug.")
            continue
        print(f"  id={cat['id']} | name WP={cat['name']!r} | count={cat.get('count')}")
        articles = lister_articles(cat["id"])
        print(f"  {len(articles)} article(s) recupere(s) via l'API (categorie principale ou secondaire) :")
        for a in articles:
            titre = a.get("title", {}).get("rendered", "")
            print(f"    - {a.get('date', '')[:10]} | {titre} | {a.get('link')}")
        print()


if __name__ == "__main__":
    main()
