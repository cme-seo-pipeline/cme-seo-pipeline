"""
CME — Diagnostic URGENT (Playwright) : le script precedent
(verifier_fix_colonnes_en_conditions_reelles.py) a trouve ZERO element
.cme-cta60 sur les 3 articles testes, y compris id=2218 dont le bloc
"avant d'appeler" fonctionnait AVANT le correctif du 04/11 (confirme par
interactions_contenu). Ca sent une regression plus large que le seul
correctif Colonnes -- ce script capture TOUT ce qui peut expliquer
pourquoi, sur une seule page (id=2218) :
  - les messages console (y compris console.error, que demarrer() emet
    TOUJOURS en cas d'exception, meme en MODE='actif') ;
  - les erreurs JS non interceptees (pageerror) ;
  - la presence du script #cme-cta-progressifs dans le HTML servi
    (deploiement bien pris en compte, pas un vieux cache) ;
  - la presence de CME_POST_ID, body.single-post, article.type-post,
    .entry-content (les gardes successives de demarrer()) ;
  - un extrait du debut du script tel que SERVI (pour confirmer qu'il
    contient bien enfantsEffectifs/estConteneurLayout, pas une ancienne
    version).

LECTURE SEULE.

USAGE :
  python3 diagnostiquer_absence_cme_cta60.py
"""
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

        messages_console = []
        erreurs_page = []
        page.on("console", lambda msg: messages_console.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda exc: erreurs_page.append(str(exc)))

        import random
        url = URL + "?t=" + str(random.randint(100000, 999999))
        print(f"Chargement de {url} ...")
        resp = page.goto(url, wait_until="load", timeout=45000)
        print(f"HTTP status : {resp.status if resp else 'inconnu'}")
        page.wait_for_timeout(2000)

        print("\n--- Messages console capture pendant le chargement ---")
        if not messages_console:
            print("  (aucun)")
        else:
            for m in messages_console:
                print(f"  {m}")

        print("\n--- Erreurs JS non interceptees (pageerror) ---")
        if not erreurs_page:
            print("  (aucune)")
        else:
            for e in erreurs_page:
                print(f"  {e}")

        print("\n--- Verification des gardes successives de demarrer() ---")
        diag = page.evaluate("""
            () => {
                const scriptTag = document.getElementById('cme-cta-progressifs');
                const dataTag = document.getElementById('cme-cta-progressifs-data');
                return {
                    scriptPresent: !!scriptTag,
                    scriptLength: scriptTag ? scriptTag.textContent.length : 0,
                    contientEnfantsEffectifs: scriptTag ? scriptTag.textContent.indexOf('enfantsEffectifs') !== -1 : false,
                    contientEstConteneurLayout: scriptTag ? scriptTag.textContent.indexOf('estConteneurLayout') !== -1 : false,
                    CME_POST_ID: window.CME_POST_ID,
                    bodyClasses: document.body ? document.body.className : null,
                    bodyHasSinglePost: document.body ? document.body.classList.contains('single-post') : null,
                    articlePresent: !!document.querySelector('article.type-post'),
                    entryContentPresent: !!document.querySelector('article.type-post .entry-content'),
                    dataCta60Attr: (() => {
                        const z = document.querySelector('article.type-post .entry-content');
                        return z ? z.getAttribute('data-cta60') : null;
                    })(),
                    debutScript: scriptTag ? scriptTag.textContent.slice(0, 300) : null
                };
            }
        """)
        for k, v in diag.items():
            if k == "debutScript":
                continue
            print(f"  {k} = {v!r}")

        print("\n--- Debut du script #cme-cta-progressifs tel que servi (300 premiers caracteres) ---")
        print(diag.get("debutScript"))

        browser.close()


if __name__ == "__main__":
    main()
