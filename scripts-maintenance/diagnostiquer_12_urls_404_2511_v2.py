"""
CME — Diagnostic d'un DEUXIEME lot de 12 URLs signalees introuvables par
l'operateur le 25/11/2026 (apres le premier lot de 5 URLs, voir
diagnostiquer_5_urls_404_2511.py et la section CLAUDE.md correspondante) :

  1.  /electricite/facture-electricite/tarif-bleu-edf-vs-autres-fournisseurs/
  2.  /uncategorized/compteur-gaz-intelligent-linky-fonctionnement/
  3.  /uncategorized/prime-energie-cee-comment-ca-marche/
  4.  /comprendre-mon-energie-mentions-legales/
  5.  /pourquoi-la-pompe-a-chaleur-est-elle-la-solution-de-chauffage-preferee-des-francais-en-2026/
  6.  /comprendre-ma-facture-delectricite/
  7.  /comprendre-tarif-de-base-electricite/
  8.  /ohm-energie/
  9.  /les-prix-de-kwh/
  10. /economies-denergie-le-guide-pratique-pour-reduire-vos-facture-en-2026/
  11. /choisir-votre-accompagnement/
  12. /reduire-vos-factures-delectricte/

Difference notable avec le 1er lot (slugs en {silo}/{sous-silo}/slug/, zero
trace nulle part) : ce 2e lot melange des URLs a permalien court (sans
prefixe silo/sous-silo), dont 2 explicitement sous /uncategorized/ (la
categorie WordPress par defaut quand aucune categorie n'est assignee) et
plusieurs URLs RACINE (ni silo ni categorie du tout) qui ressemblent a
d'anciens titres d'articles generiques/legacy (pas le gabarit de titre SEO
du pipeline actuel) -- hypothese a verifier : ancien permalien du site
(avant adoption de la structure /{silo}/{sous-silo}/{slug}/), pages
statiques legacy, ou anciennes pages de simulateurs/CTA deja documentees
comme retirees en octobre 2026.

Important : URL #2 (compteur-gaz-intelligent-linky-fonctionnement) est le
MEME SLUG que l'URL #3 du 1er lot (qui avait un prefixe /gaz/demenagement-gaz/
different et zero trace nulle part, y compris en tous statuts WP). Ici
elle apparait sous /uncategorized/ -- a verifier si c'est un VRAI post WP
sans categorie (donc une histoire differente du 1er lot), ou si elle est
tout aussi fantome.

Etendu par rapport au script du 1er lot :
  - verifie aussi /wp/v2/pages (pas seulement /wp/v2/posts) -- plusieurs
    de ces URLs ressemblent a des PAGES statiques (mentions legales,
    "choisir-votre-accompagnement") plutot qu'a des articles de blog.
  - verifie le sitemap des PAGES en plus de celui des articles.
  - scan exhaustif du contenu de TOUS les posts ET TOUTES les pages
    publies pour un lien interne vers chacune des 12 URLs.

LECTURE SEULE. Necessite WP_APP_PASSWORD (+ WP_USERNAME optionnel).
"""
import os
import sys
import re
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

import requests

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)
TIMEOUT = 20
PER_PAGE = 100
TOUS_STATUTS = "publish,draft,trash,pending,future,private"

URLS_404 = [
    "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/tarif-bleu-edf-vs-autres-fournisseurs/",
    "https://www.comprendre-mon-energie.fr/uncategorized/compteur-gaz-intelligent-linky-fonctionnement/",
    "https://www.comprendre-mon-energie.fr/uncategorized/prime-energie-cee-comment-ca-marche/",
    "https://www.comprendre-mon-energie.fr/comprendre-mon-energie-mentions-legales/",
    "https://www.comprendre-mon-energie.fr/pourquoi-la-pompe-a-chaleur-est-elle-la-solution-de-chauffage-preferee-des-francais-en-2026/",
    "https://www.comprendre-mon-energie.fr/comprendre-ma-facture-delectricite/",
    "https://www.comprendre-mon-energie.fr/comprendre-tarif-de-base-electricite/",
    "https://www.comprendre-mon-energie.fr/ohm-energie/",
    "https://www.comprendre-mon-energie.fr/les-prix-de-kwh/",
    "https://www.comprendre-mon-energie.fr/economies-denergie-le-guide-pratique-pour-reduire-vos-facture-en-2026/",
    "https://www.comprendre-mon-energie.fr/choisir-votre-accompagnement/",
    "https://www.comprendre-mon-energie.fr/reduire-vos-factures-delectricte/",
]
CHEMINS_RELATIFS = [u.replace(WP_URL, "") for u in URLS_404]
SLUGS = [u.rstrip("/").rsplit("/", 1)[-1] for u in URLS_404]


def statut_http(url):
    try:
        r = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        chain = " -> ".join(str(h.status_code) for h in r.history) + (" -> " if r.history else "")
        return f"{chain}{r.status_code}", r.url
    except Exception as e:
        return f"ERREUR({e})", None


def chercher_par_slug(endpoint, slug):
    """endpoint = 'posts' ou 'pages'."""
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/{endpoint}",
            params={"slug": slug, "status": TOUS_STATUTS, "context": "edit"},
            auth=AUTH, timeout=TIMEOUT,
        )
        if r.status_code == 200 and r.json():
            return r.json()
        if r.status_code != 200:
            return [{"erreur": f"HTTP {r.status_code} : {r.text[:200]}"}]
    except Exception as e:
        return [{"erreur": str(e)}]
    return []


def lister_tout(endpoint):
    """Recupere id/link/content de tous les posts OU pages publies."""
    items = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/{endpoint}",
                params={"per_page": PER_PAGE, "page": page, "status": "publish",
                        "_fields": "id,link,content"},
                timeout=TIMEOUT,
            )
        except Exception as e:
            print(f"  ⚠️ erreur page {page} ({endpoint}) : {e}")
            break
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        items.extend(data)
        page += 1
        time.sleep(0.15)
    return items


def verifier_sitemaps():
    trouve = {url: False for url in URLS_404}
    try:
        r = requests.get(f"{WP_URL}/sitemap_index.xml", timeout=TIMEOUT)
        sous_sitemaps = re.findall(r'<loc>([^<]+)</loc>', r.text) if r.status_code == 200 else []
    except Exception as e:
        print(f"  ⚠️ Erreur sitemap_index.xml : {e}")
        return trouve
    print(f"  sitemap_index.xml -> HTTP {r.status_code}, {len(sous_sitemaps)} sous-sitemap(s)")
    # Cette fois on regarde TOUS les sous-sitemaps (post ET page), pas seulement 'post-sitemap'
    for sm in sous_sitemaps[:20]:
        try:
            r2 = requests.get(sm, timeout=TIMEOUT)
            if r2.status_code != 200:
                continue
            for url in URLS_404:
                if url in r2.text or url.rstrip("/") in r2.text:
                    trouve[url] = True
        except Exception:
            continue
        time.sleep(0.1)
    return trouve


def main():
    client_bq = init_bigquery()

    print("=" * 110)
    print("ETAPE 1-5 : statut live, historique_publications, statuts WP (posts ET pages), GSC, wp_url_mapping")
    print("=" * 110)

    for url, slug in zip(URLS_404, SLUGS):
        print(f"\n### {url}")
        print(f"    slug = {slug!r}")

        statut, url_finale = statut_http(url)
        print(f"    HTTP live : {statut}" + (f" (redirige vers {url_finale})" if url_finale and url_finale != url else ""))

        df = client_bq.query(f"""
            SELECT post_id, date_publication, silo, sous_silo_strategique,
                   titre, mot_cle, run_id, type_publication, url_wp
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE url_wp LIKE '%{slug}%' OR url_wp LIKE '%{slug}/'
            ORDER BY date_publication
        """).to_dataframe()
        if len(df) == 0:
            print("    historique_publications : AUCUNE ligne pour ce slug")
        else:
            for _, r in df.iterrows():
                print(f"    historique_publications : post_id={r['post_id']} | {r['date_publication']} | "
                      f"silo={r['silo']} | sous_silo={r['sous_silo_strategique']} | mot_cle={r['mot_cle']!r}")
                print(f"        titre={str(r['titre'])[:90]!r} | run_id={r['run_id']!r} | "
                      f"type_publication={r['type_publication']!r} | url_wp={r['url_wp']!r}")

        for endpoint in ("posts", "pages"):
            items = chercher_par_slug(endpoint, slug)
            if items:
                for p in items:
                    if "erreur" in p:
                        print(f"    Recherche WP /{endpoint} par slug (tous statuts) : erreur -> {p['erreur']}")
                    else:
                        extra = f", categories={p.get('categories')!r}" if endpoint == "posts" else ""
                        print(f"    Recherche WP /{endpoint} par slug (tous statuts) : id={p.get('id')}, "
                              f"status={p.get('status')!r}, slug reel={p.get('slug')!r}, link={p.get('link')!r}{extra}")
            else:
                mot = "page" if endpoint == "pages" else "post"
                print(f"    Recherche WP /{endpoint} par slug (tous statuts) : AUCUN(e) {mot}, meme en corbeille/brouillon")

        df_gsc = client_bq.query(f"""
            SELECT COUNT(*) AS n, SUM(impressions) AS impressions, SUM(clics) AS clics,
                   MIN(date) AS premiere_date, MAX(date) AS derniere_date
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE page LIKE '%{slug}%'
        """).to_dataframe()
        n_gsc = int(df_gsc.iloc[0]["n"])
        if n_gsc == 0:
            print("    01_raw.gsc_queries : AUCUNE ligne (meme partielle/LIKE) pour ce slug")
        else:
            r = df_gsc.iloc[0]
            print(f"    01_raw.gsc_queries : {n_gsc} ligne(s), impressions={r['impressions']}, "
                  f"clics={r['clics']}, periode {r['premiere_date']} -> {r['derniere_date']}")

        df_map = client_bq.query(f"""
            SELECT post_id, url
            FROM `{PROJECT_ID}.02_cleaned.wp_url_mapping`
            WHERE url LIKE '%{slug}%'
        """).to_dataframe()
        if len(df_map) == 0:
            print("    02_cleaned.wp_url_mapping : AUCUNE ligne pour ce slug")
        else:
            for _, r in df_map.iterrows():
                print(f"    02_cleaned.wp_url_mapping : post_id={r['post_id']} | url={r['url']!r}")

    print("\n" + "=" * 110)
    print("ETAPE 6 : sitemaps XML live (tous les sous-sitemaps, posts et pages)")
    print("=" * 110)
    presence_sitemap = verifier_sitemaps()
    for url, present in presence_sitemap.items():
        print(f"    {'PRESENT' if present else 'absent'} dans un sitemap : {url}")

    print("\n" + "=" * 110)
    print("ETAPE 7 : scan EXHAUSTIF du maillage interne (TOUS les posts ET TOUTES les pages publies)")
    print("=" * 110)
    print("Recuperation de tous les posts publies (contenu complet)...")
    posts = lister_tout("posts")
    print(f"{len(posts)} post(s) recupere(s).")
    print("Recuperation de toutes les pages publiees (contenu complet)...")
    pages = lister_tout("pages")
    print(f"{len(pages)} page(s) recuperee(s).\n")

    tout = [("post", p) for p in posts] + [("page", p) for p in pages]

    trouvailles = {url: [] for url in URLS_404}
    for type_contenu, item in tout:
        contenu = item.get("content", {}).get("rendered", "") or ""
        for url, chemin_rel in zip(URLS_404, CHEMINS_RELATIFS):
            if url in contenu or url.rstrip("/") in contenu or chemin_rel in contenu or chemin_rel.rstrip("/") in contenu:
                trouvailles[url].append(f"[{type_contenu}] {item.get('link')}")

    total = 0
    for url, sources in trouvailles.items():
        if sources:
            total += len(sources)
            print(f"\n*** {url} ***")
            print(f"    LIE DEPUIS {len(sources)} contenu(s) :")
            for s in sources:
                print(f"        - {s}")
        else:
            print(f"\n{url} : aucun lien interne trouve (dans {len(posts)} posts + {len(pages)} pages)")

    print(f"\n{'=' * 110}")
    print(f"TOTAL : {total} lien(s) interne(s) trouve(s) vers les 12 URLs, sur {len(posts)} posts + {len(pages)} pages scannes.")
    print("=" * 110)


if __name__ == "__main__":
    main()
