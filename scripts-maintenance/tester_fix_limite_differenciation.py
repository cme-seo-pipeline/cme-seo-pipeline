"""
CME — Rejoue le correctif du 31/10/2026 de verifier_et_differencier_sujet()
(garde deterministe + echantillon LLM filtre par date plutot que par rang,
voir le commentaire dans pipeline.py et verifier_doublons_depuis_22_10.py)
contre un cas REEL de duplication trouve en prod, pour valider que le
correctif le bloque desormais.

Cas rejoue : post_id=11366, "Aides électricité 2026 : réductions et
chèques" (sous-silo Contrat Électricité, mot-cle "aides électricité 2026"),
publie le 23/10/2026 -- alors que ce meme mot-cle exact avait deja ete
publie le 31/08/2026 (post_id=7342) et le 02/10/2026 (post_id=9365), tous
deux a l'interieur de la fenetre anti-doublon de 90 jours mais hors des 15
articles les plus recents que la fonction pouvait voir avant le correctif.

Appelle la fonction REELLE (vrai appel BigQuery + vrai appel Anthropic) en
lui donnant le MEME brief que celui qui avait produit le doublon. Si le
correctif fonctionne, la fonction doit desormais detecter le chevauchement
et renvoyer un titre/mot-cle differents de l'original.

LECTURE SEULE cote BigQuery (aucune ecriture) -- un seul appel reel a
l'API Anthropic (meme cout qu'un run de production normal pour cette
etape).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import init_bigquery, verifier_et_differencier_sujet, CONFIG
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")


def main():
    client_bq = init_bigquery()

    # Brief reconstitue a l'identique du doublon reel publie le 23/10
    # (post_id=11366) -- meme titre, meme mot-cle exact.
    brief = {
        "titre_seo": "Aides électricité 2026 : réductions et chèques",
        "mot_cle_principal": "aides électricité 2026",
    }
    silo_name = "5. Électricité"
    sous_silo = "Contrat Électricité"

    print(f"Brief rejoue : {brief}")
    print(f"Silo : {silo_name} | Sous-silo : {sous_silo}")
    print("\n--- Appel de verifier_et_differencier_sujet() (code corrige) ---\n")

    resultat = verifier_et_differencier_sujet(brief, silo_name, sous_silo, client_bq, CONFIG)

    print("\n--- Resultat ---")
    print(f"Titre final     : {resultat.get('titre_seo')}")
    print(f"Mot-cle final   : {resultat.get('mot_cle_principal')}")

    titre_identique = resultat.get('titre_seo') == brief['titre_seo']
    mot_cle_identique = resultat.get('mot_cle_principal') == brief['mot_cle_principal']

    if titre_identique and mot_cle_identique:
        print("\n❌ ECHEC : le brief n'a PAS ete differencie -- le correctif ne fonctionne pas "
              "(ou le mot-cle a entre temps quitte la fenetre de 90 jours).")
        sys.exit(1)
    else:
        print("\n✅ SUCCES : le brief a bien ete differencie -- le doublon exact a ete detecte "
              "et un angle alternatif a ete propose. Le correctif fonctionne.")


if __name__ == "__main__":
    main()
