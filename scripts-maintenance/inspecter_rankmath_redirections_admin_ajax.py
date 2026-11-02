"""
CME — Verifie si le module Redirections de RankMath (le vrai gestionnaire
"source arbitraire -> destination", pas le metabox par article deja
ecarte par inspecter_source_rankmath_redirections_suite.py) expose une
action admin-ajax ou une route REST generique de creation, et si son
controle d'acces repose sur un nonce de session (bloquant pour un acces
par Application Password) ou sur une simple capacite utilisateur.

LECTURE SEULE. Ne touche a aucun moment au site comprendre-mon-energie.fr.
"""
import io
import re
import zipfile

import requests

URL_ZIP = "https://downloads.wordpress.org/plugin/seo-by-rank-math.latest-stable.zip"
TIMEOUT = 60


def main():
    print(f"Telechargement de {URL_ZIP} ...")
    r = requests.get(URL_ZIP, timeout=TIMEOUT)
    r.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(r.content))

    chemin = "seo-by-rank-math/includes/modules/redirections/class-admin.php"
    contenu = zf.read(chemin).decode("utf-8", errors="replace")

    print("=" * 100)
    print(f"{chemin} :: actions ajax / routes enregistrees")
    print("=" * 100)
    for m in re.finditer(r"add_action\(\s*'wp_ajax[^']*'[^;]{0,200};", contenu):
        print(m.group(0))
    for m in re.finditer(r"register_rest_route\([^;]{0,400};", contenu, re.DOTALL):
        print(m.group(0))

    print("\n" + "=" * 100)
    print("Verification de check_ajax_referer / wp_verify_nonce dans ce fichier")
    print("=" * 100)
    for m in re.finditer(r".{0,80}(check_ajax_referer|wp_verify_nonce|current_user_can).{0,120}", contenu):
        print(m.group(0).strip())

    # class-table.php gere l'ecran (liste/bulk actions) -- verifie aussi.
    chemin2 = "seo-by-rank-math/includes/modules/redirections/class-table.php"
    contenu2 = zf.read(chemin2).decode("utf-8", errors="replace")
    print("\n" + "=" * 100)
    print(f"{chemin2} :: nonce / capacite")
    print("=" * 100)
    for m in re.finditer(r".{0,80}(check_ajax_referer|wp_verify_nonce|current_user_can|check_admin_referer).{0,120}", contenu2):
        print(m.group(0).strip())


if __name__ == "__main__":
    main()
