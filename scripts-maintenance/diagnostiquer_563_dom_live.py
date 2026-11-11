"""
CME — Diagnostic DOM live pour id=563 (seul deficit reel confirme du run
reverifier_deficit_partiel_48.py, 4 formulaires rendus / 7 attendus par la
simulation sur le contenu BRUT stocke).

Hypothese a confirmer : le contenu stocke de cet article embarque
directement un widget/outil legacy avec son propre <script>/<style>/
<form> (voir diagnostiquer_2_cas_48_1111.py) -- si ce script modifie le
DOM de .entry-content avant que cme-cta-progressifs.php n'y pose ses
formulaires, la structure REELLEMENT vue par l'algorithme de placement
en live differe de celle du HTML brut recupere via l'API REST, ce qui
expliquerait l'ecart sans etre un bug du correctif lui-meme.

Ce script charge la page en conditions reelles (meme simulation
d'interaction que d'habitude pour contourner le Delay JS Execution de
LiteSpeed) et dump la structure REELLE de .entry-content telle que vue
par le navigateur, pour comparer directement au contenu brut.

LECTURE SEULE.
"""
import subprocess
import sys

SITE = "https://www.comprendre-mon-energie.fr"
CHEMIN = "/electricite/comparatifs-fournisseurs-electricite/changer-fournisseur-electricite/"


def main():
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "playwright"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        url = SITE + CHEMIN + "?t=" + str(__import__("random").randint(100000, 999999))
        page.goto(url, wait_until="load", timeout=45000)
        page.mouse.move(200, 300)
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(1000)
        page.mouse.wheel(0, 1200)
        page.wait_for_timeout(1500)

        n_formulaires = page.evaluate("document.querySelectorAll('.cme-cta60[data-pos]').length")
        positions = page.evaluate("[...document.querySelectorAll('.cme-cta60[data-pos]')].map(e => e.dataset.pos)")
        print(f"Formulaires rendus : {n_formulaires}, positions = {positions}")

        # Dump la structure reelle de .entry-content, telle que vue par
        # le navigateur APRES execution de tous les scripts de la page
        # (y compris le widget legacy embarque dans le contenu).
        structure = page.evaluate("""
            () => {
                const zone = document.querySelector('.entry-content');
                if (!zone) return null;
                return [...zone.children].map((el, i) => ({
                    i,
                    tag: el.tagName,
                    classe: el.className || '',
                    mots: (el.textContent || '').trim().split(/\\s+/).filter(Boolean).length,
                    estCta: el.classList.contains('cme-cta60')
                }));
            }
        """)
        print(f"\nNombre d'enfants DIRECTS de .entry-content vus en live : {len(structure) if structure else 0}")
        if structure:
            for e in structure:
                marqueur = " [CTA]" if e["estCta"] else ""
                print(f"  [{e['i']:>3}] <{e['tag']}> class=\"{e['classe']}\" {e['mots']} mots{marqueur}")

        browser.close()


if __name__ == "__main__":
    main()
