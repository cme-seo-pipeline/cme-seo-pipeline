"""
CME — Suite de l'inspection du bouton telephone du header (lecture seule).

Le bouton est <a href="tel:..." class="btn-cta" style="font-size: 20px;">
dans un widget natif WordPress (zone "header-widget", id="block-58") --
voir scripts-maintenance/inspecter_bouton_telephone_header.py. Avant
d'ecrire une surcharge CSS (mu-plugin), on recupere ici les regles CSS
reelles de la classe .btn-cta dans les feuilles de style chargees par le
theme, pour savoir si la taille du bouton vient surtout du padding
(valeurs fixes en px ?) ou seulement du texte (font-size inline, deja
identifie).

Lecture seule. Necessite un acces reseau complet (runner GitHub Actions).
"""
import re
import requests

BASE = "https://www.comprendre-mon-energie.fr"


def main():
    resp = requests.get(BASE + "/", timeout=20, headers={"User-Agent": "Mozilla/5.0 (CME-QA-bot)"})
    html = resp.text

    feuilles = re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+)["\']', html)
    print(f"{len(feuilles)} feuille(s) de style trouvee(s) sur la page d'accueil.\n")

    for url in feuilles:
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = BASE + url
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (CME-QA-bot)"})
            if "btn-cta" in r.text:
                print("=" * 70)
                print(f"MATCH dans : {url}")
                print("=" * 70)
                for m in re.finditer(r'\.btn-cta[^{]*\{[^}]*\}', r.text):
                    print(m.group(0))
                print()
        except Exception as e:
            print(f"⚠️ Erreur sur {url} : {e}")


if __name__ == "__main__":
    main()
