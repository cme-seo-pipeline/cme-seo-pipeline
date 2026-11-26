"""
CME — Diagnostic de l'audit Ahrefs du 21/11/2026 (PDF partage par l'operateur
le 26/11/2026, Site Audit, comparaison avec le 14/11).

Le PDF ne montre que la vue d'ensemble (pas le detail par URL) — ce script
reconstruit lui-meme, a partir de nos propres sources (sitemap XML live +
API REST WordPress publique, sans authentification), les 3 ecarts les plus
gros/actionnables vus dans le rapport :
  - "Indexable page not in sitemap"   (Ahrefs : 506 URLs)
  - "Page in multiple sitemaps"       (Ahrefs : 244 URLs)
  - "3XX redirect in sitemap"         (Ahrefs : 4 URLs, erreur)

Meme methodologie que les audits 404 precedents (02/11, 25/11) : lecture
seule, pont GitHub Actions (le sandbox Claude Code ne peut pas joindre le
site live directement).

LECTURE SEULE. Aucune authentification necessaire (endpoints publics).
"""
import time
import xml.etree.ElementTree as ET
from collections import defaultdict

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
TIMEOUT = 20
PER_PAGE = 100
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def lister_tout(endpoint):
    items = []
    page = 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/{endpoint}",
            params={
                "per_page": PER_PAGE,
                "page": page,
                "status": "publish",
                "_fields": "id,link,slug",
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 400:
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        items.extend(batch)
        if len(batch) < PER_PAGE:
            break
        page += 1
        time.sleep(0.15)
    return items


def recuperer_sous_sitemaps():
    r = requests.get(f"{WP_URL}/sitemap_index.xml", timeout=TIMEOUT)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    urls = [el.find("sm:loc", NS).text for el in root.findall("sm:sitemap", NS)]
    if not urls:
        # Repli : certains sites exposent /sitemap.xml plutot qu'un index
        urls = [f"{WP_URL}/sitemap.xml"]
    return urls


def recuperer_urls_sitemap(sous_sitemap_url):
    r = requests.get(sous_sitemap_url, timeout=TIMEOUT)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    urls = []
    for el in root.findall("sm:url", NS):
        loc = el.find("sm:loc", NS)
        if loc is not None and loc.text:
            urls.append(loc.text.rstrip("/"))
    return urls


def statut_http(url, session):
    try:
        r = session.head(url, timeout=TIMEOUT, allow_redirects=False)
        if r.status_code in (405, 403):
            r = session.get(url, timeout=TIMEOUT, allow_redirects=False)
        return r.status_code, r.headers.get("Location")
    except Exception as e:
        return None, str(e)


def main():
    print("=" * 100)
    print("1. SOUS-SITEMAPS")
    print("=" * 100)
    sous_sitemaps = recuperer_sous_sitemaps()
    print(f"{len(sous_sitemaps)} sous-sitemap(s) trouve(s) via sitemap_index.xml.")

    urls_par_sitemap = {}
    compte_urls = defaultdict(int)
    for sm in sous_sitemaps:
        try:
            urls = recuperer_urls_sitemap(sm)
        except Exception as e:
            print(f"  ⚠️ Erreur sur {sm} : {e}")
            continue
        urls_par_sitemap[sm] = urls
        for u in urls:
            compte_urls[u] += 1
        print(f"  {sm} -> {len(urls)} URL(s)")
        time.sleep(0.2)

    toutes_urls_sitemap = set(compte_urls.keys())
    print(f"\nTotal URLs uniques dans les sitemaps : {len(toutes_urls_sitemap)}")
    print(f"Total d'entrees (avec doublons)        : {sum(compte_urls.values())}")

    print()
    print("=" * 100)
    print("2. PAGES PRESENTES DANS PLUS D'UN SOUS-SITEMAP")
    print("=" * 100)
    doublons = {u: c for u, c in compte_urls.items() if c > 1}
    print(f"{len(doublons)} URL(s) presente(s) dans plus d'un sous-sitemap.")
    for u, c in sorted(doublons.items(), key=lambda kv: -kv[1])[:40]:
        sms = [sm for sm, urls in urls_par_sitemap.items() if u in urls]
        print(f"  [{c}x] {u}")
        for sm in sms:
            print(f"      -> {sm}")
    if len(doublons) > 40:
        print(f"  ... et {len(doublons) - 40} de plus (tronque a 40 pour lisibilite)")

    print()
    print("=" * 100)
    print("3. CONTENU INDEXABLE WP (posts + pages, status=publish)")
    print("=" * 100)
    posts = lister_tout("posts")
    pages = lister_tout("pages")
    print(f"{len(posts)} post(s) publie(s), {len(pages)} page(s) publiee(s).")
    contenu_indexable = [("post", p) for p in posts] + [("page", p) for p in pages]
    urls_indexables = {item["link"].rstrip("/"): type_ for type_, item in contenu_indexable}

    print()
    print("=" * 100)
    print("4. INDEXABLE MAIS ABSENT DE TOUT SOUS-SITEMAP")
    print("=" * 100)
    manquants = sorted(u for u in urls_indexables if u not in toutes_urls_sitemap)
    print(f"{len(manquants)} URL(s) indexable(s) absente(s) de tout sous-sitemap.")
    for u in manquants[:60]:
        print(f"  [{urls_indexables[u]}] {u}")
    if len(manquants) > 60:
        print(f"  ... et {len(manquants) - 60} de plus (tronque a 60 pour lisibilite)")

    print()
    print("=" * 100)
    print("5. URLS DU SITEMAP QUI REDIRIGENT (3xx) — scan complet")
    print("=" * 100)
    session = requests.Session()
    a_verifier = sorted(toutes_urls_sitemap)
    trouve_3xx = []
    erreurs_reseau = 0
    for i, u in enumerate(a_verifier):
        statut, loc = statut_http(u, session)
        if statut is None:
            erreurs_reseau += 1
        elif 300 <= statut < 400:
            trouve_3xx.append((u, statut, loc))
        if i % 200 == 0 and i > 0:
            print(f"  ... {i}/{len(a_verifier)} verifiees ({len(trouve_3xx)} 3xx trouves jusqu'ici)")
    print(f"\n{len(trouve_3xx)} URL(s) du sitemap renvoient un 3xx (sur {len(a_verifier)} verifiees, {erreurs_reseau} erreur(s) reseau) :")
    for u, s, loc in trouve_3xx:
        print(f"  [{s}] {u} -> {loc}")

    print()
    print("=" * 100)
    print("RESUME")
    print("=" * 100)
    print(f"Sous-sitemaps               : {len(sous_sitemaps)}")
    print(f"URLs uniques en sitemap      : {len(toutes_urls_sitemap)}")
    print(f"URLs en double (sitemaps)    : {len(doublons)}")
    print(f"Indexable absent du sitemap  : {len(manquants)}")
    print(f"Sitemap -> 3xx               : {len(trouve_3xx)}")


if __name__ == "__main__":
    main()
