"""
CME — Inspection des 3 destinations a instrumenter pour le tracking de
conversion (demande explicite de l'operateur, oct. 2026) :
1. /contactez-un-expert/ : quel systeme de formulaire est utilise (le
   detecter avant d'ecrire le JS de tracking -- Contact Form 7, Gravity
   Forms, WPForms, bloc natif Gutenberg... chacun a un evenement JS
   different a ecouter).
2. Le numero de telephone du header : confirme deja present (tel: lien,
   chantier precedent) -- on verifie juste sa structure HTML exacte ici.
3. Les 3 anciens simulateurs (comparateur-energie-electricite-gaz,
   simulateur-aides-renovation-energetique, devis-panneau-solaire) :
   sont-ils encore des pages live, et leur JS de tracking existant
   (log-lead/log-clic) est-il toujours present dans le HTML rendu ?

Lecture seule. Necessite un acces reseau complet au site live, donc
s'execute via le pont GitHub Actions (le sandbox Claude Code ne peut pas
joindre le site directement).
"""
import re
import sys
import requests

WP_URL = "https://www.comprendre-mon-energie.fr"

PAGES = {
    "contact": "/contactez-un-expert/",
    "simulateur_comparateur": "/comparateur-energie-electricite-gaz/",
    "simulateur_aides": "/simulateur-aides-renovation-energetique/",
    "simulateur_solaire": "/devis-panneau-solaire/",
}

INDICES_FORMULAIRE = {
    "Contact Form 7": [r'wpcf7', r'class="wpcf7"'],
    "Gravity Forms": [r'gform_wrapper', r'gform_\d+'],
    "WPForms": [r'wpforms-form', r'wpforms-container'],
    "Forminator": [r'forminator-custom-form'],
    "Ninja Forms": [r'nf-form-cont'],
    "Formidable Forms": [r'frm_forms', r'frm-show-form'],
    "Bloc natif Gutenberg (core/form)": [r'wp-block-form'],
}


def analyser_formulaire(html):
    trouves = []
    for nom, motifs in INDICES_FORMULAIRE.items():
        if any(re.search(m, html, re.IGNORECASE) for m in motifs):
            trouves.append(nom)
    # Extrait toutes les balises <form ...> pour inspection manuelle si rien n'est reconnu
    formulaires_bruts = re.findall(r'<form\b[^>]*>', html, re.IGNORECASE)
    return trouves, formulaires_bruts


def main():
    for cle, chemin in PAGES.items():
        url = WP_URL + chemin
        print(f"\n{'='*70}")
        print(f"{cle} — {url}")
        print(f"{'='*70}")
        try:
            resp = requests.get(url, timeout=20, allow_redirects=True)
        except Exception as e:
            print(f"❌ Erreur reseau : {e}")
            continue

        print(f"Statut HTTP : {resp.status_code}  (URL finale : {resp.url})")
        if resp.status_code != 200:
            continue

        html = resp.text

        if cle == "contact":
            trouves, formulaires_bruts = analyser_formulaire(html)
            print(f"Systeme(s) de formulaire detecte(s) : {trouves or 'AUCUN motif connu reconnu'}")
            print(f"Balises <form> trouvees ({len(formulaires_bruts)}) :")
            for f in formulaires_bruts[:5]:
                print(f"  {f[:200]}")
            m = re.search(r'<a[^>]*href="tel:[^"]*"[^>]*>.*?</a>', html, re.IGNORECASE | re.DOTALL)
            if m:
                print(f"(info) lien tel: egalement present sur cette page : {m.group(0)[:200]}")
        else:
            # Simulateurs : confirme la presence du JS de tracking existant
            a_log_lead = "log-lead" in html or "log_lead" in html
            a_log_clic = "log-clic" in html or "log_clic" in html
            a_datalayer = "dataLayer" in html
            print(f"Reference a /api/log-lead dans le HTML : {a_log_lead}")
            print(f"Reference a /api/log-clic dans le HTML : {a_log_clic}")
            print(f"Reference a dataLayer (GTM) dans le HTML : {a_datalayer}")

    print(f"\n{'='*70}")
    print("Numero de telephone du header (verification structure exacte)")
    print(f"{'='*70}")
    try:
        resp = requests.get(WP_URL + "/", timeout=20)
        m = re.search(r'<a[^>]*href="tel:[^"]*"[^>]*>.*?</a>', resp.text, re.IGNORECASE | re.DOTALL)
        print(m.group(0) if m else "⚠️ Lien tel: non trouve sur la page d'accueil")
    except Exception as e:
        print(f"❌ Erreur : {e}")


if __name__ == "__main__":
    main()
