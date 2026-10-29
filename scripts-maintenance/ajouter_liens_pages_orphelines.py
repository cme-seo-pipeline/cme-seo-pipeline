"""
CME — Correction du maillage interne pour les 4 pages orphelines signalees
par l'operateur le 29/10/2026 (lecture seule par defaut, --apply pour
ecrire). Diagnostic prealable : inspecter_pages_orphelines.py +
inspecter_pages_orphelines_legacy.py (meme session).

Principe : plutot qu'une insertion automatique a un endroit arbitraire du
corps de texte (risque de casser la mise en forme ou de paraitre hors
contexte), on ajoute une seule phrase "Pour aller plus loin, consultez
notre guide sur ..." -- gabarit deja utilise ailleurs sur le site pour le
maillage inter-articles (vu notamment sur post_id=11035) -- dans UN
article existant, deja publie et thematiquement tres proche, pour chaque
page orpheline. Un seul lien entrant par page orpheline suffit a la
sortir du statut "orpheline" ; le choix du meilleur candidat (pas un
scoring automatique) a ete fait manuellement apres inspection des H2 et
des titres candidats du meme sous-silo.

Paires choisies (source = article qui recoit le nouveau lien, cible =
page orpheline) :
  1. source 8215 "Changer de fournisseur electricite apres un
     demenagement" -> cible post_id=3820 (demenagement, sujet quasi
     identique a la source -- lien naturel vers la version la plus
     complete/generique du sujet).
  2. source 8209 "Budget renovation toiture par type de materiau" ->
     cible post_id=3776 (un lecteur qui regarde le cout veut aussi
     connaitre les conditions d'eligibilite -- complementarite directe).
  3. source 7846 "Compteur electrique : fonctionnement et lecture
     expliques" -> cible post_id=4354 (apres avoir appris a lire son
     compteur, l'etape naturelle suivante est mesurer/optimiser sa
     consommation).
  4. source 12694 "Facture electricite : modele annote pour comprendre
     chaque ligne" (la plus recente du sous-silo) -> cible post_id=699
     (le contenu de la cible argumente explicitement que la facture
     d'electricite est le meilleur justificatif de domicile -- lien
     naturel depuis un guide de lecture de facture).

Insertion : une nouvelle balise <p> contenant la phrase + le lien, inseree
juste avant le premier <h2> dont le texte contient "FAQ"/"Foire"/
"Question" (repli : ajoutee a la toute fin du contenu si aucune section
FAQ n'est trouvee). Verifie au prealable que l'URL cible n'est pas deja
presente dans le contenu source (evite un doublon si relance).

USAGE :
  python3 ajouter_liens_pages_orphelines.py                 # dry-run (affiche le diff)
  python3 ajouter_liens_pages_orphelines.py --apply          # ecrit reellement
"""
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)

PAIRES = [
    {
        "source_post_id": 8215,
        "cible_url": "https://www.comprendre-mon-energie.fr/electricite/demenagement/changer-fournisseur-electricite-demenagement/",
        "ancre": "notre guide complet pour changer de fournisseur électricité",
    },
    {
        "source_post_id": 8209,
        "cible_url": "https://www.comprendre-mon-energie.fr/aide-energetique/aides-renovation-toiture/demarches-conditions-aides-renovation-toiture/",
        "ancre": "les démarches et conditions d'éligibilité pour les aides toiture",
    },
    {
        "source_post_id": 7846,
        "cible_url": "https://www.comprendre-mon-energie.fr/electricite/compteur/consommation-electrique-mesure-optimisation/",
        "ancre": "comment mesurer et réduire votre consommation électrique",
    },
    {
        "source_post_id": 12694,
        "cible_url": "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/justificatif-de-domicile/",
        "ancre": "comment obtenir un justificatif de domicile grâce à votre facture",
    },
]

FAQ_MOTS = ("faq", "foire", "question")


def recuperer_post(post_id):
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                      auth=AUTH, params={"context": "edit"}, timeout=20)
    r.raise_for_status()
    return r.json()


def inserer_lien(contenu_html, cible_url, ancre):
    if cible_url in contenu_html:
        return contenu_html, False, "lien deja present -- rien a faire"

    soup = BeautifulSoup(contenu_html, "html.parser")
    nouveau_p = soup.new_tag("p")
    nouveau_p.append("Pour aller plus loin, consultez ")
    a = soup.new_tag("a", href=cible_url)
    a.string = ancre
    nouveau_p.append(a)
    nouveau_p.append(".")

    cible_h2 = None
    for h2 in soup.find_all("h2"):
        texte = h2.get_text().lower()
        if any(mot in texte for mot in FAQ_MOTS):
            cible_h2 = h2
            break

    if cible_h2 is not None:
        cible_h2.insert_before(nouveau_p)
        emplacement = f"juste avant le H2 : {cible_h2.get_text().strip()[:80]!r}"
    else:
        soup.append(nouveau_p)
        emplacement = "a la toute fin du contenu (aucune section FAQ trouvee)"

    return str(soup), True, emplacement


def main():
    apply_ = "--apply" in sys.argv

    for paire in PAIRES:
        post_id = paire["source_post_id"]
        print("=" * 100)
        print(f"Source post_id={post_id}  →  cible {paire['cible_url']}")
        print("=" * 100)

        post = recuperer_post(post_id)
        titre = post["title"]["rendered"]
        contenu = post["content"]["raw"]
        print(f"  Titre source : {titre}")

        nouveau_contenu, modifie, emplacement = inserer_lien(contenu, paire["cible_url"], paire["ancre"])
        if not modifie:
            print(f"  ⏭️  {emplacement}")
            continue

        print(f"  ✏️  Insertion {emplacement}")
        print(f"      Phrase : « Pour aller plus loin, consultez {paire['ancre']}. »")

        if not apply_:
            print("  (dry-run -- aucune ecriture)")
            continue

        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            auth=AUTH,
            json={"content": nouveau_contenu},
            timeout=30,
        )
        if r.status_code == 200:
            print(f"  ✅ Article {post_id} mis a jour.")
        else:
            print(f"  ❌ Echec PATCH post_id={post_id} : {r.status_code} {r.text[:300]}")

    if not apply_:
        print("\n(dry-run global -- relancer avec --apply pour ecrire reellement.)")


if __name__ == "__main__":
    main()
