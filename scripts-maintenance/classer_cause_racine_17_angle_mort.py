"""
CME — Classification (lecture seule) de la cause racine exacte, pour les
17 articles en "angle mort total" + 5 en "deficit partiel marque" trouves
par auditer_angle_mort_colonnes_cta.py (04/11/2026).

Le correctif deploye ce soir (wp-block-columns/wp-block-column) est
confirme fonctionnel en conditions reelles sur id=2218 (7/7 formulaires
desormais inseres). Mais id=3489 et id=3387 montrent TOUJOURS 0
formulaire 'contact' apres deploiement + interaction simulee -- leur
contenu est en realite enveloppe dans un <article> brut (pas un bloc
Gutenberg Colonnes), cause racine DIFFERENTE, non couverte par le
correctif de ce soir.

Classe chaque article selon le ou les types d'enfant(s) direct(s) qui
portent le plus de mots : 'columns' (wp-block-columns/wp-block-column,
deja corrige), 'article' (balise <article> brute, pas corrige), 'autre'
(aucun des deux, a investiguer au cas par cas).

LECTURE SEULE -- aucune ecriture.

USAGE :
  python3 classer_cause_racine_17_angle_mort.py
"""
import requests
from bs4 import BeautifulSoup

SITE = "https://www.comprendre-mon-energie.fr"

# Les 17 "angle mort total" + 5 "deficit partiel marque" (id=4966, 3387,
# 563, 699, 5804) de l'audit du 04/11 -- id=2218 et id=709 exclus (deja
# traites/compris separement : 2218 confirme corrige, 709 est un cas de
# longueur editoriale, pas structurel).
IDS_A_CLASSER = [
    3489, 3488, 3491, 3384, 3385, 1333, 1006, 904, 851, 844, 842, 663, 661, 561, 557, 538,
    4966, 3387, 563, 699, 5804,
]


def classer(post_id):
    resp = requests.get(f"{SITE}/wp-json/wp/v2/posts/{post_id}", params={"_fields": "id,content"}, timeout=30)
    if resp.status_code != 200:
        return post_id, "ERREUR", f"HTTP {resp.status_code}"
    html = (resp.json().get("content") or {}).get("rendered", "")
    soup = BeautifulSoup(html, "html.parser")
    enfants = [c for c in soup.contents if getattr(c, "name", None)]

    def mots(el):
        t = el.get_text(separator=" ").strip()
        return len(t.split()) if t else 0

    # L'enfant direct qui porte le plus de mots -- c'est generalement lui
    # qui determine si l'article est bloque ou pas.
    if not enfants:
        return post_id, "VIDE", "aucun enfant direct"
    plus_gros = max(enfants, key=mots)
    classes = " ".join(plus_gros.get("class", []))
    nb_mots_plus_gros = mots(plus_gros)

    if plus_gros.name == "div" and ("wp-block-columns" in classes or "wp-block-column" in classes):
        cause = "columns (deja corrige)"
    elif plus_gros.name == "article":
        cause = "article brut (PAS corrige)"
    else:
        cause = "autre (a investiguer)"

    return post_id, cause, f"<{plus_gros.name} class=\"{classes}\"> | {nb_mots_plus_gros} mots"


def main():
    compteur = {}
    for post_id in IDS_A_CLASSER:
        pid, cause, detail = classer(post_id)
        compteur[cause] = compteur.get(cause, 0) + 1
        print(f"  id={pid:5d} | {cause:28s} | {detail}")

    print("\n" + "=" * 90)
    print("Resume")
    print("=" * 90)
    for cause, nb in sorted(compteur.items(), key=lambda x: -x[1]):
        print(f"  {cause} : {nb}")


if __name__ == "__main__":
    main()
