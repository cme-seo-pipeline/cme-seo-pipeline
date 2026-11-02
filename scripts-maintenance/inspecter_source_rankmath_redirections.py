"""
CME — Telecharge la source PUBLIQUE du plugin RankMath (wordpress.org,
aucun rapport avec le site comprendre-mon-energie.fr) pour determiner le
format exact attendu par la route REST /rankmath/v1/updateRedirection
(methode HTTP, permission_callback, payload) avant toute tentative de
creation reelle de redirection en prod -- rigueur demandee par
l'operateur, pas de tentative a l'aveugle sur un site live.

LECTURE SEULE. Ne touche a aucun moment au site comprendre-mon-energie.fr.
"""
import re
import sys
import zipfile
import io

import requests

URL_ZIP = "https://downloads.wordpress.org/plugin/seo-by-rank-math.latest-stable.zip"
TIMEOUT = 60


def main():
    print(f"Telechargement de {URL_ZIP} ...")
    r = requests.get(URL_ZIP, timeout=TIMEOUT)
    r.raise_for_status()
    print(f"{len(r.content) / 1_000_000:.1f} Mo telecharges.\n")

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    noms = zf.namelist()

    candidats = [n for n in noms if "redirect" in n.lower() and n.endswith(".php")]
    print("=" * 100)
    print(f"Fichiers PHP lies aux redirections ({len(candidats)}) :")
    print("=" * 100)
    for n in candidats:
        print(f"  {n}")

    print("\n" + "=" * 100)
    print("Recherche de 'updateRedirection' / enregistrement de routes REST")
    print("=" * 100)
    for n in noms:
        if not n.endswith(".php"):
            continue
        try:
            contenu = zf.read(n).decode("utf-8", errors="replace")
        except Exception:
            continue
        if "updateRedirection" in contenu or ("register_rest_route" in contenu and "redirect" in contenu.lower()):
            print(f"\n--- {n} ---")
            for m in re.finditer(r".{0,200}updateRedirection.{0,400}", contenu, re.DOTALL):
                print(m.group(0))
                print("...")
            for m in re.finditer(r".{0,100}register_rest_route\([^;]{0,500};", contenu, re.DOTALL):
                if "redirect" in m.group(0).lower() or "Redirect" in m.group(0):
                    print(m.group(0))
                    print("...")

    print("\n" + "=" * 100)
    print("Classe Redirection -- methodes publiques (save/create/from_array)")
    print("=" * 100)
    fichiers_classe = [n for n in candidats if "class-redirection" in n.lower() and "redirections" not in n.lower().split("/")[-1]]
    fichiers_classe += [n for n in candidats if n.lower().endswith("class-redirection.php")]
    for n in set(fichiers_classe):
        try:
            contenu = zf.read(n).decode("utf-8", errors="replace")
        except Exception:
            continue
        print(f"\n--- {n} ---")
        for m in re.finditer(r"(public static function|public function)\s+\w+\s*\([^)]*\)", contenu):
            print(f"  {m.group(0)}")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
