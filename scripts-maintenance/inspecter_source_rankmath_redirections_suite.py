"""
CME — Suite de inspecter_source_rankmath_redirections.py : extrait le
corps complet de update_redirection(), get_update_redirection_args() et
get_redirection_permissions_check() depuis la source PUBLIQUE du plugin
RankMath (wordpress.org), pour connaitre le format exact du payload et
les exigences d'authentification avant toute creation reelle de
redirection en prod.

LECTURE SEULE. Ne touche a aucun moment au site comprendre-mon-energie.fr.
"""
import io
import re
import zipfile

import requests

URL_ZIP = "https://downloads.wordpress.org/plugin/seo-by-rank-math.latest-stable.zip"
TIMEOUT = 60


def extraire_fonction(contenu, nom_fonction):
    """Extrait le corps d'une fonction PHP par comptage d'accolades,
    a partir de la 1ere occurrence de 'function nom_fonction('."""
    m = re.search(r"function\s+" + re.escape(nom_fonction) + r"\s*\([^)]*\)\s*\{", contenu)
    if not m:
        return None
    depart = m.start()
    i = contenu.index("{", m.end() - 1)
    profondeur = 0
    for j in range(i, len(contenu)):
        if contenu[j] == "{":
            profondeur += 1
        elif contenu[j] == "}":
            profondeur -= 1
            if profondeur == 0:
                return contenu[depart:j + 1]
    return contenu[depart:depart + 3000]


def main():
    print(f"Telechargement de {URL_ZIP} ...")
    r = requests.get(URL_ZIP, timeout=TIMEOUT)
    r.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(r.content))

    cibles = {
        "seo-by-rank-math/includes/rest/class-shared.php": [
            "update_redirection", "get_update_redirection_args",
        ],
        "seo-by-rank-math/includes/rest/class-rest-helper.php": [
            "get_redirection_permissions_check",
        ],
    }
    # Au cas ou le nom de fichier exact differe, recherche aussi par contenu.
    noms = zf.namelist()
    fichier_helper = next((n for n in noms if n.lower().endswith("class-rest-helper.php")), None)
    if fichier_helper:
        cibles.setdefault(fichier_helper, []).append("get_redirection_permissions_check")

    for chemin, fonctions in cibles.items():
        if chemin not in noms:
            print(f"\n⚠️ Fichier absent de l'archive : {chemin}")
            continue
        contenu = zf.read(chemin).decode("utf-8", errors="replace")
        for fn in fonctions:
            corps = extraire_fonction(contenu, fn)
            print(f"\n{'=' * 100}\n{chemin} :: {fn}()\n{'=' * 100}")
            print(corps if corps else "(introuvable)")


if __name__ == "__main__":
    main()
