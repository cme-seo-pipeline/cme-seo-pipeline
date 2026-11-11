"""
CME — Re-verification EN CONDITIONS REELLES des 48 articles "deficit
partiel" (auditer_angle_mort_colonnes_cta.py, 04/11/2026 : poses_reelles
< poses_attendues_par_mots, estimation NAIVE qui ignore completement la
structure et les garde-fous volontaires de l'algorithme).

Cette liste de 48 est aujourd'hui PERIMEE pour deux raisons, expliquees a
l'operateur avant de lancer ce script :
  1/ Elle rejoue l'algorithme JS tel qu'il etait AVANT les deux
     correctifs structurels deja deployes depuis (bloc Colonnes le
     04/11, <article> brute le 11/11) -- une partie des 48 est donc
     probablement deja resolue, comme confirme ce matin pour les 4 cas
     "autre" (663/4966/699/5804).
  2/ L'estimation "attendus par les mots" ignore 3 garde-fous VOLONTAIRES
     du vrai algorithme (MOTS_FIN_MIN=120, eligibilite de balise P/UL/OL/
     TABLE/FIGURE/BLOCKQUOTE, plafond a 7) -- elle surestime donc
     systematiquement ce qu'un article "correct" devrait avoir.

Pour chaque article, ce script calcule DEUX choses distinctes, pas une
seule comparaison naive :
  A/ "attendu realiste" : rejoue l'algorithme COMPLET et A JOUR (avec le
     depliage recursif des blocs Colonnes/<article>, memes seuils/
     garde-fous que le vrai cme-cta-progressifs.php aujourd'hui) sur le
     contenu brut stocke -- c'est ce qu'un article qui fonctionne
     correctement DOIT produire, pas une estimation naive.
  B/ "reel en live" : charge la page dans un vrai navigateur (apres
     simulation d'interaction, contourne le Delay JS Execution de
     LiteSpeed) et compte les .cme-cta60[data-pos] effectivement
     presents dans le DOM aujourd'hui.

Classement final par article :
  - reel >= attendu realiste -> OK, pas de bug (le "deficit" du 04/11
    etait un artefact de l'estimation naive, pas un vrai probleme).
  - reel < attendu realiste -> DEFICIT REEL CONFIRME, a investiguer
    individuellement (seul ce sous-ensemble merite une action).

LECTURE SEULE -- aucune ecriture, aucun clic, aucune soumission.

USAGE :
  python3 reverifier_deficit_partiel_48.py
"""
import subprocess
import sys

import requests
from bs4 import BeautifulSoup, Tag

SITE = "https://www.comprendre-mon-energie.fr"

MAX_FORMULAIRES_CONTACT = 7
MOTS_FIN_MIN = 120
TAGS_ELIGIBLES = {"p", "ul", "ol", "table", "figure", "blockquote"}

# Les 48 articles "deficit partiel" de l'audit du 04/11 (id, chemin).
ARTICLES = [
    (13177, "/gaz/bouteilles/propane-vs-butane-lequel-choisir/"),
    (12390, "/aide-energetique/cheque-energie/cheque-energie-montant-2026-conditions-eligibilite/"),
    (11248, "/aide-energetique/cheque-energie/cheque-energie-2025-eligibilite-obtention/"),
    (11240, "/gaz/bouteilles/bouteille-gaz-13kg-vs-5kg-comparatif/"),
    (9798, "/aide-energetique/cheque-energie/comment-utiliser-cheque-energie-1015/"),
    (9764, "/gaz/facture-gaz/facture-gaz-octobre-2026/"),
    (9677, "/aide-energetique/maprimerenov/maprimerenov-montants-conditions-eligibilite-2025/"),
    (9454, "/aide-energetique/cheque-energie/cheque-energie-validite-delai-expiration/"),
    (8816, "/aide-energetique/cheque-energie/cheque-energie-montant-calcul/"),
    (8375, "/electricite/heures-pleines-creuses/heures-creuses-fonctionnement-tarification/"),
    (8357, "/gaz/bouteilles/bouteille-gaz-propane-vs-butane-comparatif/"),
    (8340, "/gaz/facture-gaz/facture-gaz-septembre-2026/"),
    (7984, "/renovation-energetique/audit-energetique/audit-energetique-obligatoire/"),
    (7488, "/electricite/facture-electricite/fournisseur-electricite-moins-cher-comparatif/"),
    (7476, "/aide-energetique/eco-pret-a-taux-zero/eco-ptz-fonctionnement-pret-ecologique/"),
    (7270, "/aide-energetique/eco-pret-a-taux-zero/eco-ptz-vs-maprimerenov-quel-financement-choisir/"),
    (7069, "/electricite/comparatifs-fournisseurs-electricite/meilleur-fournisseur-electricite-comparatif-2026-0827/"),
    (7067, "/electricite/comparatifs-fournisseurs-electricite/comparateur-fournisseurs-electricite-tarifs-2026/"),
    (7059, "/gaz/demenagement-gaz/delai-mise-en-service-gaz-demenagement-0827/"),
    (7037, "/electricite/facture-electricite/facture-electricite-aout-2026-0827-9/"),
    (7035, "/electricite/facture-electricite/facture-electricite-aout-2026-0827-8/"),
    (7033, "/electricite/facture-electricite/facture-electricite-aout-2026-0827-7/"),
    (7031, "/electricite/facture-electricite/facture-electricite-aout-2026-0827-6/"),
    (7029, "/electricite/facture-electricite/facture-electricite-aout-2026-0827-5/"),
    (7027, "/electricite/facture-electricite/facture-electricite-aout-2026-0827-4/"),
    (7025, "/electricite/facture-electricite/facture-electricite-aout-2026-0827-3/"),
    (7023, "/electricite/facture-electricite/facture-electricite-aout-2026-0827-2/"),
    (7021, "/electricite/facture-electricite/facture-electricite-aout-2026-0827/"),
    (7019, "/electricite/facture-electricite/facture-electricite-aout-2026/"),
    (6675, "/electricite/heures-pleines-creuses/heures-pleines-creuses-fonctionnement-0822/"),
    (6671, "/aide-energetique/cheque-energie/comment-utiliser-cheque-energie-fournisseurs/"),
    (6615, "/electricite/demenagement/changer-fournisseur-electricite-demenagement-0821-2/"),
    (6547, "/electricite/comparatifs-fournisseurs-electricite/comparer-offres-electricite-verte/"),
    (6533, "/gaz/chauffage-gaz/fonctionnement-chaudiere-gaz-0820/"),
    (6266, "/gaz/chauffage-gaz/chauffage-gaz-aout-2026/"),
    (6263, "/gaz/chauffage-gaz/chauffage-gaz-august-2026/"),
    (5945, "/electricite/facture-electricite/tarif-reglemente-electricite-2026/"),
    (5804, "/electricite/contrat-electricite/changement-fournisseur-electricite-procedure-0814/"),
    (5633, "/aide-energetique/eco-pret-a-taux-zero/travaux-eligibles-eco-ptz-2025/"),
    (4966, "/renovation-energetique/poele/installation-poele-masse/"),
    (4745, "/electricite/comparatifs-fournisseurs-electricite/meilleur-fournisseur-electricite-2026-comparatif-tarifs/"),
    (4364, "/electricite/facture-electricite/consommation-electrique-mesure-optimisation-0713/"),
    (3661, "/gaz/bouteilles/fonctionnement-bouteilles-gaz/"),
    (3387, "/electricite/comparatifs-fournisseurs-electricite/comparateur-electricite/"),
    (840, "/solaire/panneaux-solaires/installation-panneaux-photovoltaiques/"),
    (709, "/electricite/compteur/coupure-electricite/"),
    (699, "/electricite/facture-electricite/justificatif-de-domicile/"),
    (563, "/electricite/comparatifs-fournisseurs-electricite/changer-fournisseur-electricite/"),
]

# Deja individuellement investigues avant ce script -- gardes ici juste
# pour l'annoter dans le resume, pas pour les exclure (on re-verifie
# TOUT, par souci de rigueur, meme ce qui est deja cense etre regle).
DEJA_INVESTIGUES = {
    4966: "verifie en live ce matin (deja bon)",
    3387: "corrige aujourd'hui (<article> brute)",
    699: "verifie en live ce matin (deja bon)",
    5804: "verifie en live ce matin (deja bon)",
    563: "corrige le 04/11 (bloc Colonnes)",
    709: "deja explique : 362 mots, sous le seuil, comportement attendu",
}


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


def est_conteneur_layout(el):
    # Replique exactement estConteneurLayout() apres les 2 correctifs
    # (04/11 Colonnes + 11/11 <article>).
    if not isinstance(el, Tag):
        return False
    if el.name == "article":
        return True
    if el.name != "div":
        return False
    classes = el.get("class", [])
    return "wp-block-columns" in classes or "wp-block-column" in classes


def enfants_effectifs(racine):
    resultat = []

    def deplier(liste):
        for el in liste:
            if est_conteneur_layout(el):
                deplier([c for c in el.children if isinstance(c, Tag)])
            else:
                resultat.append(el)

    deplier([c for c in racine.contents if isinstance(c, Tag)])
    return resultat


def prochain_seuil_contact(poses):
    if poses < 5:
        return 300 + poses * 200
    return 1100 + (poses - 4) * 400


def simuler_attendu_realiste(html):
    """Rejoue l'algorithme COMPLET et A JOUR (avec depliage recursif) --
    c'est ce qu'un article qui fonctionne correctement doit produire."""
    soup = BeautifulSoup(html or "", "html.parser")
    enfants = enfants_effectifs(soup)
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

    return poses


def recuperer_attendu(post_id):
    resp = requests.get(f"{SITE}/wp-json/wp/v2/posts/{post_id}", params={"_fields": "id,content"}, timeout=30)
    if resp.status_code != 200:
        return None
    html = (resp.json().get("content") or {}).get("rendered", "")
    return simuler_attendu_realiste(html)


def verifier_rendu(page, chemin):
    url = SITE + chemin + "?t=" + str(__import__("random").randint(100000, 999999))
    page.goto(url, wait_until="load", timeout=45000)
    page.mouse.move(200, 300)
    page.mouse.wheel(0, 800)
    page.wait_for_timeout(1000)
    page.mouse.wheel(0, 1200)
    page.wait_for_timeout(1500)
    return page.evaluate("document.querySelectorAll('.cme-cta60[data-pos]').length")


def main():
    print("📦 Installation de playwright + chromium (one-shot, runner GitHub Actions)...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "playwright"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    from playwright.sync_api import sync_playwright

    resultats = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for post_id, chemin in ARTICLES:
            attendu = recuperer_attendu(post_id)
            try:
                reel = verifier_rendu(page, chemin)
            except Exception as e:
                print(f"id={post_id} : ❌ erreur Playwright : {e}")
                resultats.append((post_id, chemin, attendu, None))
                continue
            resultats.append((post_id, chemin, attendu, reel))
        browser.close()

    print("=" * 100)
    print(f"{'id':>7} | {'attendu realiste':>17} | {'reel en live':>12} | statut")
    print("=" * 100)
    n_ok = 0
    n_deficit = 0
    deficits = []
    for post_id, chemin, attendu, reel in resultats:
        note = f" [{DEJA_INVESTIGUES[post_id]}]" if post_id in DEJA_INVESTIGUES else ""
        if attendu is None or reel is None:
            statut = "❌ erreur"
        elif reel >= attendu:
            statut = "✅ OK"
            n_ok += 1
        else:
            statut = f"⚠️ DEFICIT REEL ({reel}/{attendu})"
            n_deficit += 1
            deficits.append((post_id, chemin, attendu, reel))
        print(f"{post_id:>7} | {str(attendu):>17} | {str(reel):>12} | {statut}{note}")

    print("=" * 100)
    print("Resume")
    print("=" * 100)
    print(f"  Total verifie       : {len(resultats)}")
    print(f"  OK (pas de bug)     : {n_ok}")
    print(f"  Deficit reel confirme : {n_deficit}")
    if deficits:
        print("\n  Articles en deficit reel confirme (a investiguer individuellement) :")
        for post_id, chemin, attendu, reel in deficits:
            print(f"    id={post_id} | {reel}/{attendu} | {SITE}{chemin}")


if __name__ == "__main__":
    main()
