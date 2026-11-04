"""
CME — Verification (lecture seule) de la structure en ENFANTS DIRECTS du
contenu de 2 articles, pour confirmer/infirmer une hypothese de root cause :

- id=2218 (attestation-de-contrat-delectricite) : le diagnostic precedent
  (diagnostiquer_cta_manquant_et_cache_obsolete.py) a trouve 67 <p>, 6
  <table>, 9 <figure>... en recherche RECURSIVE (BeautifulSoup find_all),
  mais seulement 3 <div> en ENFANTS DIRECTS. Or le JS cote client
  (cme-cta-progressifs.php, fonction demarrer()) construit sa liste de
  candidats avec `zone.children` -- ENFANTS DIRECTS UNIQUEMENT, jamais une
  recherche recursive. Hypothese : si les <p>/<table>/... reels sont
  imbriques a l'interieur de ces 3 <div> (plutot que d'etre eux-memes des
  enfants directs de .entry-content), AUCUN enfant direct ne correspond
  jamais a /^(P|UL|OL|TABLE|FIGURE|BLOCKQUOTE)$/ -- le mini-formulaire
  "contact" ne peut structurellement jamais s'inserer, quelle que soit la
  longueur de l'article. Le bloc "avant d'appeler" n'est, lui, pas
  concerne (zone.appendChild(...) inconditionnel) -- ce qui expliquerait
  exactement l'observation faite (appel vu, jamais contact).

- id=908 (solaire/production-solaire/) : contenu entierement vide (0
  caractere HTML) d'apres l'inspection precedente malgre status=publish --
  verification complementaire ici : titre, date de modification, extrait,
  pour ecarter une explication bete (ex. redirection, page volontairement
  vide).

LECTURE SEULE -- aucune ecriture.

USAGE :
  python3 verifier_structure_enfants_directs_2218_et_908.py
"""
import requests
from bs4 import BeautifulSoup

SITE = "https://www.comprendre-mon-energie.fr"


def inspecter_enfants_directs(post_id):
    resp = requests.get(
        f"{SITE}/wp-json/wp/v2/posts/{post_id}",
        params={"_fields": "id,link,content"},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  ❌ HTTP {resp.status_code}")
        return
    html = (resp.json().get("content") or {}).get("rendered", "")
    soup = BeautifulSoup(html, "html.parser")
    enfants = [c for c in soup.contents if getattr(c, "name", None)]
    print(f"  {len(enfants)} enfant(s) direct(s) au niveau racine du contenu rendu :")
    for idx, el in enumerate(enfants):
        classes = " ".join(el.get("class", []))
        nb_mots = len(el.get_text(separator=" ").strip().split())
        nb_p_imbriques = len(el.find_all("p"))
        nb_table_imbriquees = len(el.find_all("table"))
        print(f"    [{idx}] <{el.name} class=\"{classes}\"> | {nb_mots} mots | {nb_p_imbriques} <p> imbrique(s) | {nb_table_imbriquees} <table> imbriquee(s)")


def inspecter_metadonnees(post_id):
    resp = requests.get(
        f"{SITE}/wp-json/wp/v2/posts/{post_id}",
        params={"_fields": "id,link,title,excerpt,date,modified,status"},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  ❌ HTTP {resp.status_code}")
        return
    p = resp.json()
    titre = (p.get("title") or {}).get("rendered", "")
    extrait = (p.get("excerpt") or {}).get("rendered", "")
    print(f"  Titre      : {titre!r}")
    print(f"  Extrait    : {extrait!r}")
    print(f"  Statut     : {p.get('status')}")
    print(f"  Date pub.  : {p.get('date')}")
    print(f"  Modifie le : {p.get('modified')}")


def main():
    print("=" * 90)
    print("id=2218 (attestation-de-contrat-delectricite) -- structure en enfants directs")
    print("=" * 90)
    inspecter_enfants_directs(2218)

    print("\n" + "=" * 90)
    print("id=908 (solaire/production-solaire/) -- metadonnees completes")
    print("=" * 90)
    inspecter_metadonnees(908)


if __name__ == "__main__":
    main()
