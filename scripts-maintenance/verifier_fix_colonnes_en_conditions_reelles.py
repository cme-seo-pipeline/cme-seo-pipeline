"""
CME — Verification EN CONDITIONS REELLES (navigateur reel, via Playwright)
du correctif "angle mort bloc Colonnes" deploye le 04/11/2026 sur
cme-cta-progressifs.php.

Contrairement aux audits precedents (lecture seule du contenu brut via
l'API REST, sans executer le JS), ce script charge reellement chaque page
dans un Chromium headless -- c'est le SEUL moyen de confirmer que le
mini-formulaire "contact" (insere dynamiquement cote client) apparait
desormais bien dans le DOM, y compris a l'interieur d'un bloc Colonnes.

Articles verifies :
  - id=2218 (attestation-de-contrat-delectricite) : la decouverte initiale
    (angle mort total, 4461 mots, 0 formulaire avant le correctif).
  - id=3489 (renovation-energetique) : autre "angle mort total" de
    l'audit exhaustif.
  - id=3387 (comparateur-electricite) : plus gros "deficit partiel"
    (1 formulaire pose / 7 attendus avant le correctif).

Pour chaque page : compte les elements .cme-cta60[data-pos] reellement
presents dans le DOM apres chargement, et verifie si au moins un est
imbrique a l'interieur d'un wp-block-column (preuve directe que le
correctif fonctionne a l'interieur du bloc Colonnes, pas seulement en
dehors).

LECTURE SEULE -- ne soumet aucun formulaire, ne clique sur rien.

USAGE :
  python3 verifier_fix_colonnes_en_conditions_reelles.py
"""
import subprocess
import sys

print("📦 Installation de playwright + chromium (one-shot, runner GitHub Actions)...")
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "playwright"], check=True)
subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True)

from playwright.sync_api import sync_playwright  # noqa: E402

SITE = "https://www.comprendre-mon-energie.fr"
ARTICLES = [
    (2218, "attestation-de-contrat-delectricite", "/electricite/contrat-electricite/attestation-de-contrat-delectricite/"),
    (3489, "renovation-energetique", "/renovation-energetique/renovation-globale/renovation-energetique/"),
    (3387, "comparateur-electricite", "/electricite/comparatifs-fournisseurs-electricite/comparateur-electricite/"),
]


def verifier(page, post_id, nom, chemin):
    url = SITE + chemin + "?t=" + str(__import__("random").randint(100000, 999999))
    print("=" * 90)
    print(f"id={post_id} | {nom}")
    print(f"  {url}")
    print("=" * 90)

    page.goto(url, wait_until="load", timeout=45000)
    # LiteSpeed Cache ("Delay JS Execution") differe l'execution des scripts
    # jusqu'a la premiere interaction reelle -- une attente passive ne suffit
    # pas (confirme le 04/11 par verifier_delai_js_litespeed.py). On simule
    # une interaction minimale avant de lire le DOM.
    page.mouse.move(200, 300)
    page.mouse.wheel(0, 800)
    page.wait_for_timeout(1000)
    page.mouse.wheel(0, 1200)
    page.wait_for_timeout(1500)

    resultat = page.evaluate("""
        () => {
            const formulaires = Array.from(document.querySelectorAll('.cme-cta60[data-pos]'));
            return formulaires.map(f => {
                const dansColonne = !!f.closest('.wp-block-column');
                const parent = f.parentElement ? f.parentElement.className : null;
                return { pos: f.getAttribute('data-pos'), dansColonne, parent };
            });
        }
    """)

    if not resultat:
        print("  ❌ AUCUN formulaire .cme-cta60 trouve dans le DOM -- le correctif ne semble pas actif sur cette page.")
        return False

    print(f"  {len(resultat)} formulaire(s) 'cme-cta60' trouve(s) dans le DOM :")
    nb_dans_colonne = 0
    for r in resultat:
        marque = " <-- DANS un wp-block-column" if r["dansColonne"] else ""
        print(f"    pos={r['pos']} | parent class=\"{r['parent']}\"{marque}")
        if r["dansColonne"]:
            nb_dans_colonne += 1

    print(f"\n  Formulaires imbriques dans un wp-block-column : {nb_dans_colonne}/{len(resultat)}")
    if nb_dans_colonne > 0:
        print("  ✅ Le correctif fonctionne : au moins un formulaire 'contact' est bien insere a l'interieur du bloc Colonnes.")
    else:
        print("  ⚠️ Aucun formulaire trouve a l'interieur d'un wp-block-column -- a investiguer si cet article etait cense en avoir un.")
    print()
    return nb_dans_colonne > 0


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        resultats = []
        for post_id, nom, chemin in ARTICLES:
            try:
                ok = verifier(page, post_id, nom, chemin)
                resultats.append((post_id, nom, ok))
            except Exception as e:
                print(f"  ❌ Erreur sur id={post_id} ({nom}) : {e}\n")
                resultats.append((post_id, nom, False))
        browser.close()

    print("=" * 90)
    print("Resume")
    print("=" * 90)
    for post_id, nom, ok in resultats:
        print(f"  id={post_id} | {nom} | {'✅ OK' if ok else '❌ A verifier'}")


if __name__ == "__main__":
    main()
