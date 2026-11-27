"""
CME — Complement au diagnostic "Slow page" du 27/11/2026
(diagnostiquer_lenteur_pages_2711.py).

Ce premier diagnostic a mesure un TTFB uniformement eleve (~900ms-1s, y
compris sur la page la plus "rapide" de l'echantillon) ET une absence
TOTALE d'entete de cache (x-litespeed-cache, age, cache-control...) sur
les 103 pages testees -- une seule requete par URL. Ca laisse une question
ouverte : est-ce que le cache LiteSpeed finit par servir ces pages au
2e hit (vrai cache MISS->HIT normal), ou bien ces pages ne sont-elles
JAMAIS servies depuis le cache de page (cache desactive/exclu/jamais
alimente pour ces gabarits) ?

Ce script reinterroge les 15 URLs les plus lentes du diagnostic precedent
(+ la page d'accueil), chacune 3 FOIS DE SUITE (meme UA navigateur), pour
voir si le temps de reponse chute au 2e/3e hit (preuve d'un cache qui
finit par s'activer) ou reste constant (preuve que le cache ne sert
jamais ces pages).

LECTURE SEULE, endpoints publics, aucune authentification necessaire.
"""
import time

import requests

TIMEOUT = 25
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
HEADERS_A_RELEVER = [
    "x-litespeed-cache",
    "x-litespeed-cache-control",
    "x-qc-cache",
    "x-cache",
    "cf-cache-status",
    "age",
    "cache-control",
    "server",
]

URLS = [
    "https://www.comprendre-mon-energie.fr/gaz/demenagement-gaz/resilier-contrat-gaz-demenagement/",
    "https://www.comprendre-mon-energie.fr/solaire/batterie-panneaux-solaires/",
    "https://www.comprendre-mon-energie.fr/gaz/facture-gaz/aides-facture-gaz-2024/",
    "https://www.comprendre-mon-energie.fr/gaz/demenagement-gaz/comment-fonctionne-gaz-naturel/",
    "https://www.comprendre-mon-energie.fr/solaire/kit-solaire/",
    "https://www.comprendre-mon-energie.fr/renovation-energetique/renovation-globale/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/tva-reduite/tva-reduite-calculer-economies/",
    "https://www.comprendre-mon-energie.fr/gaz/facture-gaz/lire-facture-gaz-explications/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/prime-energie/prime-energie-cee-fonctionnement/",
    "https://www.comprendre-mon-energie.fr/solaire/",
    "https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/aides-electricite-2026/",
    "https://www.comprendre-mon-energie.fr/electricite/compteur/compteur-linky-fonctionnement/",
    "https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/changement-fournisseur-electricite-procedure/",
    "https://www.comprendre-mon-energie.fr/renovation-energetique/",
    "https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/tarif-reglemente-vs-marche-libre/",
    "https://www.comprendre-mon-energie.fr/",
]


def mesurer(url):
    try:
        t0 = time.monotonic()
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, stream=True)
        ttfb = time.monotonic() - t0
        entetes = {h: r.headers.get(h) for h in HEADERS_A_RELEVER if r.headers.get(h)}
        statut = r.status_code
        r.close()
        return ttfb, statut, entetes, None
    except Exception as e:
        return None, None, {}, str(e)[:150]


def main():
    print(f"{len(URLS)} URLs, 3 requetes successives chacune (meme UA navigateur).\n")
    for i, url in enumerate(URLS, 1):
        mesures = []
        for hit in range(1, 4):
            ttfb, statut, entetes, err = mesurer(url)
            mesures.append((ttfb, statut, entetes, err))
            time.sleep(1.5)
        ligne = " | ".join(
            f"hit{h+1}={m[0]*1000:.0f}ms" if m[0] is not None else f"hit{h+1}=ERR"
            for h, m in enumerate(mesures)
        )
        entetes_derniere = mesures[-1][2]
        print(f"[{i}/{len(URLS)}] {ligne}   entetes(dernier hit)={entetes_derniere}   {url}")

    print("\nSi hit2/hit3 restent proches de hit1 (pas de chute vers ~100-200ms),")
    print("le cache de page ne sert jamais ces URLs -- chaque requete, meme repetee")
    print("immediatement, retombe sur un rendu PHP/WordPress complet.")


if __name__ == "__main__":
    main()
