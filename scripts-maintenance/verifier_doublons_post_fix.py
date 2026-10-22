"""
CME — Verification en conditions reelles du correctif anti-doublon
(commit 9e88067, deploye le 20/10/2026) sur les publications reelles des
jours suivants.

LECTURE SEULE -- ne modifie rien. Deux controles complementaires sur
`historique_publications` pour la fenetre [2026-10-20 00:00 UTC, maintenant[ :

1. Meme symptome que le root cause n.1 (publier_actualites_reglementaires) :
   plusieurs articles publies le MEME jour pour le MEME sous-silo. Avant le
   correctif, le cas le plus flagrant etait 10 articles en 3 minutes sur un
   seul sous-silo (27/08). Si le correctif tient, on ne devrait plus voir
   cette signature.

2. Meme symptome que le root cause n.2 (selectionner_silos_a_traiter) :
   un meme mot-cle (ou un mot-cle tres proche, meme debut de chaine)
   republie pour un sous-silo ou il a deja ete traite dans les 90 derniers
   jours. verifier_doublons() devrait desormais l'avoir bloque en amont --
   donc aucune ligne ne devrait apparaitre ici si le correctif fonctionne.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

FENETRE_DEBUT = "2026-10-20T00:00:00Z"


def main():
    client_bq = init_bigquery()

    print("=" * 70)
    print(f"1. Publications multiples le meme jour pour le meme sous-silo")
    print(f"   depuis {FENETRE_DEBUT} (signature du root cause #1 -- Mode Actualite)")
    print("=" * 70)
    try:
        df1 = client_bq.query(f"""
            SELECT
                DATE(date_publication) AS jour,
                sous_silo_strategique,
                COUNT(*) AS nb_articles,
                STRING_AGG(mot_cle, ' | ' ORDER BY date_publication LIMIT 10) AS mots_cles
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE date_publication >= '{FENETRE_DEBUT}'
            GROUP BY jour, sous_silo_strategique
            HAVING nb_articles > 1
            ORDER BY nb_articles DESC, jour DESC
        """).to_dataframe()
        if df1.empty:
            print("   ✅ Aucun sous-silo avec plus d'un article publie le meme jour.")
        else:
            print(f"   ⚠️ {len(df1)} cas de publications multiples le meme jour / meme sous-silo :")
            print(df1.to_string())
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")

    print("\n" + "=" * 70)
    print("2. Mots-cles re-publies pour un sous-silo deja traite dans les 90j")
    print(f"   (signature du root cause #2 -- selectionner_silos_a_traiter)")
    print("   Compare chaque publication depuis le 20/10 a tout ce qui existait")
    print("   AVANT elle dans la fenetre anti-doublon de 90 jours pour le meme")
    print("   sous-silo (prefixe, pour couvrir le suffixage anti-collision).")
    print("=" * 70)
    try:
        df2 = client_bq.query(f"""
            SELECT
                h1.date_publication AS date_nouvelle,
                h1.sous_silo_strategique,
                h1.mot_cle AS mot_cle_nouveau,
                h2.date_publication AS date_precedente,
                h2.mot_cle AS mot_cle_precedent
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications` h1
            JOIN `{PROJECT_ID}.{DATASET_ID}.historique_publications` h2
              ON LOWER(h1.mot_cle) = LOWER(h2.mot_cle)
              AND SPLIT(h1.sous_silo_strategique, ' (')[OFFSET(0)]
                = SPLIT(h2.sous_silo_strategique, ' (')[OFFSET(0)]
              AND h2.date_publication < h1.date_publication
              AND h2.date_publication >= TIMESTAMP_SUB(h1.date_publication, INTERVAL 90 DAY)
            WHERE h1.date_publication >= '{FENETRE_DEBUT}'
            ORDER BY h1.date_publication DESC
        """).to_dataframe()
        if df2.empty:
            print("   ✅ Aucun mot-cle republie pour un sous-silo deja couvert dans les 90j.")
        else:
            print(f"   ⚠️ {len(df2)} cas de mot-cle republie malgre la fenetre anti-doublon :")
            print(df2.to_string())
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")

    print("\n" + "=" * 70)
    print("3. Volume publie depuis le 20/10 (pour contexte -- confirme que le")
    print("   pipeline a bien continue a publier, pas juste qu'il n'y a rien)")
    print("=" * 70)
    try:
        df3 = client_bq.query(f"""
            SELECT DATE(date_publication) AS jour, COUNT(*) AS nb_articles
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE date_publication >= '{FENETRE_DEBUT}'
            GROUP BY jour
            ORDER BY jour
        """).to_dataframe()
        print(df3.to_string() if not df3.empty else "   (0 publication depuis le 20/10 -- a investiguer si inattendu)")
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")


if __name__ == "__main__":
    main()
