"""
CME — Inspection (lecture seule) du bouton telephone du header, sur
demande de l'operateur du 25/10/2026 : reduire la taille du bouton et de
la police du numero affiche en header, visible au scroll (sticky).

Cet element n'est gere par AUCUN fichier de ce repo (ni pipeline.py, ni
cme-cta-progressifs.php, ni cme-tracking-conversion.php -- qui se contente
d'ecouter les clics sur tel:, sans rien styler) : c'est probablement du
contenu natif du theme WordPress (header.php du theme, ou CSS additionnel
via le Customizer), meme famille que le widget du footer deja documente
dans CLAUDE.md comme invisible depuis ce repo.

Objectif de ce script : recuperer le HTML/CSS reel autour du lien tel:
dans le header, pour identifier le(s) bon(s) selecteur(s) CSS a cibler --
avant d'ecrire quoi que ce soit. Lecture seule, aucune ecriture.

Necessite un acces reseau complet au site live (fourni par le runner
GitHub Actions, pas par le sandbox Claude Code).
"""
import re
import requests

BASE = "https://www.comprendre-mon-energie.fr"
PAGES = [
    BASE + "/",
    BASE + "/contactez-un-expert/",
]


def extraire_contexte(html, motif, avant=400, apres=400):
    resultats = []
    for m in re.finditer(re.escape(motif), html):
        debut = max(0, m.start() - avant)
        fin = min(len(html), m.end() + apres)
        resultats.append(html[debut:fin])
    return resultats


def main():
    for url in PAGES:
        print("=" * 70)
        print(f"Page : {url}")
        print("=" * 70)
        try:
            resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (CME-QA-bot)"})
            print(f"HTTP {resp.status_code}, {len(resp.text)} caracteres")
            html = resp.text

            # 1) tous les liens tel: dans la page
            liens_tel = re.findall(r'<a[^>]+href=["\']tel:[^"\']*["\'][^>]*>.*?</a>', html)
            print(f"\n{len(liens_tel)} lien(s) tel: trouve(s) dans la page.")

            # 2) contexte autour du PREMIER lien tel: (presume le plus haut = header)
            m = re.search(r'href=["\']tel:', html)
            if m:
                contexte = html[max(0, m.start() - 600):m.start() + 600]
                print("\n--- Contexte autour du premier lien tel: (header presume) ---")
                print(contexte)
            else:
                print("\n⚠️ Aucun lien tel: trouve sur cette page.")

            # 3) recherche de mots-cles sticky/fixed dans les balises <style> inline
            styles_inline = re.findall(r'<style[^>]*>(.*?)</style>', html, re.S)
            sticky_css = []
            for s in styles_inline:
                if 'sticky' in s.lower() or ('position' in s.lower() and 'fixed' in s.lower()):
                    sticky_css.append(s[:2000])
            print(f"\n{len(sticky_css)} bloc(s) <style> inline mentionnant sticky/fixed.")
            for i, s in enumerate(sticky_css[:3]):
                print(f"--- bloc {i+1} ---")
                print(s)

        except Exception as e:
            print(f"❌ Erreur : {e}")
        print()


if __name__ == "__main__":
    main()
