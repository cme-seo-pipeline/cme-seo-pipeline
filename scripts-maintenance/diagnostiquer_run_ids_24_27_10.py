"""
CME — Complement au diagnostic du 31/10/2026 : diagnostiquer_origine_articles_26_10.py
a montre que les 10 articles du 26/10 avec image_id venaient d'un run_id
'solaire_transac_...' (mecanisme Solaire distinct, pas publication-quotidienne.yml).
Ce script verifie les run_id reels du 24/10 (14 articles, deja localises comme
venant bien du run quotidien ce jour-la) et d'un jour sain de reference (27/10)
pour confirmer le format attendu d'un run_id issu de run_pipeline(), et verifier
si le run quotidien du 26/10 a produit 0 article (comme le 25/10) ou si des
articles lui sont bien attribuables sous un autre angle.

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

    for jour in ["2026-10-24", "2026-10-26", "2026-10-27"]:
        df = client_bq.query(f"""
            SELECT run_id, COUNT(*) AS nb, MIN(date_publication) AS premiere, MAX(date_publication) AS derniere
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE DATE(date_publication) = '{jour}'
            GROUP BY run_id
            ORDER BY premiere
        """).to_dataframe()
        print(f"=== {jour} ===")
        if df.empty:
            print("  (aucun article)")
        else:
            for _, r in df.iterrows():
                print(f"  run_id={r['run_id']!r} | {r['nb']} article(s) | {r['premiere']} -> {r['derniere']}")
        print()


if __name__ == "__main__":
    main()
