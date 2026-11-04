"""
CME — Audit (lecture seule) des articles publies qui, en l'etat actuel du
contenu, n'auraient AUCUNE occurrence du mini-formulaire inline "contact"
et/ou du bloc "avant d'appeler" (wordpress-mu-plugins/cme-cta-progressifs.php),
malgre le fait que ce mecanisme s'applique automatiquement a tous les
articles publies (is_singular('post'), cote client -- pas de marqueur en
base, donc il faut rejouer les memes conditions que le JS pour savoir
lesquels en seraient prives).

Deux causes possibles, reprises EXACTEMENT du JS actuel (cme-cta-progressifs.php) :

1. Prefixe d'URL non reconnu (PAR_PREFIXE) -- aucun formulaire du tout,
   ni contact ni appel, quelle que soit la longueur de l'article. Prefixes
   reconnus actuellement : gaz, electricite, aide-energetique,
   renovation-energetique, solaire.
2. Article trop court :
   - Bloc "avant d'appeler" : necessite totalMots >= MOTS_MIN_CTA_APPEL (300).
   - 1er formulaire "contact" : necessite d'atteindre le seuil de 300 mots
     a un bloc eligible (P/UL/OL/TABLE/FIGURE/BLOCKQUOTE) avec au moins
     MOTS_FIN_MIN (120) mots APRES ce bloc avant la fin de l'article --
     approxime ici par un total >= 420 mots (300 + 120), une approximation
     du cote structurel du JS (qui depend aussi de la position exacte des
     balises de bloc, non rejouee ici a l'identique).

Comptage de mots approxime par le texte visible (BeautifulSoup .get_text(),
split sur les espaces) -- la meme logique que mots() en JS (textContent.
split(/\s+/)), a la tokenisation pres.

LECTURE SEULE -- aucune ecriture. Lit l'API REST WordPress publique
(content.rendered, pas besoin d'authentification), par lots de 100.

USAGE :
  python3 auditer_articles_sans_cta_inline.py [--detail]
"""
import sys
import re

import requests
from bs4 import BeautifulSoup

SITE = "https://www.comprendre-mon-energie.fr"
PREFIXES_RECONNUS = {"gaz", "electricite", "aide-energetique", "renovation-energetique", "solaire"}
MOTS_MIN_CTA_APPEL = 300
SEUIL_APPROX_1ER_CONTACT = 420   # 300 (1er seuil) + 120 (MOTS_FIN_MIN), approx structurelle


def compter_mots(html):
    texte = BeautifulSoup(html or "", "html.parser").get_text(separator=" ").strip()
    return len(texte.split()) if texte else 0


def prefixe_de(lien):
    chemin = lien.replace(SITE, "").strip("/")
    return chemin.split("/")[0] if chemin else ""


def recuperer_tous_les_articles():
    articles = []
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{SITE}/wp-json/wp/v2/posts",
                params={"per_page": 100, "page": page, "status": "publish", "_fields": "id,link,slug,content"},
                timeout=30,
            )
        except requests.RequestException as e:
            sys.exit(f"❌ Erreur reseau page {page} : {e}")
        if resp.status_code == 400:
            break   # page au-dela du total -- fin de pagination WP
        if resp.status_code != 200:
            sys.exit(f"❌ HTTP {resp.status_code} page {page} : {resp.text[:200]}")
        lot = resp.json()
        if not lot:
            break
        articles.extend(lot)
        if len(lot) < 100:
            break
        page += 1
    return articles


def main():
    detail = "--detail" in sys.argv[1:]

    print("📥 Recuperation de tous les articles publies (API REST WordPress)...")
    articles = recuperer_tous_les_articles()
    print(f"   {len(articles)} article(s) recupere(s).\n")

    sans_prefixe_reconnu = []
    trop_court_appel = []
    trop_court_contact = []

    for a in articles:
        lien = a.get("link", "")
        prefixe = prefixe_de(lien)
        nb_mots = compter_mots((a.get("content") or {}).get("rendered", ""))

        if prefixe not in PREFIXES_RECONNUS:
            sans_prefixe_reconnu.append((a["id"], a.get("slug", ""), lien, prefixe, nb_mots))
            continue   # zero formulaire du tout -- pas la peine de tester la longueur

        if nb_mots < MOTS_MIN_CTA_APPEL:
            trop_court_appel.append((a["id"], a.get("slug", ""), lien, prefixe, nb_mots))
        if nb_mots < SEUIL_APPROX_1ER_CONTACT:
            trop_court_contact.append((a["id"], a.get("slug", ""), lien, prefixe, nb_mots))

    print("=" * 90)
    print(f"1/ Prefixe d'URL non reconnu -- AUCUN formulaire (ni contact ni appel) : {len(sans_prefixe_reconnu)} article(s)")
    print("=" * 90)
    if not sans_prefixe_reconnu:
        print("  (aucun)")
    else:
        prefixes_vus = sorted(set(p for _, _, _, p, _ in sans_prefixe_reconnu))
        print(f"  Prefixes en cause : {prefixes_vus}")
        if detail:
            for pid, slug, lien, prefixe, nb_mots in sans_prefixe_reconnu:
                print(f"  id={pid} | prefixe='{prefixe}' | {nb_mots} mots | {lien}")

    print("\n" + "=" * 90)
    print(f"2/ Trop court pour le bloc 'avant d'appeler' (< {MOTS_MIN_CTA_APPEL} mots) : {len(trop_court_appel)} article(s)")
    print("=" * 90)
    if not trop_court_appel:
        print("  (aucun)")
    elif detail:
        for pid, slug, lien, prefixe, nb_mots in trop_court_appel:
            print(f"  id={pid} | {prefixe} | {nb_mots} mots | {lien}")
    else:
        print("  (lancer avec --detail pour la liste complete)")

    print("\n" + "=" * 90)
    print(f"3/ Trop court pour obtenir au moins 1 formulaire 'contact' (< ~{SEUIL_APPROX_1ER_CONTACT} mots, approx.) : {len(trop_court_contact)} article(s)")
    print("=" * 90)
    if not trop_court_contact:
        print("  (aucun)")
    elif detail:
        for pid, slug, lien, prefixe, nb_mots in trop_court_contact:
            print(f"  id={pid} | {prefixe} | {nb_mots} mots | {lien}")
    else:
        print("  (lancer avec --detail pour la liste complete)")

    print("\n" + "=" * 90)
    print("Resume")
    print("=" * 90)
    print(f"  Total articles publies           : {len(articles)}")
    print(f"  Zero formulaire (prefixe inconnu) : {len(sans_prefixe_reconnu)}")
    print(f"  Zero bloc 'avant d'appeler'        : {len(trop_court_appel)}")
    print(f"  Zero 1er formulaire 'contact'      : {len(trop_court_contact)}")


if __name__ == "__main__":
    main()
