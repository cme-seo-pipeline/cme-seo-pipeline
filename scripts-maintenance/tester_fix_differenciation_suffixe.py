"""
CME — Test du correctif de verifier_et_differencier_sujet() (22/10/2026,
voir CLAUDE.md "Duplication editoriale -- suite").

Bug corrige : la fonction filtrait historique_publications sur le
sous-silo SUFFIXE (' (2)', ' (3)'...) recu pour l'occurrence 2+ d'un
sous-silo a quota > 1, alors que ce suffixe n'est JAMAIS stocke dans
historique_publications (toujours retire avant publication). Resultat :
pour toute occurrence >= 2, la requete ne trouvait JAMAIS aucune ligne --
ni l'historique des jours precedents, ni le "jumeau" occurrence 1 publie
quelques secondes plus tot dans le MEME run -- rendant la fonction un
no-op silencieux exactement quand le risque de doublon est le plus eleve.

LECTURE SEULE -- n'appelle jamais l'API Anthropic pour rediger un vrai
article ni ne publie rien sur WordPress. Simule le cas reel observe en
prod le 20/10/2026 (cluster "MaPrimeRénov' vs autres aides", 2 articles
quasi-identiques publies a 83 secondes d'intervalle) : appelle la
fonction corrigee avec sous_silo SUFFIXE (comme le vit l'occurrence 2 en
prod) et un brief delibermment quasi-identique a l'occurrence 1 reelle
deja en base, puis verifie qu'elle detecte bien le chevauchement et
renvoie un titre/mot-cle differents de ceux proposes en entree (avant le
correctif, la fonction aurait renvoye le brief parfaitement inchange,
faute d'avoir trouve la moindre ligne correspondante).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import init_bigquery, verifier_et_differencier_sujet
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")


def main():
    client_bq = init_bigquery()

    print("=" * 70)
    print("Cas reel : occurrence 1 'MaPrimeRénov'' deja publiee le 20/10/2026")
    print("08:24:16 -- titre='MaPrimeRénov' vs autres aides : quel dispositif")
    print("choisir', mot_cle='MaPrimeRénov' vs autres aides'.")
    print("Simule l'occurrence 2 (sous_silo SUFFIXE, comme recu en prod)")
    print("proposant un brief quasi-identique.")
    print("=" * 70)

    brief_propose = {
        "titre_seo": "MaPrimeRénov' vs autres aides : lequel choisir pour vos travaux",
        "mot_cle_principal": "MaPrimeRénov' vs autres aides",
    }
    sous_silo_suffixe = "MaPrimeRénov' (2)"  # tel que recu par l'occurrence 2 en prod

    brief_resultat = verifier_et_differencier_sujet(
        dict(brief_propose), "3. Aide Énergétique", sous_silo_suffixe, client_bq, {}
    )

    print(f"\nTitre propose   : {brief_propose['titre_seo']!r}")
    print(f"Titre renvoye   : {brief_resultat.get('titre_seo')!r}")
    print(f"Mot-cle propose : {brief_propose['mot_cle_principal']!r}")
    print(f"Mot-cle renvoye : {brief_resultat.get('mot_cle_principal')!r}")

    titre_change = brief_resultat.get('titre_seo') != brief_propose['titre_seo']
    mot_cle_change = brief_resultat.get('mot_cle_principal') != brief_propose['mot_cle_principal']

    if titre_change or mot_cle_change:
        print("\n✅ Chevauchement detecte et brief differencie -- le correctif fonctionne "
              "(avant le correctif, la fonction n'aurait trouve aucune ligne pour ce "
              "sous-silo suffixe et aurait renvoye le brief absolument inchange).")
    else:
        print("\n❌ INATTENDU : le brief est revenu inchange -- soit la fonction n'a "
              "toujours trouve aucune ligne existante (correctif inefficace), soit le "
              "modele a juge (a tort) qu'il n'y avait pas de chevauchement.")


if __name__ == "__main__":
    main()
