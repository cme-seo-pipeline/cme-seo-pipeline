"""
CME — Investigation (lecture seule) des 4 cas "autre (a investiguer)"
restes en suspens depuis classer_cause_racine_17_angle_mort.py (04/11) :
id=663, 4966, 699, 5804. Chacun a une structure de plus-gros-enfant-direct
differente des deux patterns deja connus (wp-block-columns corrige le
04/11, <article> brute toujours cassee) :
  - id=663  : <div class="uagb-block... uagb-infobox...">
  - id=4966 : <ul class="">
  - id=699  : <ul class="wp-block-list">
  - id=5804 : <h4 class="">

Objectif explicite de l'operateur : confirmer l'etat REEL actuel de
chacun (pas se fier a l'audit du 04/11, qui peut etre perime) AVANT de
proposer un correctif, pour ne pas dupliquer un travail deja fait entre
le 04/11 et aujourd'hui.

Deux temps par article :
  1/ Structure brute actuelle (API REST WordPress, lecture seule) --
     recompte les enfants directs et le mot-compte, pour verifier si le
     contenu a change depuis le 04/11.
  2/ Rendu reel (Playwright, navigateur reel, simulation d'interaction
     pour contourner le "Delay JS Execution" de LiteSpeed -- meme piege
     documente le 04/11 par verifier_delai_js_litespeed.py) -- compte les
     .cme-cta60[data-pos] reellement presents dans le DOM aujourd'hui.

LECTURE SEULE -- aucune ecriture, aucun clic, aucune soumission.

USAGE :
  python3 investiguer_4_cas_isoles_cta.py
"""
import subprocess
import sys

import requests
from bs4 import BeautifulSoup

SITE = "https://www.comprendre-mon-energie.fr"
ARTICLES = [
    (663, "compteur-linky", "/electricite/compteur/compteur-linky/"),
    (4966, "installation-poele-masse", "/renovation-energetique/poele/installation-poele-masse/"),
    (699, "justificatif-de-domicile", "/electricite/facture-electricite/justificatif-de-domicile/"),
    (5804, "changement-fournisseur-electricite-procedure-0814", "/electricite/contrat-electricite/changement-fournisseur-electricite-procedure-0814/"),
]


def inspecter_structure(post_id):
    resp = requests.get(f"{SITE}/wp-json/wp/v2/posts/{post_id}", params={"_fields": "id,link,content,modified"}, timeout=30)
    if resp.status_code != 200:
        print(f"    ❌ HTTP {resp.status_code}")
        return
    data = resp.json()
    html = (data.get("content") or {}).get("rendered", "")
    print(f"    Modifie : {data.get('modified')}")
    soup = BeautifulSoup(html, "html.parser")
    enfants = [c for c in soup.contents if getattr(c, "name", None)]
    total_mots = len(soup.get_text(separator=" ").strip().split())
    print(f"    {total_mots} mots au total | {len(enfants)} enfant(s) direct(s) :")
    for idx, el in enumerate(enfants):
        classes = " ".join(el.get("class", []))
        nb_mots = len(el.get_text(separator=" ").strip().split())
        print(f"      [{idx}] <{el.name} class=\"{classes}\"> | {nb_mots} mots")


def verifier_rendu(page, post_id, nom, chemin):
    url = SITE + chemin + "?t=" + str(__import__("random").randint(100000, 999999))
    page.goto(url, wait_until="load", timeout=45000)
    # Contourne le "Delay JS Execution" de LiteSpeed (differe l'execution
    # des scripts jusqu'a une interaction reelle -- confirme le 04/11).
    page.mouse.move(200, 300)
    page.mouse.wheel(0, 800)
    page.wait_for_timeout(1000)
    page.mouse.wheel(0, 1200)
    page.wait_for_timeout(1500)

    resultat = page.evaluate("""
        () => {
            const formulaires = Array.from(document.querySelectorAll('.cme-cta60[data-pos]'));
            return formulaires.map(f => {
                const parent = f.parentElement ? f.parentElement.tagName + '.' + (f.parentElement.className || '') : null;
                return { pos: f.getAttribute('data-pos'), parent };
            });
        }
    """)
    print(f"    {len(resultat)} formulaire(s) 'cme-cta60' trouve(s) dans le DOM rendu.")
    for r in resultat:
        print(f"      pos={r['pos']} | parent={r['parent']}")
    return len(resultat)


def main():
    print("📦 Installation de playwright + chromium (one-shot, runner GitHub Actions)...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "playwright"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True)
    from playwright.sync_api import sync_playwright

    resumes = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for post_id, nom, chemin in ARTICLES:
            print("=" * 90)
            print(f"id={post_id} | {nom}")
            print("=" * 90)
            print("  1/ Structure brute actuelle (API REST) :")
            inspecter_structure(post_id)
            print("  2/ Rendu reel (Playwright + interaction simulee) :")
            try:
                nb = verifier_rendu(page, post_id, nom, chemin)
            except Exception as e:
                print(f"    ❌ Erreur Playwright : {e}")
                nb = None
            resumes.append((post_id, nom, nb))
            print()
        browser.close()

    print("=" * 90)
    print("Resume")
    print("=" * 90)
    for post_id, nom, nb in resumes:
        if nb is None:
            statut = "❌ erreur de verification"
        elif nb > 0:
            statut = f"✅ {nb} formulaire(s) deja present(s) -- deja corrige ou jamais casse"
        else:
            statut = "❌ 0 formulaire -- toujours casse, correctif a faire"
        print(f"  id={post_id} | {nom} | {statut}")


if __name__ == "__main__":
    main()
