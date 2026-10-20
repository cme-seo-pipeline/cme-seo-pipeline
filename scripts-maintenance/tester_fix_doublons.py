"""
CME — Test du correctif anti-doublon (verifier_doublons + filtre SQL dans
selectionner_silos_a_traiter), avant de le laisser tourner sur un vrai run.

LECTURE SEULE -- ne publie rien, n'ecrit rien. Importe directement les
fonctions depuis pipeline/pipeline.py (le vrai code corrige, pas une copie)
pour tester exactement ce qui tournera demain.

1. verifier_doublons() : doit renvoyer True pour un titre qu'on sait deja
   publie recemment (ex. un des titres du cluster "Facture Electricite"
   trouve le 19/10), et False pour un titre clairement inedit.
2. La requete SQL modifiee de selectionner_silos_a_traiter (nouveau filtre
   NOT IN) : executee directement ici en lecture seule sur un sous-silo
   reel, pour confirmer qu'elle ne plante pas et exclut bien les mots-cles
   deja couverts.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import verifier_doublons, init_bigquery, CONFIG, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")


def main():
    client_bq = init_bigquery()

    print("=" * 70)
    print("1. verifier_doublons() -- cas connu (doit renvoyer True)")
    print("=" * 70)
    # Titre reel du cluster trouve le 19/10 (post_id=7029), toujours dans
    # la fenetre anti-doublon de 90 jours.
    titre_connu = "Facture Électricité : hausse de 3.0% en août 2026"
    resultat = verifier_doublons(titre_connu, "facture electricite aout 2026", client_bq, CONFIG)
    print(f"   Titre : {titre_connu!r}")
    print(f"   Resultat : {resultat} {'✅ attendu' if resultat else '❌ INATTENDU (devrait etre True)'}")

    print("\n" + "=" * 70)
    print("2. verifier_doublons() -- cas inedit (doit renvoyer False)")
    print("=" * 70)
    titre_inedit = f"Test diagnostic totalement inedit xyz-{os.urandom(4).hex()}"
    resultat2 = verifier_doublons(titre_inedit, f"motcle-inedit-{os.urandom(4).hex()}", client_bq, CONFIG)
    print(f"   Titre : {titre_inedit!r}")
    print(f"   Resultat : {resultat2} {'✅ attendu' if not resultat2 else '❌ INATTENDU (devrait etre False)'}")

    print("\n" + "=" * 70)
    print("3. Requete SQL corrigee de selectionner_silos_a_traiter (filtre NOT IN)")
    print("=" * 70)
    silo_safe = "5. Électricité"
    sous_silo_safe = "Facture Électricité"
    try:
        df_opp = client_bq.query(f"""
        SELECT
            '{silo_safe}' AS silo,
            '{sous_silo_safe}' AS sous_silo,
            query AS mot_cle,
            score_opportunite,
            ROUND(position, 1) AS position,
            impressions,
            jours_depuis_pub
        FROM `{PROJECT_ID}.03_final.seo_opportunities`
        WHERE silo = '{silo_safe}' AND sous_silo = '{sous_silo_safe}'
          AND jours_depuis_pub >= 30
          AND LOWER(query) NOT IN (
              SELECT LOWER(mot_cle)
              FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
              WHERE sous_silo_strategique LIKE '{sous_silo_safe}%'
                AND date_publication >= '2026-07-22'
                AND mot_cle IS NOT NULL AND mot_cle != ''
          )
        ORDER BY score_opportunite DESC
        LIMIT 5
        """).to_dataframe()
        print(f"   ✅ Requete executee sans erreur -- {len(df_opp)} ligne(s) retournee(s)")
        if not df_opp.empty:
            print(df_opp[['mot_cle', 'score_opportunite']].to_string())
        else:
            print("   (0 ligne -- soit aucune opportunite pour ce sous-silo, soit toutes deja exclues)")
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")

    print("\n" + "=" * 70)
    print("4. Meme requete SANS le filtre NOT IN (pour comparaison -- la table")
    print("   seo_opportunities a-t-elle seulement des lignes pour ce sous-silo ?)")
    print("=" * 70)
    try:
        df_sans_filtre = client_bq.query(f"""
        SELECT query AS mot_cle, score_opportunite
        FROM `{PROJECT_ID}.03_final.seo_opportunities`
        WHERE silo = '{silo_safe}' AND sous_silo = '{sous_silo_safe}'
          AND jours_depuis_pub >= 30
        ORDER BY score_opportunite DESC
        LIMIT 5
        """).to_dataframe()
        print(f"   {len(df_sans_filtre)} ligne(s) sans le filtre")
        if not df_sans_filtre.empty:
            print(df_sans_filtre.to_string())
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")

    print("\n" + "=" * 70)
    print("5. Contenu de la sous-requete d'exclusion (mots-cles deja publies)")
    print("=" * 70)
    try:
        df_exclus = client_bq.query(f"""
        SELECT LOWER(mot_cle) AS mot_cle, sous_silo_strategique, date_publication
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE sous_silo_strategique LIKE '{sous_silo_safe}%'
          AND date_publication >= '2026-07-22'
          AND mot_cle IS NOT NULL AND mot_cle != ''
        ORDER BY date_publication DESC
        LIMIT 10
        """).to_dataframe()
        print(f"   {len(df_exclus)} mot(s)-cle(s) deja publie(s) recemment pour ce sous-silo (exclus par le filtre)")
        if not df_exclus.empty:
            print(df_exclus.to_string())
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")


if __name__ == "__main__":
    main()
