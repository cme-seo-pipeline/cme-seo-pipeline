"""
CME — Identification des pages a fort volume d'impressions mais faible CTR
(donnees Google Search Console, table 01_raw.gsc_queries synchronisee par
cme-gsc-to-bq.gs).

Objectif : ces pages sont deja vues souvent dans les resultats Google mais
convertissent mal cette visibilite en clics -- signal classique d'un
titre/meta-description a retravailler, ou d'un mauvais alignement entre
intention de recherche et contenu reel de la page. Priorite naturelle pour
une optimisation de CTR (titre_seo/meta_description), car l'effet potentiel
(impressions deja la) est plus eleve que sur une page a faible volume.

Methode : agrege par page sur la fenetre choisie (SUM impressions/clics,
PAS de moyenne de ctr brut -- recalcule depuis les sommes pour rester exact
meme si une page a plusieurs lignes/jours), isole le pool des pages a plus
fort volume (top --pool par impressions), puis classe ce pool par CTR
croissant et affiche les --limite premieres.

Lecture seule -- aucune ecriture, aucun --apply necessaire.

USAGE :
  python3 identifier_pages_fort_volume_faible_ctr.py
  python3 identifier_pages_fort_volume_faible_ctr.py --jours=90 --pool=30 --limite=5

Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def parse_args():
    jours = 90
    pool = 30
    limite = 5
    for arg in sys.argv:
        if arg.startswith("--jours="):
            jours = int(arg.split("=", 1)[1])
        elif arg.startswith("--pool="):
            pool = int(arg.split("=", 1)[1])
        elif arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])
    return jours, pool, limite


def main():
    jours, pool, limite = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print(f"🔎 Fenetre : {jours} derniers jours — pool fort volume : top {pool} pages "
          f"par impressions — on affiche les {limite} au CTR le plus faible dans ce pool\n")

    query = f"""
        WITH agrege AS (
            SELECT
                page,
                ANY_VALUE(silo) AS silo,
                ANY_VALUE(sous_silo) AS sous_silo,
                SUM(impressions) AS impressions,
                SUM(clics) AS clics,
                SAFE_DIVIDE(SUM(clics), SUM(impressions)) AS ctr,
                AVG(position) AS position_moyenne
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {jours} DAY)
            GROUP BY page
        ),
        pool_fort_volume AS (
            SELECT *
            FROM agrege
            ORDER BY impressions DESC
            LIMIT {pool}
        )
        SELECT *
        FROM pool_fort_volume
        ORDER BY ctr ASC
        LIMIT {limite}
    """

    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery : {e}")

    if df.empty:
        print("✅ Aucune donnee sur cette fenetre.")
        return

    print(f"{'='*70}")
    print(f"TOP {limite} — fort volume d'impressions, CTR le plus faible")
    print(f"{'='*70}")
    for i, r in df.iterrows():
        print(f"\n  {i+1}. {r['page']}")
        print(f"     silo={r['silo']} / sous_silo={r['sous_silo']}")
        print(f"     impressions={int(r['impressions'])}  clics={int(r['clics'])}  "
              f"ctr={r['ctr']*100:.2f}%  position_moyenne={r['position_moyenne']:.1f}")


if __name__ == "__main__":
    main()
