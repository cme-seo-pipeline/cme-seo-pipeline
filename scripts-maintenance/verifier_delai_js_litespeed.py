"""
CME — Verification de l'hypothese "delai d'execution JS LiteSpeed" :
le diagnostic precedent (diagnostiquer_absence_cme_cta60.py) a trouve
toutes les gardes de demarrer() au vert (body.single-post, article,
.entry-content, prefixe reconnu) mais `data-cta60` jamais pose sur la
zone et CME_POST_ID jamais defini -- signe que le <script> inline
#cme-cta-progressifs n'a tout simplement JAMAIS ETE EXECUTE pendant
l'attente passive (2s sans interaction). Un message console
"[LiteSpeed] Start Lazy Load" etait present -- LiteSpeed Cache propose
une option "Delay JS Execution" qui differe l'execution des scripts
(inline et externes) jusqu'a la premiere interaction reelle de
l'utilisateur (clic, scroll, mousemove) ou un timeout. Playwright, en
attente passive, ne genere aucune de ces interactions -- ce qui
expliquerait un faux-negatif total, pas une regression du code.

Ce script simule une interaction reelle (scroll + mousemove) puis
reverifie si demarrer() s'est execute (CME_POST_ID defini, data-cta60
pose sur .entry-content, et cette fois des elements .cme-cta60
presents).

LECTURE SEULE.

USAGE :
  python3 verifier_delai_js_litespeed.py
"""
import random
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "playwright"], check=True)
subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True)

from playwright.sync_api import sync_playwright  # noqa: E402

URL = "https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/attestation-de-contrat-delectricite/"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        url = URL + "?t=" + str(random.randint(100000, 999999))
        print(f"Chargement de {url} ...")
        page.goto(url, wait_until="load", timeout=45000)

        print("Avant interaction :")
        avant = page.evaluate("() => ({ CME_POST_ID: window.CME_POST_ID, dataCta60: document.querySelector('.entry-content') ? document.querySelector('.entry-content').getAttribute('data-cta60') : null, nbFormulaires: document.querySelectorAll('.cme-cta60').length })")
        print(f"  {avant}")

        print("\nSimulation d'une interaction reelle (mousemove + scroll + clic neutre)...")
        page.mouse.move(200, 300)
        page.mouse.move(250, 400)
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(1000)
        page.mouse.wheel(0, 1200)
        page.wait_for_timeout(2000)

        print("\nApres interaction :")
        apres = page.evaluate("""
            () => {
                const formulaires = Array.from(document.querySelectorAll('.cme-cta60[data-pos]'));
                return {
                    CME_POST_ID: window.CME_POST_ID,
                    dataCta60: document.querySelector('.entry-content') ? document.querySelector('.entry-content').getAttribute('data-cta60') : null,
                    nbFormulaires: formulaires.length,
                    formulaires: formulaires.map(f => ({ pos: f.getAttribute('data-pos'), dansColonne: !!f.closest('.wp-block-column') }))
                };
            }
        """)
        print(f"  CME_POST_ID = {apres['CME_POST_ID']}")
        print(f"  data-cta60 sur .entry-content = {apres['dataCta60']}")
        print(f"  Nombre de formulaires .cme-cta60 = {apres['nbFormulaires']}")
        for f in apres["formulaires"]:
            print(f"    pos={f['pos']} | dans un wp-block-column : {f['dansColonne']}")

        if apres["nbFormulaires"] > 0:
            print("\n✅ Confirme : le script s'execute bien, simplement differe jusqu'a la premiere interaction (LiteSpeed 'Delay JS Execution').")
            nb_dans_colonne = sum(1 for f in apres["formulaires"] if f["dansColonne"])
            print(f"   Formulaires 'contact' imbriques dans un wp-block-column : {nb_dans_colonne}")
        else:
            print("\n❌ Toujours 0 formulaire meme apres interaction -- l'hypothese du delai JS ne suffit pas a expliquer, a investiguer autrement.")

        browser.close()


if __name__ == "__main__":
    main()
