"""
CME — Verification RIGOUREUSE (demande operateur explicite, 02/11/2026) de
l'hypothese "le pipeline lui-meme a pu generer un lien de maillage interne
vers une des 7 URLs 404 de l'audit externe du jour". Le diagnostic precedent
(diagnostiquer_404_audit_0211_liens.py) n'avait verifie que 7 pages
d'archive silo/sous-silo + 13 articles candidats choisis a la main -- pas
l'integralite du corpus. Ce script corrige ca : parcourt TOUT le contenu
publie (tous les articles, paginated) et cherche une occurrence litterale
de chacune des 7 URLs (forme absolue ET relative, au cas ou un lien aurait
ete insere en chemin relatif).

LECTURE SEULE.
"""
import sys
import time

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
TIMEOUT = 20
PER_PAGE = 100

URLS_404 = [
    "https://www.comprendre-mon-energie.fr/solaire/systeme-solaire-combine/aides-systeme-solaire-combine-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/batterie-panneaux-solaires/aides-batterie-solaire-2026/",
    "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/augmentation-electricite-causes/",
    "https://www.comprendre-mon-energie.fr/solaire/panneaux-solaires/maprimerenov-panneaux-solaires-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/aides-chauffe-eau-solaire-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/prix-chauffe-eau-solaire-2026-cout-installation/",
    "https://www.comprendre-mon-energie.fr/solaire/panneaux-solaires/prix-panneaux-solaires-2026-tarifs/",
]
# Formes relatives possibles (chemin sans domaine) pour chaque URL.
CHEMINS_RELATIFS = [u.replace("https://www.comprendre-mon-energie.fr", "") for u in URLS_404]
SLUGS = [u.rstrip("/").rsplit("/", 1)[-1] for u in URLS_404]


def lister_tous_les_posts():
    posts = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                params={"per_page": PER_PAGE, "page": page, "status": "publish",
                        "_fields": "id,link,content"},
                timeout=TIMEOUT,
            )
        except Exception as e:
            print(f"  ⚠️ erreur page {page} : {e}")
            break
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        posts.extend(data)
        page += 1
        time.sleep(0.2)
    return posts


def main():
    print("Recuperation de tous les articles publies (contenu complet)...")
    posts = lister_tous_les_posts()
    print(f"{len(posts)} article(s) recupere(s).\n")

    trouvailles = {url: [] for url in URLS_404}

    for post in posts:
        contenu = post.get("content", {}).get("rendered", "") or ""
        for url, chemin_rel, slug in zip(URLS_404, CHEMINS_RELATIFS, SLUGS):
            if url in contenu or url.rstrip("/") in contenu or chemin_rel in contenu or chemin_rel.rstrip("/") in contenu:
                trouvailles[url].append(post.get("link"))

    print("=" * 100)
    print("RESULTAT -- liens internes trouves DANS LE CONTENU PUBLIE (tous articles, pas un echantillon)")
    print("=" * 100)
    total = 0
    for url, sources in trouvailles.items():
        if sources:
            total += len(sources)
            print(f"\n*** {url} ***")
            print(f"    LIE DEPUIS {len(sources)} article(s) :")
            for s in sources:
                print(f"        - {s}")
        else:
            print(f"\n{url} : aucun lien trouve dans les {len(posts)} articles publies")

    print(f"\n{'=' * 100}")
    print(f"TOTAL : {total} lien(s) interne(s) trouve(s) vers les 7 URLs 404, sur {len(posts)} articles scannes.")
    print("=" * 100)


if __name__ == "__main__":
    main()
