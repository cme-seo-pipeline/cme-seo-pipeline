"""
CME — Audit (lecture seule) de l'angle mort "bloc Colonnes" decouvert le
04/11/2026 sur l'article attestation-de-contrat-delectricite (id=2218) :
le JS cote client (cme-cta-progressifs.php, fonction demarrer()) ne
regarde que les ENFANTS DIRECTS de .entry-content (zone.children) pour
inserer le mini-formulaire "contact" -- jamais une recherche recursive.
Un article dont le corps est enveloppe dans un bloc Gutenberg "Colonnes"
(<div class="wp-block-columns">) a donc tous ses <p>/<table>/... reels
NON eligibles (ils ne sont plus des enfants directs), quelle que soit la
longueur totale de l'article.

Ce script REJOUE EXACTEMENT l'algorithme JS (meme fonctions mots/estCta/
estVide/prochainSeuilContact, memes constantes MAX_FORMULAIRES_CONTACT=7/
MOTS_FIN_MIN=120/MOTS_MIN_CTA_APPEL=300, meme boucle sur les enfants
directs) en Python, pour chaque article publie, afin de compter
PRECISEMENT combien de formulaires "contact" seraient reellement
inseres -- par opposition a l'audit du 04/11 (auditer_articles_sans_cta_
inline.py) qui n'approximait que par le nombre de mots total, sans
rejouer la structure.

Classement :
  - "Angle mort total" : poses_reelles == 0 alors que l'article a assez
    de mots au total pour en avoir eu au moins 1 (>= 420, meme seuil
    approx. que le 04/11) -- le cas type attestation-de-contrat.
  - "Deficit partiel" : poses_reelles < poses_attendues_par_les_mots
    (le compte simple par seuils de mots, sans tenir compte de la
    structure) -- l'article recoit MOINS de formulaires qu'il ne
    devrait, sans en etre totalement prive.

LECTURE SEULE -- aucune ecriture. Lit l'API REST WordPress publique.

USAGE :
  python3 auditer_angle_mort_colonnes_cta.py [--detail]
"""
import sys

import requests
from bs4 import BeautifulSoup, Tag

SITE = "https://www.comprendre-mon-energie.fr"

MAX_FORMULAIRES_CONTACT = 7
MOTS_FIN_MIN = 120
MOTS_MIN_CTA_APPEL = 300
SEUIL_ANGLE_MORT_TOTAL = 420   # 300 + 120, meme approx. que le 04/11
TAGS_ELIGIBLES = {"p", "ul", "ol", "table", "figure", "blockquote"}


def mots(el):
    if isinstance(el, Tag):
        texte = el.get_text(separator=" ").strip()
    else:
        texte = str(el).strip()
    return len(texte.split()) if texte else 0


def est_cta(el):
    if not isinstance(el, Tag) or el.name != "div":
        return False
    style = el.get("style", "")
    if isinstance(style, list):
        style = " ".join(style)
    return "linear-gradient" in (style or "")


def est_vide(el):
    if not isinstance(el, Tag) or el.name != "div":
        return False
    a_des_enfants_tag = any(isinstance(c, Tag) for c in el.children)
    texte = el.get_text().strip()
    return (not a_des_enfants_tag) and (not texte)


def prochain_seuil_contact(poses):
    if poses < 5:
        return 300 + poses * 200
    return 1100 + (poses - 4) * 400


def poses_attendues_par_mots(total_mots):
    """Nombre de formulaires 'contact' qu'on obtiendrait si on ignorait
    la structure et qu'on comptait juste les seuils de mots franchis."""
    n = 0
    while n < MAX_FORMULAIRES_CONTACT and total_mots >= prochain_seuil_contact(n):
        n += 1
    return n


def simuler(html):
    soup = BeautifulSoup(html or "", "html.parser")
    enfants = [c for c in soup.contents if isinstance(c, Tag)]
    n = len(enfants)

    apres = [0] * n
    acc = 0
    for i in range(n - 1, -1, -1):
        apres[i] = acc
        if est_cta(enfants[i]):
            acc = 0
        else:
            acc += mots(enfants[i])

    total_mots_vus = 0
    poses = 0
    for i in range(n):
        el = enfants[i]
        if est_cta(el):
            continue
        total_mots_vus += mots(el)
        if poses >= MAX_FORMULAIRES_CONTACT:
            break
        if total_mots_vus < prochain_seuil_contact(poses):
            continue
        if el.name not in TAGS_ELIGIBLES:
            continue
        suivant = enfants[i + 1] if i + 1 < n else None
        if suivant is None or est_cta(suivant) or est_vide(suivant):
            continue
        if apres[i] < MOTS_FIN_MIN:
            continue
        poses += 1

    total_mots_reel = sum(mots(e) for e in enfants if not est_cta(e))
    return poses, total_mots_reel


def recuperer_tous_les_articles():
    articles = []
    page = 1
    while True:
        try:
            resp = requests.get(
                f"{SITE}/wp-json/wp/v2/posts",
                params={"per_page": 100, "page": page, "status": "publish", "_fields": "id,link,content"},
                timeout=30,
            )
        except requests.RequestException as e:
            sys.exit(f"❌ Erreur reseau page {page} : {e}")
        if resp.status_code == 400:
            break
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

    angle_mort_total = []
    deficit_partiel = []

    for a in articles:
        html = (a.get("content") or {}).get("rendered", "")
        poses_reelles, total_mots = simuler(html)
        attendues = poses_attendues_par_mots(total_mots)

        if poses_reelles == 0 and total_mots >= SEUIL_ANGLE_MORT_TOTAL:
            angle_mort_total.append((a["id"], a.get("link", ""), total_mots, attendues))
        elif poses_reelles < attendues:
            deficit_partiel.append((a["id"], a.get("link", ""), total_mots, poses_reelles, attendues))

    print("=" * 90)
    print(f"1/ ANGLE MORT TOTAL (0 formulaire 'contact' pose malgre >= {SEUIL_ANGLE_MORT_TOTAL} mots) : {len(angle_mort_total)} article(s)")
    print("=" * 90)
    if not angle_mort_total:
        print("  (aucun)")
    else:
        for pid, lien, total_mots, attendues in angle_mort_total:
            print(f"  id={pid} | {total_mots} mots | {attendues} formulaire(s) attendu(s), 0 pose | {lien}")

    print("\n" + "=" * 90)
    print(f"2/ DEFICIT PARTIEL (moins de formulaires 'contact' que ce que les seuils de mots suggereraient) : {len(deficit_partiel)} article(s)")
    print("=" * 90)
    if not deficit_partiel:
        print("  (aucun)")
    elif detail:
        for pid, lien, total_mots, poses_reelles, attendues in deficit_partiel:
            print(f"  id={pid} | {total_mots} mots | {poses_reelles} pose(s) / {attendues} attendu(s) | {lien}")
    else:
        print("  (lancer avec --detail pour la liste complete)")

    print("\n" + "=" * 90)
    print("Resume")
    print("=" * 90)
    print(f"  Total articles publies : {len(articles)}")
    print(f"  Angle mort total        : {len(angle_mort_total)}")
    print(f"  Deficit partiel         : {len(deficit_partiel)}")


if __name__ == "__main__":
    main()
