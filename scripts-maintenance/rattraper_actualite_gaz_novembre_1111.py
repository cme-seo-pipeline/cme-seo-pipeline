"""
CME — Rattrapage de l'actualite "Facture Gaz : hausse de 5.8% en novembre
2026", detectee le 10/11/2026 et bloquee a tort par le bug de
verifier_doublons() corrige dans ce meme commit (voir pipeline.py).

Le changement n'est plus visible dans vue_changements_indicateurs
aujourd'hui (la valeur s'est stabilisee depuis le 10/11, donc la vue ne
voit plus de transition "aujourd'hui vs hier") -- ce script reconstruit
manuellement le "changement" tel que la vue l'aurait retourne ce jour-la
(valeurs confirmees par auditer_actualites_manquees_1111.py), puis
rejoue EXACTEMENT le meme chemin que publier_actualites_reglementaires()
pour ce changement precis : construire_brief_actualite() -> verifier_
doublons() (avec le correctif -- doit desormais laisser passer) ->
rediger_article() -> valider_et_nettoyer_liens_internes() -> publier_
article() -> marquage type_publication='actualite' -> schemas/images/
notification, comme un run normal.

ECRITURE REELLE : publie un article WordPress reel si tout se deroule
normalement. Demande explicite de l'operateur le 11/11/2026
("corriger le bug ET publier l'article manque").
"""
import os
import re
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

from pipeline import (
    CONFIG, WP_CONFIG, PROJECT_ID, DATASET_ID,
    init_bigquery, construire_brief_actualite, verifier_doublons,
    rediger_article, valider_et_nettoyer_liens_internes, publier_article,
    nettoyer_et_generer_schemas, generer_featured_images, notifier_nouveaux_articles,
)


def main():
    client_bq = init_bigquery()
    run_id = datetime.now().strftime("%Y%m%d_%H%M")

    valeur_precedente = 194.90053865300212
    valeur_actuelle = 206.25603666147236
    variation_pct = round((valeur_actuelle - valeur_precedente) / valeur_precedente * 100, 2)

    changement = {
        "domaine": "Gaz",
        "indicateur": "PRVG_moyen_TTC",
        "sous_categorie": None,
        "valeur_precedente": valeur_precedente,
        "valeur_actuelle": valeur_actuelle,
        "unite": "€/MWh",
        "variation_pct": variation_pct,
        "date_debut_validite": "2026-12-01",
        "date_verification": "2026-11-10",
    }
    print(f"Changement reconstruit : {changement}")

    brief = construire_brief_actualite(changement, client_bq)
    if not brief:
        print("❌ Pas de silo mappe pour PRVG_moyen_TTC -- impossible de continuer")
        sys.exit(1)
    print(f"✍️ Brief construit : {brief['titre_seo']}")

    if verifier_doublons(brief['titre_seo'], brief['mot_cle_principal'], client_bq, CONFIG):
        print("⏭️ verifier_doublons() dit encore 'doublon' -- le correctif n'a pas eu l'effet attendu, ARRET (pas de publication)")
        sys.exit(1)
    print("✅ verifier_doublons() : pas de doublon, le correctif fonctionne -- on continue")

    contenu_html, erreur = rediger_article(brief, CONFIG, None, client_bq)
    if erreur:
        print(f"❌ Erreur redaction : {erreur}")
        sys.exit(1)
    print(f"✅ Article redige ({len(contenu_html)} caracteres HTML)")

    contenu_html, nb_liens_retires = valider_et_nettoyer_liens_internes(contenu_html)
    if nb_liens_retires:
        print(f"🧹 {nb_liens_retires} lien(s) interne(s) mort(s) retire(s) avant publication")

    resultat = publier_article(
        brief, brief['silo'], brief['sous_silo'], contenu_html,
        WP_CONFIG, client_bq, run_id, CONFIG
    )
    if not resultat['success']:
        print(f"❌ Erreur publication : {resultat.get('erreur')}")
        sys.exit(1)
    print(f"✅ ARTICLE PUBLIE : {resultat['url']} (post_id={resultat['post_id']})")

    try:
        client_bq.query(f"""
        UPDATE `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        SET type_publication = 'actualite'
        WHERE post_id = {resultat['post_id']}
        """).result()
        print("✅ type_publication marque 'actualite'")
    except Exception as e:
        print(f"⚠️ Erreur marquage type_publication : {e}")

    nb_mots = len(re.sub(r'<[^>]+>', '', contenu_html).split())
    df_publications = pd.DataFrame([{
        "Silo": brief['silo'],
        "Titre": brief['titre_seo'],
        "Mot_cle": brief['mot_cle_principal'],
        "Nb_mots": nb_mots,
        "Post_ID": resultat['post_id'],
        "URL_WP": resultat['url'],
        "Statut": "publish",
        "Contenu_HTML": contenu_html,
        "sous_silo": brief['sous_silo'],
    }])

    try:
        nettoyer_et_generer_schemas(df_publications, WP_CONFIG, CONFIG)
        print("✅ Schemas generes")
    except Exception as e:
        print(f"⚠️ Erreur schemas : {e}")

    try:
        from pipeline import OPENAI_CONFIG
        generer_featured_images(df_publications, client_bq, CONFIG, OPENAI_CONFIG, WP_CONFIG)
        print("✅ Image mise en avant generee")
    except Exception as e:
        print(f"⚠️ Erreur image mise en avant : {e}")

    try:
        notifier_nouveaux_articles(df_publications, CONFIG)
        print("✅ Notification envoyee")
    except Exception as e:
        print(f"⚠️ Erreur notification : {e}")

    print(f"\n🎉 RATTRAPAGE TERMINE : {resultat['url']}")


if __name__ == "__main__":
    main()
