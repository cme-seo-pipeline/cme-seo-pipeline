"""
CME — Correction retroactive des 58 liens internes pointant vers une
redirection (vers 68 articles vivants), trouves le 27/11/2026 par
`diagnostiquer_liens_vers_redirections.py` (voir CLAUDE.md, suite de
l'audit Ahrefs du 21/11/2026 -- "Page has links to redirect", 81 pages).

Remplace chaque <a href="ANCIENNE_URL">texte</a> (ANCIENNE_URL repond un
3xx) par <a href="DESTINATION_FINALE">texte</a> (reponse 200 confirmee par
le diagnostic) -- garde le texte de l'ancre, change uniquement l'URL,
exactement comme fix_liens_morts_maillage_0211.py et
fix_cta_liens_retroactif.py. Detection via BeautifulSoup (pas de regex sur
HTML imbrique).

Table REMPLACEMENTS generee programmatiquement a partir du log du
diagnostic (58 paires, toutes resolues a un HTTP 200 final, aucun doublon
de cle) -- pas transcrite a la main.

Dry-run par defaut (affiche ce qui SERAIT change, n'ecrit rien).
--apply pour ecrire reellement (PATCH WordPress, content uniquement --
jamais de cle 'slug', voir audit du 31/10 dans CLAUDE.md).
--limite=N pour cibler les N premiers articles qui ont REELLEMENT un lien
a corriger.
"""
import argparse
import os
import sys

from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
TIMEOUT = 20
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")

# URL source (repond un 3xx) -> destination finale (confirmee HTTP 200),
# issues de scripts-maintenance/logs/20261127-134607-diagnostiquer_liens_vers_redirections.log
REMPLACEMENTS = {
    "https://www.comprendre-mon-energie.fr/comparateur-electricite/": "https://www.comprendre-mon-energie.fr/comparateur-energie-electricite-gaz/",
    "https://www.comprendre-mon-energie.fr/comprendre-sa-facture-delectricite/": "https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/comprendre-sa-facture-delectricite/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/maprimerenov/maprimerenov-montants-baremes-2026/": "https://www.comprendre-mon-energie.fr/aide-energetique/maprimerenov/delais-versement-maprimerenov-2025/",
    "https://www.comprendre-mon-energie.fr/gaz/facture-gaz/strategies-maitrise-facture-gaz/": "https://www.comprendre-mon-energie.fr/gaz/facture-gaz/facture-gaz-ttc-vs-ht-taxes/",
    "https://www.comprendre-mon-energie.fr/demenagement-electricite/": "https://www.comprendre-mon-energie.fr/electricite/demenagement/normes-electriques/",
    "https://www.comprendre-mon-energie.fr/guide-gratuit-travaux-de-renovation-energetique/": "https://www.comprendre-mon-energie.fr/renovation-energetique/renovation-globale/guide-gratuit-travaux-de-renovation-energetique/",
    "https://www.comprendre-mon-energie.fr/pompe-a-chaleur/": "https://www.comprendre-mon-energie.fr/renovation-energetique/pompe-a-chaleur/",
    "https://www.comprendre-mon-energie.fr/reduire-sa-facture-delectricite/": "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/reduire-sa-facture-delectricite/",
    "https://www.comprendre-mon-energie.fr/attestation-de-contrat-delectricite/": "https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/attestation-de-contrat-delectricite/",
    "https://www.comprendre-mon-energie.fr/demande-de-rappel-gratuit/": "https://www.comprendre-mon-energie.fr/contactez-un-expert/",
    "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/aides-chauffe-eau-solaire-2026/": "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/chauffe-eau-solaire-vs-gaz-roi/",
    "https://www.comprendre-mon-energie.fr/?p=4456": "https://www.comprendre-mon-energie.fr/solaire/panneaux-solaires/fonctionnement-panneaux-solaires-photovoltaiques/",
    "https://www.comprendre-mon-energie.fr/renovation-energetique/pompe-a-chaleur/aides-pompe-a-chaleur-2026-0812/": "https://www.comprendre-mon-energie.fr/renovation-energetique/pompe-a-chaleur/aides-pompe-a-chaleur-2024-0812/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/prime-energie/cumul-aides-energetiques-2026/": "https://www.comprendre-mon-energie.fr/aide-energetique/prime-energie/cumul-aides-energetiques-2025/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/tva-reduite/tva-reduite-travaux-renovation-2026/": "https://www.comprendre-mon-energie.fr/aide-energetique/aides-combles-perdus/cout-isolation-combles-perdus-devis-aides/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/cheque-energie/cheque-energie-2026-eligibilite-obtention/": "https://www.comprendre-mon-energie.fr/aide-energetique/cheque-energie/cheque-energie-refuse-causes-solutions/",
    "https://www.comprendre-mon-energie.fr/aide-energetic/cheque-energie/cheque-energie-comment-utiliser-fournisseur/": "https://www.comprendre-mon-energie.fr/aide-energetique/cheque-energie/cheque-energie-comment-utiliser-fournisseur/",
    "https://www.comprendre-mon-energie.fr/aide-energetic/maprimerenov/maprimerenov-montants-conditions-eligibilite-2026/": "https://www.comprendre-mon-energie.fr/aide-energetique/maprimerenov/maprimerenov-montants-conditions-eligibilite-2026/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/eco-pret-a-taux-zero/eco-ptz-fonctionnement-pret-sans-interet/": "https://www.comprendre-mon-energie.fr/aide-energetique/tva-reduite/tva-reduite-travaux-energetiques-conditions/",
    "https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/changement-fournisseur-electricite-delais-procedure/": "https://www.comprendre-mon-energie.fr/electricite/chauffage-electricite/installation-chauffage-electrique-normes-cout/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/prime-energie/pompe-chaleur-air-air-vs-climatisation/": "https://www.comprendre-mon-energie.fr/aide-energetique/eco-pret-a-taux-zero/eco-ptz-fonctionnement-complet/",
    "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/facture-electricite-trop-chere-reduire/": "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/justificatif-de-domicile/",
    "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/aides-chauffe-eau-solaire/": "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/chauffe-eau-solaire-vs-thermodynamique/",
    "https://www.comprendre-mon-energie.fr/aide-etat-thermostat-connecte/": "https://www.comprendre-mon-energie.fr/aide-energetique/prime-energie/aide-etat-thermostat-connecte/",
    "https://www.comprendre-mon-energie.fr/chauffage-gaz/": "https://www.comprendre-mon-energie.fr/gaz/chauffage-gaz/",
    "https://www.comprendre-mon-energie.fr/cheque-energie-2026/": "https://www.comprendre-mon-energie.fr/aide-energetique/cheque-energie/cheque-energie-2026/",
    "https://www.comprendre-mon-energie.fr/installation-panneaux-photovoltaiques/": "https://www.comprendre-mon-energie.fr/solaire/panneaux-solaires/installation-panneaux-photovoltaiques/",
    "https://www.comprendre-mon-energie.fr/simulateur-aides-renovation-2026-calculez-votre-reste-a-charge-0-en-2-min/": "https://www.comprendre-mon-energie.fr/contactez-un-expert/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/aides-locales-chauffe-eau-thermodynamique-region/": "https://www.comprendre-mon-energie.fr/aide-energetique/aides-chauffe-eau-thermodynamique/aides-locales-chauffe-eau-thermodynamique-region/",
    "https://www.comprendre-mon-energie.fr/gaz/bouteilles/comparatif-fournisseurs-gaz-naturel/": "https://www.comprendre-mon-energie.fr/gaz/facture-gaz/comparatif-fournisseurs-gaz-naturel/",
    "https://www.comprendre-mon-energie.fr/aides-renovation-energetique/": "https://www.comprendre-mon-energie.fr/gaz/facture-gaz/facture-gaz-septembre-2026/",
    "https://www.comprendre-mon-energie.fr/gaz/bouteilles/installation-bouteille-de-gaz-normes-securite-1018/": "https://www.comprendre-mon-energie.fr/gaz/bouteilles/prix-bouteille-gaz-2024/",
    "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/aides-electricite-2026-reductions/": "https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/aides-electricite-2026-reductions/",
    "https://www.comprendre-mon-energie.fr/aide-energetic/cheque-energie/comment-utiliser-cheque-energie-1002/": "https://www.comprendre-mon-energie.fr/aide-energetique/cheque-energie/comment-utiliser-cheque-energie-1002/",
    "https://www.comprendre-mon-energie.fr/gaz/bouteilles/negocier-ses-tarifs-et-reduire-sa/": "https://www.comprendre-mon-energie.fr/gaz/bouteilles/prix-bouteille-de-gaz-tarifs-1002/",
    "https://www.comprendre-mon-energie.fr/gaz/bouteilles/recharger-bouteille-de-gaz-securite/": "https://www.comprendre-mon-energie.fr/gaz/bouteilles/prix-bouteille-de-gaz-tarifs-1002/",
    "https://www.comprendre-mon-energie.fr/aides-renovation-energetique": "https://www.comprendre-mon-energie.fr/gaz/facture-gaz/facture-gaz-septembre-2026/",
    "https://www.comprendre-mon-energie.fr/aide-energetic/aides-renovation-toiture/cout-renovation-toiture-tarifs-aides/": "https://www.comprendre-mon-energie.fr/aide-energetique/aides-renovation-toiture/cout-renovation-toiture-tarifs-aides/",
    "https://www.comprendre-mon-energie.fr/aide-energetic/aides-chauffe-eau-thermodynamique/prix-chauffe-eau-thermodynamique-tarifs/": "https://www.comprendre-mon-energie.fr/aide-energetique/aides-chauffe-eau-thermodynamique/prix-chauffe-eau-thermodynamique-tarifs/",
    "https://www.comprendre-mon-energie.fr/aide-energetic/tva-reduite/tva-reduite-fenetres-economies-conditions/": "https://www.comprendre-mon-energie.fr/aide-energetique/tva-reduite/tva-reduite-fenetres-economies-conditions/",
    "https://www.comprendre-mon-energie.fr/aide-energetic/maprimerenov/comment-fonctionne-maprimerenov-2026/": "https://www.comprendre-mon-energie.fr/aide-energetique/maprimerenov/comment-fonctionne-maprimerenov-2026/",
    "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/comparer-fournisseurs-electricite/les meilleures comparaisons": "https://www.comprendre-mon-energie.fr/electricite/demenagement/changer-fournisseur-electricite-demenagement-0924/",
    "https://www.comprendre-mon-energie.fr/electricite/demenagement/transfert-contrat-electricite-demenagement/": "https://www.comprendre-mon-energie.fr/electricite/demenagement/electricite-demenagement-guide-complet-0904/",
    "https://www.comprendre-mon-energie.fr/gaz/bouteilles/bouteille-gaz-propane-fonctionnement/": "https://www.comprendre-mon-energie.fr/gaz/demenagement-gaz/compteur-gaz-communicant-linky/",
    "https://www.comprendre-mon-energie.fr/aide-energetic/eco-pret-a-taux-zero/eco-ptz-vs-maprimerenov-quel-financement-choisir/": "https://www.comprendre-mon-energie.fr/aide-energetique/eco-pret-a-taux-zero/eco-ptz-vs-maprimerenov-quel-financement-choisir/",
    "https://www.comprendre-mon-energie.fr/gaz/gaz/comparatifs-fournisseurs-gaz/meilleurs-fournisseurs-gaz-comparatif-tarifs-2024/": "https://www.comprendre-mon-energie.fr/gaz/comparatifs-fournisseurs-gaz/meilleurs-fournisseurs-gaz-comparatif-tarifs-2024/",
    "https://www.comprendre-mon-energie.fr/electricite/compteur/consommation-electricite-mesure-optimisation/": "https://www.comprendre-mon-energie.fr/electricite/compteur/consommation-electrique-mesure-optimisation/",
    "https://www.comprendre-mon-energie.fr/solaire/kit-solaire/installation-kit-solaire/": "https://www.comprendre-mon-energie.fr/solaire/kit-solaire/kit-solaire-autonome-dimensionnement/",
    "https://www.comprendre-mon-energie.fr/gaz/chauffage-gaz/raccordement-au-gaz/": "https://www.comprendre-mon-energie.fr/gaz/chauffage-gaz/guide-chauffage-gaz/",
    "https://www.comprendre-mon-energie.fr/electricite/facture/lire-sa-facture-d-electricite/": "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/lire-sa-facture-d-electricite/",
    "https://www.comprendre-mon-energie.fr/electricite/facture/reduire-sa-facture-delectricite/": "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/reduire-sa-facture-delectricite/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/maprimerenov/aides-energetiques/": "https://www.comprendre-mon-energie.fr/aide-energetique/maprimerenov/aides-energetiques-guide-2/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/prime-energie/aides-energetiques-2/": "https://www.comprendre-mon-energie.fr/aide-energetique/prime-energie/aides-energetiques-guide/",
    "https://www.comprendre-mon-energie.fr/electricite/contrat/attestation-de-contrat-delectricite/": "https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/attestation-de-contrat-delectricite/",
    "https://www.comprendre-mon-energie.fr/electricite/comparatifs-fournisseurs/comparateur-electricite/": "https://www.comprendre-mon-energie.fr/electricite/comparatifs-fournisseurs-electricite/comparateur-electricite/",
    "https://www.comprendre-mon-energie.fr/justificatif-de-domicile/": "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/justificatif-de-domicile/",
    "https://www.comprendre-mon-energie.fr/heures-creuses-heures-pleines/": "https://www.comprendre-mon-energie.fr/electricite/heures-pleines-creuses/heures-creuses/",
    "https://www.comprendre-mon-energie.fr/la-transition-energetique/": "https://www.comprendre-mon-energie.fr/aide-energetique/prime-energie/transition-energetique/",
}
# Formes sans slash final, au cas ou le lien genere n'en avait pas (meme
# precaution que fix_liens_morts_maillage_0211.py) -- sauf pour le cas
# avec espace et pour ?p=, deja sans slash final par nature.
REMPLACEMENTS.update({
    k.rstrip("/"): v for k, v in list(REMPLACEMENTS.items())
    if k.endswith("/") and " " not in k
})

print(f"Table chargee : {len(REMPLACEMENTS)} entree(s) (avec variantes sans slash final).")


def lister_tous_les_posts():
    posts, page = [], 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={"per_page": 100, "page": page, "status": "publish", "context": "edit",
                    "_fields": "id,link,content"},
            auth=(WP_USERNAME, WP_APP_PASSWORD),
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        posts.extend(data)
        page += 1
    return posts


def corriger_contenu(contenu_raw):
    soup = BeautifulSoup(contenu_raw, "html.parser")
    nb_corriges = 0
    details = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Resout en absolu avant de comparer -- certains liens du contenu
        # sont relatifs (ex. post_id=8340, "/aides-renovation-energetique"),
        # alors que REMPLACEMENTS est toujours indexe en URL absolue (meme
        # forme que le diagnostic, qui fait deja ce urljoin avant de
        # regrouper). Sans ca, un lien relatif ne matcherait jamais.
        href_absolu = urljoin(WP_URL + "/", href)
        if href_absolu in REMPLACEMENTS:
            cible = REMPLACEMENTS[href_absolu]
            details.append((href, cible, a.get_text()))
            a["href"] = cible
            nb_corriges += 1
    return str(soup), nb_corriges, details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limite", type=int, default=None)
    args = parser.parse_args()

    print("Recuperation de tous les articles publies (contenu brut, ?context=edit)...")
    posts = lister_tous_les_posts()
    print(f"{len(posts)} article(s) recupere(s).\n")

    traites = 0
    total_liens_corriges = 0
    for post in posts:
        contenu_raw = post.get("content", {}).get("raw", "") or post.get("content", {}).get("rendered", "")
        # Pas de pre-filtre par sous-chaine ici (contrairement a
        # fix_liens_morts_maillage_0211.py) : certains hrefs du contenu
        # sont relatifs, donc la forme absolue des cles de REMPLACEMENTS
        # ne serait pas forcement une sous-chaine litterale du contenu
        # brut -- on passe directement par BeautifulSoup + urljoin pour
        # chaque article, qui gere correctement les deux formes.
        nouveau_contenu, nb_corriges, details = corriger_contenu(contenu_raw)
        if nb_corriges == 0:
            continue

        print(f"\n{'='*100}")
        print(f"ARTICLE : {post.get('link')} (id={post.get('id')})")
        print(f"  {nb_corriges} lien(s) vers une redirection a corriger :")
        for href, cible, texte in details:
            print(f"    - \"{texte}\" : {href}")
            print(f"      -> {cible}")

        if args.apply:
            r = requests.post(
                f"{WP_URL}/wp-json/wp/v2/posts/{post['id']}",
                auth=(WP_USERNAME, WP_APP_PASSWORD),
                json={"content": nouveau_contenu},
                timeout=TIMEOUT,
            )
            if r.status_code == 200:
                print("  ✅ Corrige et publie.")
            else:
                print(f"  ❌ Echec PATCH : HTTP {r.status_code} -- {r.text[:300]}")
        else:
            print("  (dry-run -- rien ecrit, relancer avec --apply pour corriger reellement)")

        total_liens_corriges += nb_corriges
        traites += 1
        if args.limite and traites >= args.limite:
            print(f"\n⏹️ Limite de {args.limite} article(s) atteinte, arret.")
            break

    print(f"\n{'='*100}")
    print(f"TOTAL : {traites} article(s) traite(s), {total_liens_corriges} lien(s) "
          f"{'corrige(s)' if args.apply else 'detecte(s) (dry-run)'}.")
    print("=" * 100)


if __name__ == "__main__":
    main()
