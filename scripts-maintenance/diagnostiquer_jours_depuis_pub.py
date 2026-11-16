"""
CME — Diagnostic (16/11/2026, suite) : meme avec le mismatch slug/libelle
corrige, la requete complete reste a 0/20 (voir
tester_fix_slug_seo_opportunities.py). Hypothese testee ici : le filtre
`jours_depuis_pub >= 30` (jours depuis la DERNIERE publication sur CE
sous-silo, colonne calculee par sous-silo dans la vue, pas par article)
est structurellement quasi-toujours faux pour un sous-silo publie a
cadence reguliere (1/jour ouvre pour la plupart des 20 sous-silos
actuels) -- sa derniere publication a presque toujours moins de 30 jours,
puisqu'elle est republiee en continu.

Verifie la distribution reelle de jours_depuis_pub pour les quelques
sous-silos ou le slug matche (bouteilles, maprimerenov, etc.).

Lecture seule.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"

SLUGS_A_VERIFIER = [
    ("1. Gaz", "bouteilles"),
    ("1. Gaz", "contrat-gaz"),
    ("1. Gaz", "facture-gaz"),
    ("1. Gaz", "demenagement-gaz"),
    ("5. Électricité", "facture-electricite"),
    ("5. Électricité", "contrat-electricite"),
    ("5. Électricité", "compteur"),
    ("5. Électricité", "chauffage-electricite"),
    ("5. Électricité", "demenagement"),
    ("3. Aide Énergétique", "maprimerenov"),
    ("3. Aide Énergétique", "cheque-energie"),
    ("4. Solaire", "panneaux-solaires"),
    ("4. Solaire", "chauffe-eau-solaire"),
    ("4. Solaire", "systeme-solaire-combine"),
    ("4. Solaire", "kit-solaire"),
    ("4. Solaire", "batterie-panneaux-solaires"),
]


def esc(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print(f"{'='*105}")
    print("DISTRIBUTION DE jours_depuis_pub PAR (silo, sous_silo SLUG) -- pour les slugs qui matchent reellement")
    print(f"{'='*105}")
    for silo, slug in SLUGS_A_VERIFIER:
        silo_safe, slug_safe = esc(silo), esc(slug)
        try:
            df = client.query(f"""
                SELECT
                    COUNT(*) AS total_lignes,
                    MIN(jours_depuis_pub) AS min_jours,
                    MAX(jours_depuis_pub) AS max_jours,
                    APPROX_QUANTILES(jours_depuis_pub, 2)[OFFSET(1)] AS mediane_jours,
                    COUNTIF(jours_depuis_pub >= 30) AS nb_avec_30j_ou_plus,
                    ANY_VALUE(derniere_pub) AS derniere_pub_exemple
                FROM `{PROJECT_ID}.03_final.seo_opportunities`
                WHERE silo = '{silo_safe}' AND sous_silo = '{slug_safe}'
            """).to_dataframe()
            row = df.iloc[0]
            print(f"  {silo:<22} {slug:<35} total={int(row['total_lignes']):<5} "
                  f"min_j={row['min_jours']:<6} mediane_j={row['mediane_jours']:<8} max_j={row['max_jours']:<6} "
                  f"nb_avec_30j_ou_plus={int(row['nb_avec_30j_ou_plus']):<4} derniere_pub={row['derniere_pub_exemple']}")
        except Exception as e:
            print(f"  {silo:<22} {slug:<35} ❌ erreur : {e}")


if __name__ == "__main__":
    main()
