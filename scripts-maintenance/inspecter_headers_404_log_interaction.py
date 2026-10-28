"""
CME — Diagnostic ponctuel (lecture seule) : le fichier cme-tracking-
conversion.php uploade le 28/10 contient bien register_rest_route('cme/v1',
'/log-interaction', ...) (confirme visuellement par l'operateur en cPanel),
mais la route repond toujours 404 en live. Ce script inspecte les
en-tetes HTTP de la reponse pour distinguer deux hypotheses :
  - une couche de cache (CDN, LiteSpeed edge, reverse proxy) qui sert
    encore l'ancien 404 -- se verrait via des en-tetes type Age/X-Cache/
    CF-Cache-Status/X-LiteSpeed-Cache
  - OPcache PHP (bytecode compile en cache, independant du plugin
    LiteSpeed Cache deja purge) -- la reponse aurait alors des en-tetes
    WordPress standard, sans aucun signal de cache

Compare aussi avec la route /log-lead (fonctionnelle, meme fichier, meme
mecanisme de registration) pour voir si le comportement differe.

Lecture seule.

USAGE :
  python3 inspecter_headers_404_log_interaction.py
"""
import requests

WP_URL = "https://www.comprendre-mon-energie.fr"

ROUTES = [
    "/wp-json/cme/v1/log-interaction",
    "/wp-json/cme/v1/log-lead",
    "/wp-json/",
]


def main():
    for route in ROUTES:
        print(f"{'='*70}\n{route}\n{'='*70}")
        try:
            r = requests.get(f"{WP_URL}{route}", timeout=20)
            print(f"HTTP {r.status_code}")
            for h in ["Age", "X-Cache", "CF-Cache-Status", "X-LiteSpeed-Cache",
                      "X-Litespeed-Cache", "Cache-Control", "X-Proxy-Cache",
                      "Server", "Date", "ETag", "Via"]:
                if h in r.headers:
                    print(f"  {h}: {r.headers[h]}")
            print()
        except Exception as e:
            print(f"  ⚠️ Erreur : {e}\n")


if __name__ == "__main__":
    main()
