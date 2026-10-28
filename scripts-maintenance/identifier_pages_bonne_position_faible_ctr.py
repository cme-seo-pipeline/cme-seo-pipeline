"""
CME — Identification des pages BIEN positionnees (page 1 Google) mais a
CTR anormalement faible (donnees Google Search Console, table
01_raw.gsc_queries synchronisee par cme-gsc-to-bq.gs).

Complementaire de identifier_pages_fort_volume_faible_ctr.py : ce
script-la remontait des pages a fort volume mais tres mal positionnees
(position moyenne 20-70), ou un CTR a 0% s'explique surtout par la
position, pas par le titre/meta -- peu actionnable via un simple
retravail de titre. Ici on isole au contraire les pages deja en bonne
position (donc visibles, cliquables en theorie) dont le CTR reste tres
bas : c'est le signal le plus actionnable pour une optimisation de
titre_seo/meta_description, puisque la position n'explique pas le
probleme.

Methode : agrege par page sur la fenetre choisie (SUM impressions/clics,
CTR recalcule depuis les sommes, pas de moyenne de ctr brut), filtre sur
position_moyenne <= --position-max ET ctr < --ctr-max, avec un seuil
anti-bruit --impressions-min, puis classe par impressions decroissantes
(priorite a l'effet potentiel le plus eleve) et affiche les --limite
premieres.

Lecture seule -- aucune ecriture, aucun --apply necessaire.

USAGE :
  python3 identifier_pages_bonne_position_faible_ctr.py
  python3 identifier_pages_bonne_position_faible_ctr.py --jours=90 --position-max=10 --ctr-max=0.01 --impressions-min=20 --limite=5

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
    position_max = 10
    ctr_max = 0.01
    impressions_min = 20
    limite = 5
    for arg in sys.argv:
        if arg.startswith("--jours="):
            jours = int(arg.split("=", 1)[1])
        elif arg.startswith("--position-max="):
            position_max = float(arg.split("=", 1)[1])
        elif arg.startswith("--ctr-max="):
            ctr_max = float(arg.split("=", 1)[1])
        elif arg.startswith("--impressions-min="):
            impressions_min = int(arg.split("=", 1)[1])
        elif arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])
    return jours, position_max, ctr_max, impressions_min, limite


def main():
    jours, position_max, ctr_max, impressions_min, limite = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print(f"🔎 Fenetre : {jours} derniers jours — position moyenne <= {position_max} "
          f"— ctr < {ctr_max*100:.1f}% — impressions >= {impressions_min} "
          f"— on affiche les {limite} au volume d'impressions le plus eleve\n")

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
        )
        SELECT *
        FROM agrege
        WHERE impressions >= {impressions_min}
          AND position_moyenne <= {position_max}
          AND ctr < {ctr_max}
        ORDER BY impressions DESC
        LIMIT {limite}
    """

    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery : {e}")

    if df.empty:
        print("✅ Aucune page ne correspond a ces criteres sur cette fenetre.")
        return

    print(f"{'='*70}")
    print(f"TOP {limite} — bonne position, CTR anormalement faible")
    print(f"{'='*70}")
    for i, r in df.iterrows():
        print(f"\n  {i+1}. {r['page']}")
        print(f"     silo={r['silo']} / sous_silo={r['sous_silo']}")
        print(f"     impressions={int(r['impressions'])}  clics={int(r['clics'])}  "
              f"ctr={r['ctr']*100:.2f}%  position_moyenne={r['position_moyenne']:.1f}")


if __name__ == "__main__":
    main()
