"""
CME — Dernier volet du diagnostic des 7 URLs 404 : cherche qui, sur le site
EN LIVE, contient encore un lien vers ces URLs (source probable du 404 pour
un vrai visiteur / crawler qui suit les liens plutot que le sitemap), et
verifie une correspondance partielle (LIKE, pas egalite stricte) dans GSC
au cas ou l'URL stockee differe legerement (slash final, etc.).

Verifie aussi 02_cleaned.wp_url_mapping (snapshot WRITE_TRUNCATE du dernier
rafraichissement -- si ces URLs y figurent encore, c'est qu'elles etaient
publiees lors du dernier rafraichissement de cette table).

LECTURE SEULE.
"""
import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

import requests

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

WP_URL = "https://www.comprendre-mon-energie.fr"
TIMEOUT = 15

URLS_404 = [
    "https://www.comprendre-mon-energie.fr/solaire/systeme-solaire-combine/aides-systeme-solaire-combine-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/batterie-panneaux-solaires/aides-batterie-solaire-2026/",
    "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/augmentation-electricite-causes/",
    "https://www.comprendre-mon-energie.fr/solaire/panneaux-solaires/maprimerenov-panneaux-solaires-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/aides-chauffe-eau-solaire-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/prix-chauffe-eau-solaire-2026-cout-installation/",
    "https://www.comprendre-mon-energie.fr/solaire/panneaux-solaires/prix-panneaux-solaires-2026-tarifs/",
]
SLUGS = [u.rstrip("/").rsplit("/", 1)[-1] for u in URLS_404]

# Pages d'archive de silo/sous-silo a inspecter directement (racines de
# chaque URL 404, + la racine /solaire/ elle-meme).
PAGES_A_INSPECTER = sorted(set(
    [u.rsplit("/", 2)[0] + "/" for u in URLS_404] + [f"{WP_URL}/solaire/", f"{WP_URL}/electricite/"]
))


def main():
    client_bq = init_bigquery()

    print("=" * 100)
    print("1) wp_url_mapping (dernier snapshot WRITE_TRUNCATE)")
    print("=" * 100)
    for url, slug in zip(URLS_404, SLUGS):
        df = client_bq.query(f"""
            SELECT post_id, url, date_maj FROM `{PROJECT_ID}.02_cleaned.wp_url_mapping`
            WHERE url LIKE '%{slug}%'
        """).to_dataframe()
        if len(df):
            for _, r in df.iterrows():
                print(f"    TROUVE : {slug} -> post_id={r['post_id']}, url={r['url']}, date_maj={r['date_maj']}")
        else:
            print(f"    absent : {slug}")

    print("\n" + "=" * 100)
    print("2) Correspondance PARTIELLE dans gsc_queries (LIKE, pas egalite stricte)")
    print("=" * 100)
    for url, slug in zip(URLS_404, SLUGS):
        df = client_bq.query(f"""
            SELECT DISTINCT page FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE page LIKE '%{slug}%'
            LIMIT 5
        """).to_dataframe()
        if len(df):
            for _, r in df.iterrows():
                print(f"    TROUVE (variante) pour {slug} : {r['page']}")
        else:
            print(f"    aucune variante trouvee pour : {slug}")

    print("\n" + "=" * 100)
    print("3) Liens EN LIVE sur les pages d'archive silo/sous-silo")
    print("=" * 100)
    for page in PAGES_A_INSPECTER:
        try:
            r = requests.get(page, timeout=TIMEOUT)
            print(f"\n{page} -> HTTP {r.status_code}")
            if r.status_code == 200:
                for url in URLS_404:
                    if url.rstrip("/") in r.text or url.rstrip("/").split("comprendre-mon-energie.fr")[-1] in r.text:
                        print(f"    *** LIEN TROUVE vers {url} ***")
        except Exception as e:
            print(f"{page} -> erreur {e}")

    print("\n" + "=" * 100)
    print("4) Liens EN LIVE sur les articles candidats de remplacement deja identifies")
    print("=" * 100)
    # Articles trouves par la recherche par mot-cle du script precedent --
    # susceptibles de pointer eux-memes vers un sujet voisin disparu.
    candidats = [
        f"{WP_URL}/solaire/systeme-solaire-combine/systeme-solaire-combine-vs-chaudiere-gaz-economies/",
        f"{WP_URL}/solaire/systeme-solaire-combine/cout-economies-systeme-solaire-combine/",
        f"{WP_URL}/solaire/systeme-solaire-combine/prix-installation-systeme-solaire-combine-2026/",
        f"{WP_URL}/solaire/batterie-panneaux-solaires/batterie-solaire-vs-panneau-seul-roi-2026/",
        f"{WP_URL}/solaire/batterie-panneaux-solaires/batterie-solaire-5-kwh-prix-devis-rentabilite/",
        f"{WP_URL}/solaire/panneaux-solaires/panneaux-solaires-400w-prix-rendement-roi-1031/",
        f"{WP_URL}/solaire/panneaux-solaires/panneaux-solaires-400w-prix-rendement-roi-1031-2/",
        f"{WP_URL}/solaire/kit-solaire/kit-solaire-9kw-dimensionnement-prix-roi/",
        f"{WP_URL}/solaire/kit-solaire/kit-solaire-9kw-prix-installation/",
        f"{WP_URL}/solaire/chauffe-eau-solaire/chauffe-eau-solaire-vs-gaz-roi/",
        f"{WP_URL}/solaire/chauffe-eau-solaire/chauffe-eau-solaire-vs-electrique-cout-reel/",
        f"{WP_URL}/electricite/facture-electricite/aides-reductions-facture-electricite/",
        f"{WP_URL}/electricite/facture-electricite/pic-consommation-electrique-facture-explose/",
    ]
    for page in candidats:
        try:
            r = requests.get(page, timeout=TIMEOUT)
            trouve = []
            if r.status_code == 200:
                for url, slug in zip(URLS_404, SLUGS):
                    if slug in r.text:
                        trouve.append(slug)
            print(f"{page} -> HTTP {r.status_code}" + (f" | LIENS MORTS TROUVES : {trouve}" if trouve else ""))
        except Exception as e:
            print(f"{page} -> erreur {e}")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
