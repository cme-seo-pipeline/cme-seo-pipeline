"""
CME — Reponse a la question operateur du 31/10/2026 : l'audit mensuel
(audit-mensuel.yml, auditer_et_corriger_articles()) sollicite-t-il l'API
Claude, et si oui pour combien d'appels ? auditer_article() (confirme par
lecture du code) appelle bien api.anthropic.com/v1/messages, un appel par
article candidat. Ce script compte, en lecture seule, combien d'articles
seraient actuellement candidats pour le run du 1/11/2026 -- meme requete
que celle utilisee par auditer_et_corriger_articles(), sans appeler l'API
Claude ni rien modifier.

LECTURE SEULE.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")


def main():
    client_bq = init_bigquery()

    df_candidats = client_bq.query(f"""
        SELECT DISTINCT m.indicateur, h.post_id, h.titre, h.url_wp
        FROM `{PROJECT_ID}.{DATASET_ID}.mapping_indicateur_sous_silo` m
        JOIN `{PROJECT_ID}.{DATASET_ID}.historique_publications` h
            ON h.silo = m.silo AND h.sous_silo_strategique = m.sous_silo_strategique
        WHERE m.pertinence = 'directe'
    """).to_dataframe()

    print(f"Articles candidats a l'audit (pertinence='directe') : {len(df_candidats)}")
    print("Repartition par indicateur :")
    print(df_candidats['indicateur'].value_counts())
    print()
    print(f"-> auditer_et_corriger_articles() appellera donc l'API Claude "
          f"(modele Haiku) environ {len(df_candidats)} fois lors du prochain "
          f"run de audit-mensuel.yml (1 appel = 1 article candidat).")


if __name__ == "__main__":
    main()
