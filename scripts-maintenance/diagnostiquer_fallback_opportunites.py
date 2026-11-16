"""
CME — Diagnostic (16/11/2026) : pourquoi `selectionner_silos_a_traiter()`
tombe en "fallback anciennete" pour TOUS les sous-silos, tous les jours,
depuis au moins le 31/10/2026 (confirme en relisant 6 runs de
`publication-quotidienne.yml` espaces sur 17 jours -- 0 "trouve via SEO"
a chaque fois, quelle que soit la configuration de quota).

Le selecteur interroge la vue `03_final.seo_opportunities`
(scripts-maintenance/fix_seo_opportunities_postid.sh) avec :
  WHERE silo = X AND sous_silo = Y AND jours_depuis_pub >= 30
    AND query NOT IN (deja publie sur ce sous-silo, 90 derniers jours)
  ORDER BY score_opportunite DESC LIMIT quota

Et la vue elle-meme filtre en amont sur `01_raw.gsc_queries` :
  WHERE date >= 30 derniers jours AND position BETWEEN 5 AND 42
    AND impressions > 5

Ce script isole, pour chaque sous-silo du quota actuel, OU exactement le
funnel casse : (a) aucune ligne GSC ne matche le silo/sous-silo meme
sans aucun filtre de date/position, (b) des lignes existent mais aucune
dans la fenetre position 5-42 + impressions>5, (c) des lignes passent ce
filtre mais jours_depuis_pub<30, ou (d) tout passe mais l'exclusion
anti-doublon (deja publie) vide le reste.

Lecture seule.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"

QUOTAS_SOUS_SILO = [
    ("1. Gaz", "Bouteilles"), ("1. Gaz", "Facture Gaz"), ("1. Gaz", "Compteur gaz"),
    ("1. Gaz", "Contrat Gaz"), ("1. Gaz", "Chauffage Gaz"), ("1. Gaz", "Déménagement gaz"),
    ("5. Électricité", "Contrat Électricité"), ("5. Électricité", "Facture Électricité"),
    ("5. Électricité", "Compteur"), ("5. Électricité", "Chauffage Électricité"),
    ("5. Électricité", "Déménagement"),
    ("3. Aide Énergétique", "MaPrimeRénov'"), ("3. Aide Énergétique", "Chèque énergie"),
    ("3. Aide Énergétique", "Aide pompe à chaleur"), ("3. Aide Énergétique", "Aide isolation"),
    ("4. Solaire", "Kit solaire"), ("4. Solaire", "Panneaux solaires"),
    ("4. Solaire", "Batterie panneaux solaires"), ("4. Solaire", "Système solaire combiné"),
    ("4. Solaire", "Chauffe-eau solaire"),
]


def esc(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def main():
    client = bigquery.Client(project=PROJECT_ID)

    # 0) La vue existe-t-elle, a-t-elle des lignes DU TOUT, et sur quelle
    #    plage de dates GSC repose-t-elle reellement en ce moment ?
    print(f"{'='*95}")
    print("ETAT GLOBAL DE LA VUE seo_opportunities ET DE SA SOURCE gsc_queries")
    print(f"{'='*95}")
    try:
        df_total = client.query(f"""
            SELECT COUNT(*) AS lignes, COUNT(DISTINCT silo) AS silos_distincts,
                   MIN(jours_depuis_pub) AS min_jours, MAX(jours_depuis_pub) AS max_jours
            FROM `{PROJECT_ID}.03_final.seo_opportunities`
        """).to_dataframe()
        print(df_total.to_string(index=False))
    except Exception as e:
        print(f"❌ Erreur lecture seo_opportunities : {e}")

    try:
        df_gsc_range = client.query(f"""
            SELECT MIN(date) AS date_min, MAX(date) AS date_max, COUNT(*) AS lignes
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
        """).to_dataframe()
        print("\nPlage de dates reelle de 01_raw.gsc_queries :")
        print(df_gsc_range.to_string(index=False))
    except Exception as e:
        print(f"❌ Erreur lecture gsc_queries : {e}")

    # 1) Distribution des silos TELS QU'ILS EXISTENT dans la vue (pour
    #    comparer aux libelles exacts utilises par QUOTAS_SOUS_SILO).
    print(f"\n{'='*95}")
    print("LIBELLES DE silo REELLEMENT PRESENTS DANS seo_opportunities")
    print(f"{'='*95}")
    try:
        df_silos = client.query(f"""
            SELECT silo, COUNT(*) AS lignes, COUNT(DISTINCT sous_silo) AS nb_sous_silo
            FROM `{PROJECT_ID}.03_final.seo_opportunities`
            GROUP BY silo ORDER BY lignes DESC
        """).to_dataframe()
        print(df_silos.to_string(index=False))
    except Exception as e:
        print(f"❌ Erreur : {e}")

    # 2) Funnel detaille par sous-silo cible du quota actuel.
    print(f"\n{'='*95}")
    print("FUNNEL PAR SOUS-SILO DU QUOTA ACTUEL (20 sous-silos)")
    print(f"{'='*95}")
    for silo, sous_silo in QUOTAS_SOUS_SILO:
        silo_safe, sous_silo_safe = esc(silo), esc(sous_silo)
        try:
            df = client.query(f"""
                SELECT
                    COUNT(*) AS total_lignes,
                    COUNTIF(jours_depuis_pub >= 30) AS avec_jours_ok,
                    MIN(jours_depuis_pub) AS min_jours_depuis_pub,
                    MAX(score_opportunite) AS meilleur_score
                FROM `{PROJECT_ID}.03_final.seo_opportunities`
                WHERE silo = '{silo_safe}' AND sous_silo = '{sous_silo_safe}'
            """).to_dataframe()
            row = df.iloc[0]
            print(f"  {silo:<25} {sous_silo:<30} "
                  f"lignes_vue={int(row['total_lignes']):<5} "
                  f"avec_jours_depuis_pub>=30={int(row['avec_jours_ok']):<5} "
                  f"min_jours_depuis_pub={row['min_jours_depuis_pub']}")
        except Exception as e:
            print(f"  {silo:<25} {sous_silo:<30} ❌ erreur : {e}")

    # 3) Pour le sous-silo le plus "rempli" (s'il y en a un), montrer ce
    #    qui bloque precisement (anti-doublon ou jours_depuis_pub).
    print(f"\n{'='*95}")
    print("ECHANTILLON BRUT (sans aucun filtre) POUR 3 SOUS-SILOS -- comprendre pourquoi jours_depuis_pub reste bas")
    print(f"{'='*95}")
    for silo, sous_silo in [("1. Gaz", "Bouteilles"), ("3. Aide Énergétique", "MaPrimeRénov'"),
                             ("4. Solaire", "Panneaux solaires")]:
        silo_safe, sous_silo_safe = esc(silo), esc(sous_silo)
        try:
            df = client.query(f"""
                SELECT query, position, impressions, score_opportunite,
                       derniere_pub, jours_depuis_pub
                FROM `{PROJECT_ID}.03_final.seo_opportunities`
                WHERE silo = '{silo_safe}' AND sous_silo = '{sous_silo_safe}'
                ORDER BY score_opportunite DESC
                LIMIT 5
            """).to_dataframe()
            print(f"\n  -- {silo} | {sous_silo} --")
            if df.empty:
                print("  (aucune ligne du tout dans la vue pour ce couple silo/sous_silo)")
            else:
                print(df.to_string(index=False))
        except Exception as e:
            print(f"  ❌ erreur : {e}")


if __name__ == "__main__":
    main()
