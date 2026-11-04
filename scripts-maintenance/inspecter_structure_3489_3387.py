"""
CME — Inspection (lecture seule) de la structure en enfants directs des
articles id=3489 et id=3387 : le correctif "bloc Colonnes" deploye le
04/11 fonctionne parfaitement sur id=2218 (7 formulaires 'contact'
desormais inseres a l'interieur du wp-block-column), mais id=3489 et
id=3387 n'ont TOUJOURS aucun formulaire 'contact' apres deploiement +
simulation d'interaction (verifier_fix_colonnes_en_conditions_reelles.py).
Hypothese : leur contenu est enveloppe dans un autre type de conteneur
que wp-block-columns/wp-block-column (le seul gere par le correctif),
par exemple wp-block-group, wp-block-cover, ou une classe personnalisee.

LECTURE SEULE -- aucune ecriture. Lit l'API REST WordPress publique.

USAGE :
  python3 inspecter_structure_3489_3387.py
"""
import requests
from bs4 import BeautifulSoup

SITE = "https://www.comprendre-mon-energie.fr"


def inspecter(post_id):
    resp = requests.get(f"{SITE}/wp-json/wp/v2/posts/{post_id}", params={"_fields": "id,link,content"}, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ HTTP {resp.status_code}")
        return
    html = (resp.json().get("content") or {}).get("rendered", "")
    soup = BeautifulSoup(html, "html.parser")
    enfants = [c for c in soup.contents if getattr(c, "name", None)]
    print(f"  {len(enfants)} enfant(s) direct(s) :")
    for idx, el in enumerate(enfants):
        classes = " ".join(el.get("class", []))
        nb_mots = len(el.get_text(separator=" ").strip().split())
        nb_p_imbriques = len(el.find_all("p"))
        print(f"    [{idx}] <{el.name} class=\"{classes}\"> | {nb_mots} mots | {nb_p_imbriques} <p> imbrique(s)")


def main():
    print("=" * 90)
    print("id=3489 (renovation-energetique)")
    print("=" * 90)
    inspecter(3489)

    print("\n" + "=" * 90)
    print("id=3387 (comparateur-electricite)")
    print("=" * 90)
    inspecter(3387)


if __name__ == "__main__":
    main()
