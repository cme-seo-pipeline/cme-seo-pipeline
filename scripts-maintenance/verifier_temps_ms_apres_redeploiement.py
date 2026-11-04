"""
CME — Verification (lecture seule) que le fix temps_ms
(tracking-api/server.py, voir CLAUDE.md) est bien actif apres le
redeploiement Cloud Run du 04/11/2026 (revision cme-tracking-api-00009-kl7).

Affiche les N derniers evenements de interactions_contenu, quel que soit
leur type, pour voir si les plus recents (survenus APRES le redeploiement)
ont temps_ms renseigne, contrairement aux 5048 lignes historiques toutes a
NULL (diagnostiquer_temps_ms_vide.py, 04/11/2026).

LECTURE SEULE -- aucune ecriture. Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 verifier_temps_ms_apres_redeploiement.py [--limite=20]
"""
import sys

try:
    import pandas as pd
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery/pandas manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"
TABLE = f"{PROJECT_ID}.{DATASET_ID}.interactions_contenu"


def parse_args():
    limite = 20
    for arg in sys.argv[1:]:
        if arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])
    return limite


def main():
    limite = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    df = client.query(f"""
        SELECT timestamp, type_evenement, temps_ms, position_contenu, silo, source_post_id
        FROM `{TABLE}`
        ORDER BY timestamp DESC
        LIMIT {limite}
    """).to_dataframe()

    if df.empty:
        print("⚠️ Aucune ligne dans interactions_contenu.")
        return

    print(f"📅 {len(df)} evenement(s) le(s) plus recent(s) (toute la table, pas filtre par date) :\n")
    for _, r in df.iterrows():
        # Bug corrige (04/11/2026) : "tms is not None and str(tms) != 'nan'"
        # traitait a tort le NA nullable pandas (Int64/<NA>) comme une valeur
        # presente -- seul pandas.isna() detecte correctement ce cas, en plus
        # du vrai NULL BigQuery renvoye comme None ou NaN flottant.
        tms = r["temps_ms"]
        marqueur = "❌ NULL" if pd.isna(tms) else "✅ " + str(int(tms))
        print(f"  {r['timestamp']} | {r['type_evenement']:<16} | temps_ms={marqueur:<14} | pos={r['position_contenu']} | {r['silo']} | post_id={r['source_post_id']}")

    non_null = df["temps_ms"].notna().sum()
    print(f"\n{non_null}/{len(df)} des {len(df)} evenements les plus recents ont temps_ms renseigne.")
    if non_null == 0:
        print("⚠️ Toujours NULL partout -- soit aucun evenement n'est encore survenu APRES le redeploiement,")
        print("   soit le fix n'est pas encore pris en compte. Reessayer apres un peu de trafic reel/un test manuel.")


if __name__ == "__main__":
    main()
