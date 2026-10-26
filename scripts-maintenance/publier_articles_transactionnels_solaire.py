"""
CME — Production ciblee de 10 nouveaux articles Solaire a intention
TRANSACTIONNELLE (2 par sous-silo x 5 sous-silos), chantier "Pages pilier
Solaire + maillage interne" du 26/10/2026.

Contexte : le silo Solaire a le meilleur taux de conversion du site (2,63%,
voir analyser_potentiel_silos.py) mais le trafic organique le plus faible.
Decision operateur : au lieu de laisser le tirage quotidien habituel
(pilote par les mots-cles GSC, angle generalement informationnel -- voir
selectionner_silos_a_traiter dans pipeline.py) choisir les sujets, on force
10 mots-cles choisis a la main pour leur intention TRANSACTIONNELLE (prix,
devis, rentabilite, dimensionnement/budget) -- le profil de visiteur le
plus proche de remplir le mini-formulaire inline. Chaque sujet a ete
verifie a la main contre les articles deja publies de son sous-silo (voir
cartographie_pilier_sous_silos_solaire.py) pour eviter tout chevauchement.

Reutilise integralement les fonctions existantes de pipeline/pipeline.py --
AUCUNE reimplementation de la logique de redaction/publication :
  - generer_brief_silo(..., mot_cle_force=..., angle_force=...) : parametre
    ajoute le 26/10/2026 specifiquement pour ce chantier (defaut None =
    comportement du run quotidien strictement inchange).
  - rediger_article() : identique au run quotidien.
  - inserer_lien_pilier() : insertion du lien vers la page pilier du
    sous-silo, table LIENS_PILIERS_SOUS_SILO etendue a Solaire dans le
    meme commit que ce script.
  - publier_article() : publication WordPress + log BigQuery, identique.

Volontairement HORS PERIMETRE pour ce lot (a ajouter separement si
souhaite) : verifier_et_differencier_sujet() (le dedoublonnage a deja ete
fait a la main sur les 10 sujets, et cette fonction peut reecrire le
mot-cle impose si elle detecte un chevauchement -- on ne veut pas qu'elle
contourne silencieusement le ciblage transactionnel voulu ici), schemas SVG,
featured images, Facebook/Instagram (deja desactive globalement via
CONFIG['FACEBOOK_INSTAGRAM_ACTIF']=False).

USAGE :
  python3 publier_articles_transactionnels_solaire.py                 # dry-run (defaut) : genere et affiche, ne publie rien
  python3 publier_articles_transactionnels_solaire.py --limite=1      # dry-run sur le 1er sujet seulement (test rapide)
  python3 publier_articles_transactionnels_solaire.py --apply --limite=1   # publie REELLEMENT 1 seul article (test)
  python3 publier_articles_transactionnels_solaire.py --apply         # publie REELLEMENT les 10 articles

Necessite ANTHROPIC_API_KEY (+ WP_APP_PASSWORD si --apply) et
GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
"""
import sys
import os
import re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import (
        CONFIG, WP_CONFIG, init_bigquery, creer_table_historique,
        generer_brief_silo, recuperer_articles_meme_sous_silo,
        recuperer_articles_meme_silo, rediger_article, inserer_lien_pilier,
        publier_article, nettoyer_texte_ia, LIENS_PILIERS_SOUS_SILO,
    )
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

SILO = "4. Solaire"

# 10 sujets (2 par sous-silo), intention transactionnelle, verifies a la
# main contre les articles existants de chaque sous-silo (aucun ne
# chevauche un sujet deja publie -- voir le detail du raisonnement dans la
# conversation, notamment l'exclusion de "prix"/"devis" pour
# Panneaux solaires et Chauffe-eau solaire, deja couverts par ailleurs).
SUJETS = [
    {"sous_silo": "Kit solaire",
     "mot_cle_force": "prix kit solaire autoconsommation installation comprise",
     "angle_force": "Prix/devis : combien coûte un kit solaire posé par un professionnel, budget réel tout compris, pour quelqu'un qui compare avant de demander un devis."},
    {"sous_silo": "Kit solaire",
     "mot_cle_force": "rentabilité kit solaire temps de retour sur investissement",
     "angle_force": "Rentabilité : en combien d'années un kit solaire est amorti, calcul concret, pour quelqu'un qui hésite encore à investir."},

    {"sous_silo": "Batterie panneaux solaires",
     "mot_cle_force": "prix batterie solaire installation coût",
     "angle_force": "Prix/devis : budget réel pour une batterie de stockage solaire posée, pour quelqu'un qui compare avant de demander un devis."},
    {"sous_silo": "Batterie panneaux solaires",
     "mot_cle_force": "quelle capacité batterie solaire choisir pour sa maison",
     "angle_force": "Aide au choix : quelle capacité (kWh) choisir selon sa consommation, pour quelqu'un prêt à sélectionner un produit précis."},

    {"sous_silo": "Système solaire combiné",
     "mot_cle_force": "système solaire combiné vs chaudière gaz quel est le plus rentable",
     "angle_force": "Comparatif rentabilité SSC vs chaudière gaz classique, pour quelqu'un qui compare deux solutions avant de choisir -- intention d'achat."},
    {"sous_silo": "Système solaire combiné",
     "mot_cle_force": "système solaire combiné temps de retour sur investissement rentabilité",
     "angle_force": "Rentabilité/payback : en combien d'années un SSC est amorti, distinct du coût d'installation déjà couvert ailleurs sur le site."},

    {"sous_silo": "Chauffe-eau solaire",
     "mot_cle_force": "chauffe-eau solaire rentabilité économies par an",
     "angle_force": "Rentabilité : combien d'économies réelles par an, pour quelqu'un qui hésite à investir."},
    {"sous_silo": "Chauffe-eau solaire",
     "mot_cle_force": "chauffe-eau solaire vs chauffe-eau électrique classique quel est le plus économique",
     "angle_force": "Comparatif économique solaire vs électrique classique (distinct des comparatifs vs thermodynamique déjà publiés), pour quelqu'un qui choisit avant d'acheter."},

    {"sous_silo": "Panneaux solaires",
     "mot_cle_force": "rentabilité panneaux solaires temps de retour sur investissement",
     "angle_force": "Rentabilité : temps de retour réel, distinct du prix/devis déjà couverts ailleurs sur le site, pour quelqu'un qui hésite à investir."},
    {"sous_silo": "Panneaux solaires",
     "mot_cle_force": "combien de panneaux solaires faut-il pour une maison budget",
     "angle_force": "Dimensionnement + budget : combien de panneaux et quel budget selon sa surface/consommation, pour quelqu'un prêt à demander un devis précis."},
]


def traiter_un_sujet(sujet, client_bq, apply_mode, run_id):
    silo, sous_silo = SILO, sujet["sous_silo"]
    print(f"\n{'='*70}")
    print(f"📂 {silo} | {sous_silo} — mot-clé imposé : {sujet['mot_cle_force']}")
    print(f"{'='*70}")

    contexte = {"silo": silo, "sous_silo": sous_silo}
    brief, erreur = generer_brief_silo(
        contexte, CONFIG,
        mot_cle_force=sujet["mot_cle_force"],
        angle_force=sujet["angle_force"],
    )
    if erreur:
        print(f"  ❌ Brief : {erreur}")
        return None

    annee_courante = datetime.now().year
    brief['titre_seo'] = nettoyer_texte_ia(brief.get('titre_seo', ''), annee_courante)
    brief['meta_description'] = nettoyer_texte_ia(brief.get('meta_description', ''), annee_courante)
    print(f"  📝 Titre SEO : {brief.get('titre_seo')}")
    print(f"  🔑 Mot-clé retenu par le brief : {brief.get('mot_cle_principal')}")

    articles_silo = recuperer_articles_meme_sous_silo(silo, sous_silo, client_bq)
    if not articles_silo:
        articles_silo = recuperer_articles_meme_silo(silo, WP_CONFIG)

    contenu_html, erreur = rediger_article(brief, CONFIG, articles_silo, client_bq)
    if erreur:
        print(f"  ❌ Rédaction : {erreur}")
        return None

    contenu_html = inserer_lien_pilier(contenu_html, silo, sous_silo)

    nb_mots = len(re.sub(r'<[^>]+>', '', contenu_html).split())
    liens = re.findall(r'<a href="https://www\.comprendre-mon-energie\.fr[^"]*"', contenu_html)
    a_lien_pilier = (silo, sous_silo) in LIENS_PILIERS_SOUS_SILO and (
        LIENS_PILIERS_SOUS_SILO[(silo, sous_silo)][0] in contenu_html
    )
    print(f"  📊 {nb_mots} mots | {len(liens)} lien(s) interne(s) | "
          f"lien pilier présent : {'✅' if a_lien_pilier else '❌'}")

    if not apply_mode:
        print("  🔍 [DRY-RUN] Article généré mais NON publié -- relancer avec --apply pour publier.")
        apercu = re.sub(r'<[^>]+>', ' ', contenu_html)
        apercu = re.sub(r'\s+', ' ', apercu).strip()[:400]
        print(f"  Aperçu texte : {apercu}...")
        return {"titre": brief.get('titre_seo'), "mot_cle": brief.get('mot_cle_principal'), "publie": False}

    resultat = publier_article(brief, silo, sous_silo, contenu_html, WP_CONFIG, client_bq, run_id, CONFIG)
    if resultat.get('success'):
        print(f"  ✅ Publié : {resultat.get('url')} (post_id={resultat.get('post_id')})")
        return {"titre": brief.get('titre_seo'), "mot_cle": brief.get('mot_cle_principal'),
                "publie": True, "url": resultat.get('url')}
    else:
        print(f"  ❌ Publication : {resultat.get('erreur')}")
        return None


def main():
    apply_mode = "--apply" in sys.argv
    limite = None
    sujet_unique = None
    for arg in sys.argv:
        if arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])
        if arg.startswith("--sujet="):
            sujet_unique = int(arg.split("=", 1)[1])  # 1-indexe

    print(f"{'='*70}")
    print(f"Mode : {'PUBLICATION RÉELLE (--apply)' if apply_mode else 'DRY-RUN (lecture/génération seule, rien n’est publié)'}")
    if limite:
        print(f"Limité aux {limite} premier(s) sujet(s) sur {len(SUJETS)}")
    print(f"{'='*70}")

    client_bq = init_bigquery()
    if apply_mode:
        creer_table_historique(client_bq)

    run_id = "solaire_transac_" + datetime.now().strftime("%Y%m%d_%H%M")

    if sujet_unique:
        sujets_a_traiter = [SUJETS[sujet_unique - 1]]
    else:
        sujets_a_traiter = SUJETS[:limite] if limite else SUJETS
    resultats = []
    for sujet in sujets_a_traiter:
        r = traiter_un_sujet(sujet, client_bq, apply_mode, run_id)
        if r:
            resultats.append(r)

    print(f"\n{'='*70}")
    print(f"BILAN : {len(resultats)}/{len(sujets_a_traiter)} article(s) généré(s) avec succès"
          + (f", {sum(1 for r in resultats if r.get('publie'))} publié(s)" if apply_mode else " (dry-run, rien publié)"))
    print(f"{'='*70}")
    for r in resultats:
        statut = f"→ {r.get('url')}" if r.get('publie') else "(non publié)"
        print(f"  - {r['titre']} [{r['mot_cle']}] {statut}")


if __name__ == "__main__":
    main()
