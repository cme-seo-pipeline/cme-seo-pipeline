"""
CME — Inspection ponctuelle des tables BigQuery utiles au chantier
"SEO technique delegue" (cannibalisation par requete GSC + audit liens).

Script de LECTURE SEULE (aucune ecriture). Affiche le schema et quelques
lignes d'exemple de :
- 01_raw.gsc_queries      (donnees brutes Search Console, sync quotidien)
- 03_final.seo_opportunities (vue scoree existante, voir si elle a deja
  les colonnes necessaires pour la detection de cannibalisation)
- 02_cleaned.wp_url_mapping (liste des 437 URLs connues du site)

Objectif : savoir exactement avec quelles colonnes construire la requete
de detection de cannibalisation, sans deviner le schema.

Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement (fourni par
le workflow GitHub Actions "maintenance-a-la-demande").
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant (devrait etre dans pipeline/requirements.txt)")

PROJECT_ID = "seo-data-hub-cme"

TABLES = [
    "01_raw.gsc_queries",
    "03_final.seo_opportunities",
    "02_cleaned.wp_url_mapping",
]


def main():
    client = bigquery.Client(project=PROJECT_ID)

    for table_name in TABLES:
        print(f"\n{'='*70}")
        print(f"TABLE : {table_name}")
        print(f"{'='*70}")
        try:
            table_ref = f"{PROJECT_ID}.{table_name}"
            table = client.get_table(table_ref)
            print(f"Nombre de lignes (estimation) : {table.num_rows}")
            print("Colonnes :")
            for field in table.schema:
                print(f"  - {field.name} ({field.field_type})")

            print("\nExemple (3 lignes) :")
            rows = client.query(f"SELECT * FROM `{table_ref}` LIMIT 3").to_dataframe()
            print(rows.to_string())
        except Exception as e:
            print(f"⚠️ Erreur sur {table_name} : {e}")

    # Question specifique : combien de requetes GSC ont plusieurs URLs
    # distinctes qui se partagent des clics/impressions -- juste un ordre
    # de grandeur avant de construire la vraie requete de detection.
    print(f"\n{'='*70}")
    print("APERCU — requetes GSC couvertes par plusieurs URLs du site")
    print(f"{'='*70}")
    try:
        apercu = client.query(f"""
            SELECT query, COUNT(DISTINCT url) AS nb_urls_distinctes,
                   SUM(impressions) AS impressions_totales,
                   SUM(clicks) AS clics_totaux
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            GROUP BY query
            HAVING nb_urls_distinctes > 1
            ORDER BY impressions_totales DESC
            LIMIT 20
        """).to_dataframe()
        print(apercu.to_string())
    except Exception as e:
        print(f"⚠️ Erreur sur l'apercu cannibalisation : {e}")


if __name__ == "__main__":
    main()
