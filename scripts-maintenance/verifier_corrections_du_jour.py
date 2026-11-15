"""
CME — Detail des corrections reglementaires automatiques appliquees
AUJOURD'HUI (`corrections_articles_auto`, voir `appliquer_correction_article()`
dans pipeline.py), + verification qu'aucun nouvel article "actualite" n'a
ete publie aujourd'hui (Mode Actualite, `sync-indicateurs.yml`).

Demande operateur (15/11/2026) : etat des lieux du jour -- le log du run
`audit-mensuel.yml` de ce matin indique "476 article(s) audite(s), 7
corrige(s)" mais ne donne que les post_id, pas le detail (titre,
indicateur, passage change) -- ce script le recupere.

Lecture seule.
"""
import sys
from datetime import date

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"


def main():
    client = bigquery.Client(project=PROJECT_ID)
    aujourdhui = date.today().isoformat()

    print(f"🔎 Etat des lieux du {aujourdhui}\n")

    # 1) Corrections reglementaires appliquees aujourd'hui.
    query_corrections = f"""
        SELECT post_id, titre, indicateur, passage_avant, passage_apres,
               date_correction, url_wp
        FROM `{PROJECT_ID}.{DATASET_ID}.corrections_articles_auto`
        WHERE DATE(date_correction) = CURRENT_DATE()
        ORDER BY date_correction
    """
    try:
        df_corr = client.query(query_corrections).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery (corrections_articles_auto) : {e}")

    print(f"{'='*90}")
    print(f"CORRECTIONS REGLEMENTAIRES AUTOMATIQUES — {aujourdhui}")
    print(f"{'='*90}")
    if df_corr.empty:
        print("Aucune correction trouvee pour aujourd'hui dans corrections_articles_auto.")
    else:
        for _, row in df_corr.iterrows():
            print(f"\n  Post {row['post_id']} — {row['titre']}")
            print(f"    Indicateur : {row['indicateur']}")
            print(f"    URL : {row['url_wp']}")
            print(f"    Avant : {row['passage_avant']}")
            print(f"    Apres : {row['passage_apres']}")
        print(f"\nTotal : {len(df_corr)} correction(s) appliquee(s) aujourd'hui.")

    # 2) Nouveaux articles publies aujourd'hui (tous mecanismes confondus),
    #    pour confirmer/infirmer "rien a publier" du log Mode Actualite.
    query_pub = f"""
        SELECT post_id, titre, silo, sous_silo_strategique, url_wp, run_id, date_publication
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE DATE(date_publication) = CURRENT_DATE()
        ORDER BY date_publication
    """
    try:
        df_pub = client.query(query_pub).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery (historique_publications) : {e}")

    print(f"\n{'='*90}")
    print(f"NOUVEAUX ARTICLES PUBLIES — {aujourdhui}")
    print(f"{'='*90}")
    if df_pub.empty:
        print("Aucun nouvel article publie aujourd'hui (coherent avec "
              "publication-quotidienne.yml, Lun-Ven uniquement, et le log "
              "Mode Actualite 'Aucun changement detecte, rien a publier').")
    else:
        for _, row in df_pub.iterrows():
            print(f"\n  Post {row['post_id']} — {row['titre']}")
            print(f"    {row['silo']} / {row['sous_silo_strategique']}")
            print(f"    URL : {row['url_wp']}")
            print(f"    run_id : {row['run_id']}")
        print(f"\nTotal : {len(df_pub)} article(s) publie(s) aujourd'hui.")


if __name__ == "__main__":
    main()
