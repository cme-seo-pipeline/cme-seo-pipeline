"""
CME — Complement de diagnostic (lecture seule) a
verifier_doublons_post_fix.py : celui-ci a montre des `mot_cle` exactement
identiques republies plusieurs fois depuis le 20/10 pour les memes
sous-silos. Avant de conclure que le correctif anti-doublon est inefficace,
il faut verifier si les TITRES (`titre`) different reellement malgre un
mot_cle identique -- cas possible si verifier_et_differencier_sujet()
(qui ne modifie QUE titre_seo, jamais mot_cle_principal, voir
pipeline/pipeline.py) a bien differencie le titre mais laisse le mot-cle
cible identique (cannibalisation SEO, pas duplication de contenu au sens
strict de CLAUDE.md "Duplication editoriale").

Affiche titre + mot_cle + date pour chaque sous-silo cible depuis le
20/10, dans l'ordre chronologique, pour inspection visuelle directe.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

FENETRE_DEBUT = "2026-10-20T00:00:00Z"
SOUS_SILOS = [
    "Bouteilles", "Facture Gaz", "Contrat Électricité", "Facture Électricité",
    "MaPrimeRénov'", "Chèque énergie", "Aides chauffe-eau thermodynamique",
]


def main():
    client_bq = init_bigquery()
    for sous_silo in SOUS_SILOS:
        sous_silo_safe = sous_silo.replace("'", "\\'")
        print("=" * 70)
        print(f"Sous-silo : {sous_silo}")
        print("=" * 70)
        try:
            df = client_bq.query(f"""
                SELECT date_publication, titre, mot_cle, sous_silo_strategique
                FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
                WHERE sous_silo_strategique LIKE '{sous_silo_safe}%'
                  AND date_publication >= '{FENETRE_DEBUT}'
                ORDER BY date_publication
            """).to_dataframe()
            if df.empty:
                print("   (rien depuis le 20/10 pour ce sous-silo)")
            else:
                for _, r in df.iterrows():
                    print(f"   {r['date_publication']} | [{r['sous_silo_strategique']}] | mot_cle='{r['mot_cle']}'")
                    print(f"      titre = {r['titre']!r}")
        except Exception as e:
            print(f"   ❌ Erreur SQL : {e}")
        print()


if __name__ == "__main__":
    main()
