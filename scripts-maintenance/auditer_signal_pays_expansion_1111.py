"""
CME — Quantifie le signal organique existant par pays (Belgique, Canada,
France, autres) sur les 60 derniers jours, pour eclairer une decision
d'elargissement de marche (demande operateur du 11/11/2026 : Pro France
vs Particulier Belgique vs Particulier Canada vs autre option).

Source : 04_pipeline_seo.clarity_insights_quotidien, metric_name='Country'
(meme table que le diagnostic "trafic Chine" du 02/11, mais agregee sur
une fenetre plus longue et ciblee sur les pays candidats a l'expansion
plutot que sur un seul pays suspect).

LECTURE SEULE.
"""
import json
from collections import defaultdict

from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"


def main():
    client = bigquery.Client(project=PROJECT_ID)
    df = client.query(f"""
        SELECT date_sync, information
        FROM `{PROJECT_ID}.{DATASET_ID}.clarity_insights_quotidien`
        WHERE metric_name = 'Country'
          AND date_sync >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
        ORDER BY date_sync
    """).to_dataframe()

    print(f"{len(df)} jour(s) de donnees 'Country' recuperes")

    totaux = defaultdict(int)
    jours_presents = defaultdict(int)
    jours_total = df["date_sync"].nunique()

    for _, row in df.iterrows():
        try:
            infos = json.loads(row["information"])
        except Exception:
            continue
        for entry in infos:
            pays = entry.get("Country") or entry.get("country") or entry.get("name") or "?"
            sessions = entry.get("sessionsCount") or entry.get("sessionCount") or entry.get("numOfVisitors") or entry.get("value") or 0
            try:
                sessions = int(sessions)
            except Exception:
                continue
            totaux[pays] += sessions
            jours_presents[pays] += 1

    print(f"\nFenetre : {jours_total} jours distincts avec des donnees")
    print("=" * 80)
    print(f"{'Pays':<30} | {'Sessions cumulees':>18} | {'Moy/jour':>10} | {'Jours presents':>15}")
    print("=" * 80)
    for pays, total in sorted(totaux.items(), key=lambda x: -x[1]):
        moy = total / jours_total if jours_total else 0
        print(f"{pays:<30} | {total:>18} | {moy:>10.2f} | {jours_presents[pays]:>15}")

    print()
    print("=" * 80)
    print("Focus pays candidats a l'expansion")
    print("=" * 80)
    for cible in ["France", "Belgium", "Belgique", "Canada"]:
        if cible in totaux:
            moy = totaux[cible] / jours_total if jours_total else 0
            print(f"  {cible} : {totaux[cible]} sessions cumulees sur {jours_total}j ({moy:.2f}/jour), present {jours_presents[cible]} jour(s)")
        else:
            print(f"  {cible} : absent du top des pays remontes par Clarity sur la fenetre")


if __name__ == "__main__":
    main()
