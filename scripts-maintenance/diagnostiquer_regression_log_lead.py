"""
CME — Diagnostic URGENT (lecture seule) : apres le redeploiement du
28/10 de cme-tracking-conversion.php (pour ajouter la route
/log-interaction), la route /log-lead -- utilisee en PRODUCTION pour les
leads reels -- repond aussi 404. Determine si c'est une vraie casse du
fichier (toutes les routes cme/v1 disparues) ou un artefact de cache sur
la page precise testee pour le maillon 1.

Verifie, dans l'ordre :
  1. Le coeur de l'API REST WordPress fonctionne (route native /wp/v2/posts)
  2. Les en-tetes de la page article testee pour le maillon 1 (signes de
     cache HTML qui expliqueraient un JS "fige" malgre un PHP casse)
  3. Un appel direct en POST (pas GET) sur /log-lead avec un corps vide --
     si la route existe, WordPress renvoie une erreur de validation des
     parametres (400/500), PAS un 404 "rest_no_route"

Lecture seule -- aucune donnee de test envoyee avec des vraies infos.

USAGE :
  python3 diagnostiquer_regression_log_lead.py
"""
import requests

WP_URL = "https://www.comprendre-mon-energie.fr"


def main():
    print("="*70)
    print("1. Le coeur de l'API REST WordPress fonctionne-t-il ?")
    print("="*70)
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts", params={"per_page": 1}, timeout=20)
    print(f"  GET /wp-json/wp/v2/posts?per_page=1 -> HTTP {r.status_code}")
    print(f"  {'✅ API REST core OK' if r.status_code == 200 else '❌ API REST core cassee aussi !'}")

    print(f"\n{'='*70}")
    print("2. En-tetes de la page article testee pour le maillon 1")
    print(f"{'='*70}")
    url_article = f"{WP_URL}/solaire/kit-solaire/kit-solaire-vs-panneau-solaire-seul-comparatif/"
    r2 = requests.get(url_article, timeout=20)
    print(f"  GET {url_article} -> HTTP {r2.status_code}")
    for h in ["Age", "X-Cache", "X-LiteSpeed-Cache", "X-Litespeed-Cache",
              "Cache-Control", "Last-Modified", "ETag"]:
        if h in r2.headers:
            print(f"    {h}: {r2.headers[h]}")

    print(f"\n{'='*70}")
    print("3. POST direct sur /log-lead (corps vide -- teste juste l'EXISTENCE de la route)")
    print(f"{'='*70}")
    r3 = requests.post(f"{WP_URL}/wp-json/cme/v1/log-lead", json={}, timeout=20)
    print(f"  POST /wp-json/cme/v1/log-lead (corps vide) -> HTTP {r3.status_code}")
    print(f"  Corps : {r3.text[:250]}")
    if r3.status_code == 404:
        print("  ❌ Route reellement absente, meme en POST -- pas un probleme de methode HTTP")
    else:
        print("  ✅ Route presente (erreur de validation attendue sur un corps vide, pas 404)")

    print(f"\n{'='*70}")
    print("4. POST direct sur /log-interaction (meme logique)")
    print(f"{'='*70}")
    r4 = requests.post(f"{WP_URL}/wp-json/cme/v1/log-interaction", json=[], timeout=20)
    print(f"  POST /wp-json/cme/v1/log-interaction (liste vide) -> HTTP {r4.status_code}")
    print(f"  Corps : {r4.text[:250]}")


if __name__ == "__main__":
    main()
