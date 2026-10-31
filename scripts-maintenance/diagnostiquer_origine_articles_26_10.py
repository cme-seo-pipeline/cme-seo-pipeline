"""
CME — Suite du diagnostic du 31/10/2026 : le diagnostic precedent
(diagnostiquer_echecs_24_26_10.py) a trouve 10 articles publies le 26/10
avec image_id renseignee, et en a deduit que l'echec du run
publication-quotidienne.yml de ce jour (08:15 UTC, failure confirme via
`gh run list`) etait survenu APRES generer_featured_images(). Mais les
horodatages reels de ces 10 publications (16:20-16:38 UTC) ne correspondent
PAS au run quotidien (08:15 UTC) ni au run sync-indicateurs.yml du jour
(09:41 UTC) -- ils correspondent en revanche exactement a une sequence de
runs `maintenance-a-la-demande.yml` (15:29-16:59 UTC) deja documentee ce
jour-la (debogage de recuperer_articles_meme_sous_silo()).

Ce script verifie la vraie origine de ces 10 articles (type_publication,
titres, post_id) avant de conclure quoi que ce soit sur le point de panne
du run quotidien du 26/10.

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

    df = client_bq.query(f"""
        SELECT post_id, date_publication, silo, sous_silo_strategique,
               titre, mot_cle, image_id, type_publication, run_id
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE DATE(date_publication) = '2026-10-26'
        ORDER BY date_publication
    """).to_dataframe()

    print(f"{len(df)} article(s) le 2026-10-26 :\n")
    for _, r in df.iterrows():
        print(f"  post_id={r['post_id']} | {r['date_publication']} | "
              f"type_publication={r['type_publication']!r} | run_id={r['run_id']!r}")
        print(f"      titre={r['titre'][:80]!r}")
        print(f"      silo={r['silo']} | sous_silo={r['sous_silo_strategique']} | mot_cle={r['mot_cle']}")
        print()

    # Distribution des run_id pour ce jour -- un seul run_id attendu si ces
    # 10 articles viennent effectivement du run quotidien du 08:15 UTC.
    print("Repartition par run_id :")
    print(df['run_id'].value_counts())
    print()
    print("Repartition par type_publication :")
    print(df['type_publication'].value_counts(dropna=False))


if __name__ == "__main__":
    main()
