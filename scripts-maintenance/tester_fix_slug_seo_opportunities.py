"""
CME — Test des DEUX correctifs du 16/11/2026 (slug vs libelle affiche +
retrait de jours_depuis_pub>=30) dans selectionner_silos_a_traiter() :
rejoue EXACTEMENT la requete corrigee (celle commitee dans pipeline.py)
pour les 20 sous-silos du quota actuel, sans rien publier ni ecrire --
juste pour confirmer, avant le prochain run reel de
publication-quotidienne.yml, que les correctifs debloquent bien la
selection d'opportunites GSC la ou des donnees existent.

Bug 1 : seo_opportunities.sous_silo est stocke en SLUG (ex.
"bouteilles", "maprimerenov") par la vue, alors que
selectionner_silos_a_traiter() comparait jusqu'ici au libelle affiche
("Bouteilles", "MaPrimeRénov'") -- egalite stricte qui ne matchait
JAMAIS. Fix : to_slug(sous_silo_cible) utilise desormais pour le WHERE
sur seo_opportunities.sous_silo (le libelle affiche reste utilise pour
le SELECT et pour le filtre anti-doublon sur historique_publications,
qui stocke bien le libelle).

Bug 2 : jours_depuis_pub>=30 est calcule PAR SOUS-SILO ENTIER (derniere
publication sur tout le sous-silo), donc quasi toujours < 30 pour un
sous-silo publie en continu (1/jour ouvre) -- auto-contradictoire avec
la presence meme d'un sous-silo dans QUOTAS_SOUS_SILO. Decision
operateur (16/11) : retire entierement, la protection anti-doublon
restant assuree par (1) l'exclusion exacte par mot-cle (90 jours,
ci-dessous) et (2) verifier_et_differencier_sujet() en aval (comparaison
semantique LLM, deja eprouvee).

Avec les deux correctifs appliques, ce script devrait montrer un
resultat tres different du premier test (0/20) : la plupart des
sous-silos ayant des donnees GSC devraient desormais trouver une vraie
opportunite.

Lecture seule -- ne touche ni WordPress ni historique_publications.
"""
import re
import sys
from datetime import datetime, timedelta

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"
FENETRE_ANTI_DOUBLON_JOURS = 90

QUOTAS_SOUS_SILO = [
    ("1. Gaz", "Bouteilles", 1), ("1. Gaz", "Facture Gaz", 1), ("1. Gaz", "Compteur gaz", 1),
    ("1. Gaz", "Contrat Gaz", 1), ("1. Gaz", "Chauffage Gaz", 1), ("1. Gaz", "Déménagement gaz", 1),
    ("5. Électricité", "Contrat Électricité", 1), ("5. Électricité", "Facture Électricité", 1),
    ("5. Électricité", "Compteur", 1), ("5. Électricité", "Chauffage Électricité", 1),
    ("5. Électricité", "Déménagement", 1),
    ("3. Aide Énergétique", "MaPrimeRénov'", 1), ("3. Aide Énergétique", "Chèque énergie", 1),
    ("3. Aide Énergétique", "Aide pompe à chaleur", 1), ("3. Aide Énergétique", "Aide isolation", 1),
    ("4. Solaire", "Kit solaire", 1), ("4. Solaire", "Panneaux solaires", 1),
    ("4. Solaire", "Batterie panneaux solaires", 1), ("4. Solaire", "Système solaire combiné", 1),
    ("4. Solaire", "Chauffe-eau solaire", 1),
]


def to_slug(texte):
    texte = texte.lower()
    for a, b in [('à', 'a'), ('â', 'a'), ('é', 'e'), ('è', 'e'), ('ê', 'e'),
                 ('î', 'i'), ('ô', 'o'), ('ù', 'u'), ('û', 'u'), ('ç', 'c'),
                 ("'", ""), ("'", "")]:
        texte = texte.replace(a, b)
    texte = re.sub(r'[^a-z0-9-]', '-', texte)
    texte = re.sub(r'-+', '-', texte).strip('-')
    return texte


def esc(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def main():
    client = bigquery.Client(project=PROJECT_ID)
    date_limite_rotation = (datetime.now() - timedelta(days=FENETRE_ANTI_DOUBLON_JOURS)).strftime('%Y-%m-%d')

    nb_trouves_total = 0
    nb_fallback_total = 0

    print(f"{'='*100}")
    print("REJEU DE LA REQUETE CORRIGEE (apres to_slug) POUR LES 20 SOUS-SILOS DU QUOTA")
    print(f"{'='*100}")

    for silo, sous_silo, quota in QUOTAS_SOUS_SILO:
        silo_safe = esc(silo)
        sous_silo_safe = esc(sous_silo)
        sous_silo_slug_safe = esc(to_slug(sous_silo))
        try:
            df = client.query(f"""
                SELECT query AS mot_cle, score_opportunite, ROUND(position, 1) AS position,
                       impressions, jours_depuis_pub
                FROM `{PROJECT_ID}.03_final.seo_opportunities`
                WHERE silo = '{silo_safe}' AND sous_silo = '{sous_silo_slug_safe}'
                  AND LOWER(query) NOT IN (
                      SELECT LOWER(mot_cle)
                      FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
                      WHERE sous_silo_strategique LIKE '{sous_silo_safe}%'
                        AND date_publication >= '{date_limite_rotation}'
                        AND mot_cle IS NOT NULL AND mot_cle != ''
                  )
                ORDER BY score_opportunite DESC
                LIMIT {quota}
            """).to_dataframe()
        except Exception as e:
            print(f"  ❌ {silo:<22} {sous_silo:<28} erreur : {e}")
            continue

        if df.empty:
            print(f"  ⚠️ {silo:<22} {sous_silo:<28} slug={to_slug(sous_silo):<35} "
                  f"-> toujours 0 opportunite (fallback anciennete inchange)")
            nb_fallback_total += 1
        else:
            row = df.iloc[0]
            print(f"  ✅ {silo:<22} {sous_silo:<28} slug={to_slug(sous_silo):<35} "
                  f"-> '{row['mot_cle']}' (pos {row['position']}, impr. {int(row['impressions'])}, "
                  f"score {row['score_opportunite']:.0f}, pub. il y a {int(row['jours_depuis_pub'])}j)")
            nb_trouves_total += 1

    print(f"\n{'='*100}")
    print(f"BILAN : {nb_trouves_total}/20 sous-silos trouveraient desormais une opportunite GSC reelle "
          f"(contre 0/20 avant le correctif), {nb_fallback_total}/20 resteraient en fallback anciennete.")
    print(f"{'='*100}")


if __name__ == "__main__":
    main()
