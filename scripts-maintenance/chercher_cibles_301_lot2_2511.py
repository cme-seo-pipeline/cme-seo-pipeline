"""
CME — Recherche de cibles de redirection 301 candidates pour le 2e lot de
12 URLs 404 signalees le 25/11/2026 (voir diagnostiquer_12_urls_404_2511_v2.py,
qui a confirme zero trace nulle part pour les 12 -- aucun post/page WP,
aucune ligne historique_publications/GSC/wp_url_mapping/sitemap, aucun lien
interne dans les 1154 posts + 13 pages publies).

Ce script :
  1. Liste les 13 pages statiques du site (pour confirmer l'URL reelle de
     la page mentions legales/confidentialite -- deja documentee ailleurs
     dans CLAUDE.md comme etant /cadre-legal-et-confidentialite/).
  2. Recherche par mot-cle (API publique WP, /wp/v2/posts?search=) les
     meilleurs articles DEJA PUBLIES et VIVANTS pour chacun des sujets
     evoques par les slugs des 10 autres URLs 404 (hors mentions-legales
     deja couverte par (1), et hors compteur-gaz-intelligent-linky deja
     resolue par le lot 1 -> compteur-gaz-communicant-linky).

LECTURE SEULE -- API publique WordPress, pas d'authentification necessaire.
"""
import time

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
TIMEOUT = 20

RECHERCHES = [
    ("tarif-bleu-edf-vs-autres-fournisseurs", "tarif bleu EDF"),
    ("tarif-bleu-edf-vs-autres-fournisseurs (bis)", "tarif reglemente electricite"),
    ("prime-energie-cee-comment-ca-marche", "CEE certificat economie energie"),
    ("prime-energie-cee-comment-ca-marche (bis)", "prime energie"),
    ("pourquoi-la-pompe-a-chaleur...", "pompe a chaleur solution chauffage"),
    ("comprendre-ma-facture-delectricite", "comprendre facture electricite"),
    ("comprendre-tarif-de-base-electricite", "tarif de base electricite"),
    ("ohm-energie", "Ohm Energie"),
    ("les-prix-de-kwh", "prix du kwh electricite"),
    ("economies-denergie-le-guide-pratique...", "guide economies energie reduire facture"),
    ("reduire-vos-factures-delectricte", "reduire facture electricite"),
]


def rechercher(terme, par_page=5):
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={"search": terme, "per_page": par_page, "_fields": "id,link,title,date"},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()
        print(f"    ⚠️ HTTP {r.status_code} pour la recherche {terme!r}")
    except Exception as e:
        print(f"    ⚠️ erreur recherche {terme!r} : {e}")
    return []


def lister_pages():
    pages = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/pages",
                params={"per_page": 50, "page": page, "_fields": "id,link,title,slug,status"},
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
        pages.extend(data)
        page += 1
        time.sleep(0.15)
    return pages


def main():
    print("=" * 100)
    print("1. LISTE DES PAGES STATIQUES DU SITE (pour confirmer l'URL mentions legales)")
    print("=" * 100)
    pages = lister_pages()
    print(f"{len(pages)} page(s) publiee(s) :")
    for p in pages:
        titre = p.get("title", {}).get("rendered", "")
        print(f"  - slug={p.get('slug')!r} | {titre} | {p.get('link')}")

    print("\n" + "=" * 100)
    print("2. RECHERCHE DE CANDIDATS DE REDIRECTION PAR MOT-CLE (articles vivants)")
    print("=" * 100)
    for label, terme in RECHERCHES:
        print(f"\n### Pour : {label}  (recherche : {terme!r})")
        resultats = rechercher(terme)
        if not resultats:
            print("    Aucun resultat.")
            continue
        for r in resultats:
            titre = r.get("title", {}).get("rendered", "")
            print(f"    - {r.get('date', '')[:10]} | {titre} | {r.get('link')}")
        time.sleep(0.2)


if __name__ == "__main__":
    main()
