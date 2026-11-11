"""
CME — Verification EN CONDITIONS REELLES (navigateur reel, via Playwright)
du correctif "angle mort <article> brute" deploye le 11/11/2026 sur
cme-cta-progressifs.php (commit efa3b7b), sur les 6 articles confirmes
casses par classer_cause_racine_17_angle_mort.py (04/11) :
id=3489, 3488, 3491, 3384, 3385, 3387.

Un simple curl du HTML stocke (deja fait par l'operateur) ne confirme que
le deploiement du bon FICHIER -- le <script> du mu-plugin contient de
toute facon litteralement la chaine "cme-cta60" dans son propre code JS,
qu'il fonctionne ou non. Seule l'execution reelle du JS dans un navigateur
confirme que des formulaires sont effectivement INSERES dans le DOM.

Compte les .cme-cta60[data-pos] reellement presents dans le DOM apres
chargement + simulation d'interaction (contourne le "Delay JS Execution"
de LiteSpeed, piege confirme le 04/11 par verifier_delai_js_litespeed.py).

LECTURE SEULE -- ne soumet aucun formulaire, ne clique sur rien.

USAGE :
  python3 verifier_fix_article_brute_en_conditions_reelles.py
"""
import subprocess
import sys

SITE = "https://www.comprendre-mon-energie.fr"
ARTICLES = [
    (3489, "renovation-energetique", "/renovation-energetique/renovation-globale/renovation-energetique/"),
    (3488, "entretien-chaudiere-gaz", "/gaz/chauffage-gaz/entretien-chaudiere-gaz/"),
    (3491, "installation-panneaux-solaires", "/solaire/panneaux-solaires/installation-panneaux-solaires/"),
    (3384, "aides-renovation-energetique", "/renovation-energetique/renovation-globale/aides-renovation-energetique/"),
    (3385, "aides-energetiques-guide-2", "/aide-energetique/maprimerenov/aides-energetiques-guide-2/"),
    (3387, "comparateur-electricite", "/electricite/comparatifs-fournisseurs-electricite/comparateur-electricite/"),
]


def verifier(page, post_id, nom, chemin):
    url = SITE + chemin + "?t=" + str(__import__("random").randint(100000, 999999))
    page.goto(url, wait_until="load", timeout=45000)
    page.mouse.move(200, 300)
    page.mouse.wheel(0, 800)
    page.wait_for_timeout(1000)
    page.mouse.wheel(0, 1200)
    page.wait_for_timeout(1500)

    resultat = page.evaluate("""
        () => {
            const formulaires = Array.from(document.querySelectorAll('.cme-cta60[data-pos]'));
            return formulaires.map(f => {
                const dansArticleImbrique = !!f.closest('.entry-content article');
                const parent = f.parentElement ? (f.parentElement.tagName + '.' + (f.parentElement.className || '')) : null;
                return { pos: f.getAttribute('data-pos'), dansArticleImbrique, parent };
            });
        }
    """)
    return resultat


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
            try:
                resultat = verifier(page, post_id, nom, chemin)
            except Exception as e:
                print(f"  ❌ Erreur Playwright : {e}\n")
                resumes.append((post_id, nom, None))
                continue
            if not resultat:
                print("  ❌ 0 formulaire 'cme-cta60' trouve dans le DOM.")
            else:
                print(f"  {len(resultat)} formulaire(s) 'cme-cta60' trouve(s) dans le DOM :")
                for r in resultat:
                    marque = " <-- a l'interieur de l'<article> imbrique" if r["dansArticleImbrique"] else ""
                    print(f"    pos={r['pos']} | parent={r['parent']}{marque}")
            resumes.append((post_id, nom, len(resultat)))
            print()
        browser.close()

    print("=" * 90)
    print("Resume")
    print("=" * 90)
    for post_id, nom, nb in resumes:
        if nb is None:
            statut = "❌ erreur de verification"
        elif nb > 0:
            statut = f"✅ {nb} formulaire(s) -- correctif confirme fonctionnel"
        else:
            statut = "❌ 0 formulaire -- toujours casse"
        print(f"  id={post_id} | {nom} | {statut}")


if __name__ == "__main__":
    main()
