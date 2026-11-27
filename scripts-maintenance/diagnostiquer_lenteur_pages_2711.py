"""
CME — Diagnostic "Slow page" / "Slow server response for AI crawlers"
(audit Ahrefs du 21/11/2026, PDF partage le 26/11/2026).

Le PDF ne donne que la vue d'ensemble (33 pages "Slow page", 1 "Slow server
response for AI crawlers", pas de detail par URL). Ce script mesure
lui-meme, sur un echantillon representatif de vraies pages live, le temps
de reponse serveur (TTFB = time-to-first-byte, approxime par le temps
ecoule jusqu'a reception des entetes HTTP en mode stream, methode standard
en l'absence d'un acces socket bas niveau) :

  1. Un echantillon stratifie d'articles par anciennete (pas seulement les
     plus recents) + toutes les pages statiques + les archives de
     categorie + la page d'accueil.
  2. Chaque URL interrogee DEUX FOIS avec un user-agent "normal" (navigateur)
     ET une fois avec un user-agent "crawler IA" (GPTBot, le plus repandu
     des UA de ce type) -- pour verifier si le serveur traite differemment
     (plus lentement) les requetes identifiables comme venant d'un crawler
     IA, hypothese directement liee a l'intitule "Slow server response for
     AI crawlers" plutot qu'au "Slow page" generique.
  3. Releve des entetes de cache pertinents (x-litespeed-cache,
     x-litespeed-cache-control, x-qc-cache, age, cache-control, server) sur
     chaque reponse, pour correler lenteur et etat du cache.

Meme contrainte que tous les diagnostics precedents de ce projet : le
sandbox Claude Code ne peut pas joindre le site live directement -- execute
via le pont GitHub Actions (maintenance-a-la-demande.yml), qui a l'acces
reseau complet.

LECTURE SEULE. Endpoints publics uniquement, aucune authentification
necessaire (pas de WP_APP_PASSWORD).
"""
import statistics
import time

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
TIMEOUT = 25
PER_PAGE = 100

UA_NORMAL = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
# GPTBot : le crawler IA le plus documente/repandu, choisi comme
# representant de la famille "AI crawler" visee par l'intitule Ahrefs.
UA_CRAWLER_IA = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.2 (+https://openai.com/gptbot)"

HEADERS_A_RELEVER = [
    "x-litespeed-cache",
    "x-litespeed-cache-control",
    "x-lsadc-cache",
    "x-qc-cache",
    "x-cache",
    "cf-cache-status",
    "age",
    "cache-control",
    "server",
]


def lister_tout(endpoint, fields="id,link,slug,date"):
    items = []
    page = 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/{endpoint}",
            params={
                "per_page": PER_PAGE,
                "page": page,
                "status": "publish",
                "_fields": fields,
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


def construire_echantillon():
    print("Recuperation des articles et pages publies (API REST, publique)...")
    posts = lister_tout("posts")
    pages = lister_tout("pages")
    cats = lister_tout("categories", fields="id,link,slug,count")
    print(f"  {len(posts)} articles, {len(pages)} pages, {len(cats)} categories.")

    posts_tries = sorted(posts, key=lambda p: p["date"])
    n = len(posts_tries)
    echantillon = []

    # Stratifie par anciennete : 10 articles a chaque quintile (plus ancien
    # -> plus recent), pas seulement les derniers publies.
    for q in range(5):
        debut = (n * q) // 5
        fin = (n * (q + 1)) // 5
        tranche = posts_tries[debut:fin]
        pas = max(1, len(tranche) // 10)
        for p in tranche[::pas][:10]:
            echantillon.append(("article", p["link"]))

    # Toutes les pages statiques.
    for p in pages:
        echantillon.append(("page statique", p["link"]))

    # Archives de categorie ayant du contenu (sous-silos + silos racine).
    for c in cats:
        if c.get("count", 0) > 0:
            echantillon.append(("archive categorie", c["link"]))

    # Page d'accueil.
    echantillon.append(("accueil", WP_URL + "/"))

    # Deduplique en gardant l'ordre.
    vus = set()
    dedupe = []
    for type_, url in echantillon:
        if url not in vus:
            vus.add(url)
            dedupe.append((type_, url))
    return dedupe


def mesurer(url, user_agent):
    """Mesure le temps jusqu'a reception des entetes (proxy de TTFB en
    l'absence d'acces socket bas niveau), en mode stream (ne telecharge
    pas le corps)."""
    try:
        t0 = time.monotonic()
        r = requests.get(
            url,
            headers={"User-Agent": user_agent},
            timeout=TIMEOUT,
            stream=True,
        )
        ttfb = time.monotonic() - t0
        entetes = {h: r.headers.get(h) for h in HEADERS_A_RELEVER if r.headers.get(h)}
        statut = r.status_code
        r.close()
        return ttfb, statut, entetes, None
    except Exception as e:
        return None, None, {}, str(e)[:150]


def main():
    echantillon = construire_echantillon()
    print(f"\nEchantillon final : {len(echantillon)} URLs uniques.\n")

    resultats = []  # (type_, url, ttfb_normal, ttfb_crawler, statut, entetes)

    for i, (type_, url) in enumerate(echantillon, 1):
        ttfb_n, statut_n, entetes_n, err_n = mesurer(url, UA_NORMAL)
        time.sleep(0.3)
        ttfb_c, statut_c, entetes_c, err_c = mesurer(url, UA_CRAWLER_IA)
        time.sleep(0.3)

        resultats.append(
            {
                "type": type_,
                "url": url,
                "ttfb_normal": ttfb_n,
                "ttfb_crawler": ttfb_c,
                "statut_normal": statut_n,
                "statut_crawler": statut_c,
                "entetes_normal": entetes_n,
                "err_normal": err_n,
                "err_crawler": err_c,
            }
        )
        marqueur_n = f"{ttfb_n*1000:.0f}ms" if ttfb_n is not None else f"ERR({err_n})"
        marqueur_c = f"{ttfb_c*1000:.0f}ms" if ttfb_c is not None else f"ERR({err_c})"
        print(f"[{i}/{len(echantillon)}] {type_:18s} normal={marqueur_n:>12s} crawler_ia={marqueur_c:>12s}  {url}")

    print("\n" + "=" * 100)
    print("RESUME")
    print("=" * 100)

    ttfb_normaux = [r["ttfb_normal"] for r in resultats if r["ttfb_normal"] is not None]
    ttfb_crawlers = [r["ttfb_crawler"] for r in resultats if r["ttfb_crawler"] is not None]

    if ttfb_normaux:
        ttfb_normaux_tri = sorted(ttfb_normaux)
        p50 = statistics.median(ttfb_normaux_tri)
        p90 = ttfb_normaux_tri[int(len(ttfb_normaux_tri) * 0.9)]
        print(f"\nUser-agent NORMAL (navigateur) -- {len(ttfb_normaux)} mesures reussies :")
        print(f"  Min={min(ttfb_normaux)*1000:.0f}ms  Median={p50*1000:.0f}ms  P90={p90*1000:.0f}ms  Max={max(ttfb_normaux)*1000:.0f}ms")

    if ttfb_crawlers:
        ttfb_crawlers_tri = sorted(ttfb_crawlers)
        p50c = statistics.median(ttfb_crawlers_tri)
        p90c = ttfb_crawlers_tri[int(len(ttfb_crawlers_tri) * 0.9)]
        print(f"\nUser-agent CRAWLER IA (GPTBot) -- {len(ttfb_crawlers)} mesures reussies :")
        print(f"  Min={min(ttfb_crawlers)*1000:.0f}ms  Median={p50c*1000:.0f}ms  P90={p90c*1000:.0f}ms  Max={max(ttfb_crawlers)*1000:.0f}ms")

    # Ecart normal vs crawler IA, par URL (paire).
    ecarts = []
    for r in resultats:
        if r["ttfb_normal"] is not None and r["ttfb_crawler"] is not None:
            ecarts.append((r["ttfb_crawler"] - r["ttfb_normal"], r["url"], r["ttfb_normal"], r["ttfb_crawler"]))
    if ecarts:
        ecarts.sort(reverse=True)
        print(f"\nTop 10 ecarts (crawler IA plus LENT que normal), sur {len(ecarts)} paires completes :")
        for ecart, url, tn, tc in ecarts[:10]:
            print(f"  +{ecart*1000:+.0f}ms  (normal={tn*1000:.0f}ms -> crawler={tc*1000:.0f}ms)  {url}")
        ecart_moyen = statistics.mean(e[0] for e in ecarts)
        print(f"  Ecart moyen (crawler - normal) sur l'echantillon : {ecart_moyen*1000:+.0f}ms")

    # Top 15 pages les plus lentes (UA normal), avec entetes de cache.
    avec_ttfb = [r for r in resultats if r["ttfb_normal"] is not None]
    avec_ttfb.sort(key=lambda r: -r["ttfb_normal"])
    print(f"\nTop 15 pages les plus lentes (UA normal) :")
    for r in avec_ttfb[:15]:
        print(f"  {r['ttfb_normal']*1000:.0f}ms  [{r['type']}]  entetes={r['entetes_normal']}  {r['url']}")

    # Repartition par type de page.
    print("\nMediane TTFB par type de page (UA normal) :")
    par_type = {}
    for r in avec_ttfb:
        par_type.setdefault(r["type"], []).append(r["ttfb_normal"])
    for type_, valeurs in par_type.items():
        print(f"  {type_:18s} n={len(valeurs):3d}  mediane={statistics.median(valeurs)*1000:.0f}ms  max={max(valeurs)*1000:.0f}ms")

    # Erreurs.
    erreurs = [r for r in resultats if r["err_normal"] or r["err_crawler"]]
    if erreurs:
        print(f"\n{len(erreurs)} URL(s) avec au moins une erreur reseau :")
        for r in erreurs:
            print(f"  {r['url']}  normal={r['err_normal']}  crawler={r['err_crawler']}")

    # Presence/absence d'un VRAI signal de cache (hors "server", toujours
    # present meme sans cache actif -- bug corrige le 27/11/2026 : l'ancienne
    # version comptait "entetes_normal non vide", qui ne pouvait jamais etre
    # vide puisque "server" y figure toujours).
    HEADERS_CACHE_REEL = [h for h in HEADERS_A_RELEVER if h != "server"]
    avec_cache = [
        r for r in avec_ttfb
        if any(h in r["entetes_normal"] for h in HEADERS_CACHE_REEL)
    ]
    sans_cache = [r for r in avec_ttfb if r not in avec_cache]
    print(f"\n{len(avec_cache)}/{len(avec_ttfb)} pages avec un VRAI entete de cache detecte (x-lsadc-cache ou equivalent).")
    print(f"{len(sans_cache)}/{len(avec_ttfb)} pages encore SANS aucun entete de cache.")
    if avec_cache:
        ttfb_avec_cache = [r["ttfb_normal"] for r in avec_cache]
        print(f"  TTFB median (pages AVEC cache)  : {statistics.median(ttfb_avec_cache)*1000:.0f}ms")
    if sans_cache:
        ttfb_sans_cache = [r["ttfb_normal"] for r in sans_cache]
        print(f"  TTFB median (pages SANS cache)  : {statistics.median(ttfb_sans_cache)*1000:.0f}ms")
    if sans_cache:
        print(f"\n  Pages encore sans cache (a surveiller) :")
        for r in sans_cache:
            print(f"    [{r['type']}] {r['url']}")


if __name__ == "__main__":
    main()
