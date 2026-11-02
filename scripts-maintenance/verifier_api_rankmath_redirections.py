"""
CME — Verifie si une creation PROGRAMMATIQUE de redirections 301 est
possible sur le site (demande operateur du 02/11/2026, suite au blocage
deja identifie : aucun mecanisme de creation de 301 trouve dans ce repo).

Approche : interroge la racine de decouverte REST WordPress
(/wp-json/, publique, liste tous les namespaces enregistres par les
plugins actifs, qu'ils necessitent une auth ou non) pour confirmer si
RankMath expose un namespace REST, puis tente de lister ses routes. Si le
namespace "rankmath/v1" existe et expose une route de redirections, verifie
ensuite (authentifie, avec le compte WP_USERNAME/WP_APP_PASSWORD deja
utilise par le pipeline) si une LECTURE simple (GET) y est autorisee --
sans jamais rien creer ni modifier.

LECTURE SEULE. N'ecrit, ne cree, ne modifie AUCUNE redirection.
"""
import os
import sys

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
TIMEOUT = 15
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")


def main():
    print("=" * 100)
    print("1) Decouverte REST (/wp-json/) -- namespaces enregistres par les plugins actifs")
    print("=" * 100)
    try:
        r = requests.get(f"{WP_URL}/wp-json/", timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        sys.exit(f"❌ Decouverte REST impossible : {e}")

    namespaces = data.get("namespaces", [])
    print(f"{len(namespaces)} namespace(s) trouve(s).")
    pertinents = [n for n in namespaces if "rankmath" in n.lower() or "redirect" in n.lower() or "seo" in n.lower()]
    print(f"Namespaces lies SEO/redirections : {pertinents or '(aucun)'}")

    if not any("rankmath" in n.lower() for n in namespaces):
        print("\n❌ Aucun namespace 'rankmath*' enregistre -- RankMath n'expose pas (ou ne le permet pas)")
        print("   de REST API sur ce site, du moins pas sous ce nom attendu.")
        print("   Verifier aussi si un plugin dedie 'Redirection' (namespace 'redirection/v1') existe :")
        print(f"   présent : {any('redirection' in n.lower() for n in namespaces)}")
        return

    print("\n" + "=" * 100)
    print("2) Routes exposees par le(s) namespace(s) RankMath")
    print("=" * 100)
    routes = data.get("routes", {})
    routes_rankmath = {path: info for path, info in routes.items() if "rankmath" in path.lower()}
    for path in sorted(routes_rankmath):
        print(f"    {path}")
    routes_redirect = [p for p in routes_rankmath if "redirect" in p.lower()]
    print(f"\nRoutes mentionnant 'redirect' : {routes_redirect or '(aucune)'}")

    if not routes_redirect:
        print("\n⚠️ RankMath expose une API REST mais aucune route visible ne mentionne les redirections --")
        print("   soit le module Redirections n'est pas active sur ce site, soit il n'est pas expose en REST.")
        return

    print("\n" + "=" * 100)
    print("3) Test de lecture authentifie sur la 1ere route de redirections trouvee (GET uniquement)")
    print("=" * 100)
    route_test = routes_redirect[0]
    try:
        r2 = requests.get(
            f"{WP_URL}{route_test}",
            auth=(WP_USERNAME, WP_APP_PASSWORD),
            timeout=TIMEOUT,
        )
        print(f"GET {route_test} -> HTTP {r2.status_code}")
        print(r2.text[:1500])
    except Exception as e:
        print(f"❌ Erreur lors du test GET : {e}")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
