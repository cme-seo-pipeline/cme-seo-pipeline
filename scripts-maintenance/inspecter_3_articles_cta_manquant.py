"""
CME — Inspection (lecture seule) de 3 articles signales comme n'ayant pas
(ou pas tous) les mini-formulaires inline (contact/avant d'appeler) :
- id=908 (solaire/production-solaire/) : 0 mot detecte par l'audit du 04/11
  (auditer_articles_sans_cta_inline.py) -- a comprendre pourquoi.
- id=709 (electricite/compteur/coupure-electricite/) : 362 mots, sous le
  seuil approx. de ~420 mots pour le 1er formulaire "contact".
- electricite/contrat-electricite/attestation-de-contrat-delectricite/
  (signale par l'operateur le 04/11, id a determiner par slug).

Affiche pour chacun : nombre de mots reel (texte visible), un extrait du
debut et de la fin du contenu rendu, et le statut WordPress (pour ecarter
une cause bete type page vide/brouillon mal publie).

LECTURE SEULE -- aucune ecriture. Lit l'API REST WordPress publique.

USAGE :
  python3 inspecter_3_articles_cta_manquant.py
"""
import sys

import requests
from bs4 import BeautifulSoup

SITE = "https://www.comprendre-mon-energie.fr"


def get_post_by_id(post_id):
    resp = requests.get(f"{SITE}/wp-json/wp/v2/posts/{post_id}", params={"_fields": "id,link,slug,status,content"}, timeout=30)
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code} : {resp.text[:200]}"
    return resp.json(), None


def get_post_by_slug(slug):
    resp = requests.get(f"{SITE}/wp-json/wp/v2/posts", params={"slug": slug, "_fields": "id,link,slug,status,content"}, timeout=30)
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code} : {resp.text[:200]}"
    lot = resp.json()
    if not lot:
        return None, "aucun post trouve pour ce slug (status=publish seulement, cote API publique)"
    return lot[0], None


def inspecter(label, post, erreur):
    print("=" * 90)
    print(label)
    print("=" * 90)
    if erreur:
        print(f"  ❌ {erreur}")
        return
    html = (post.get("content") or {}).get("rendered", "")
    soup = BeautifulSoup(html or "", "html.parser")
    texte = soup.get_text(separator=" ").strip()
    mots = texte.split() if texte else []
    print(f"  id={post['id']} | status={post.get('status')} | {post.get('link')}")
    print(f"  Longueur HTML brute  : {len(html)} caracteres")
    print(f"  Mots visibles (texte): {len(mots)}")
    if mots:
        print(f"  Debut : {' '.join(mots[:40])}...")
        print(f"  Fin   : ...{' '.join(mots[-40:])}")
    else:
        print("  ⚠️ Aucun texte visible extrait -- contenu probablement compose uniquement de blocs")
        print("     non textuels (shortcode, embed, galerie d'images, iframe...). Extrait HTML brut :")
        print(f"     {html[:500]!r}")
    print()


def main():
    p908, e908 = get_post_by_id(908)
    inspecter("1/ id=908 (solaire/production-solaire/)", p908, e908)

    p709, e709 = get_post_by_id(709)
    inspecter("2/ id=709 (electricite/compteur/coupure-electricite/)", p709, e709)

    pAtt, eAtt = get_post_by_slug("attestation-de-contrat-delectricite")
    inspecter("3/ attestation-de-contrat-delectricite (signale par l'operateur)", pAtt, eAtt)


if __name__ == "__main__":
    main()
