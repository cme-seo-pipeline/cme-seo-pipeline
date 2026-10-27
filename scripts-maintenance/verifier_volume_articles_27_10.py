"""
CME — Vérification ponctuelle (lecture seule) du volume d'articles publiés
le 26/10 et le 27/10/2026, pour répondre à la question operateur : les 10
articles Solaire transactionnels (publiés le 26/10 via
publier_articles_transactionnels_solaire.py, un script ponctuel hors du
run quotidien) ont-ils pu "prendre une place" dans le quota de 14
articles/jour du run quotidien (publication-quotidienne.yml) ?

Script de diagnostic jetable, pas destiné à rester dans scripts-maintenance/
à long terme (pas de --apply : lecture seule uniquement).

USAGE :
  python3 verifier_volume_articles_27_10.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import CONFIG, init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")


def main():
    client_bq = init_bigquery()

    for jour in ("2026-10-26", "2026-10-27"):
        print(f"\n{'='*70}")
        print(f"📅 {jour}")
        print(f"{'='*70}")
        df = client_bq.query(f"""
            SELECT silo, sous_silo_strategique, COUNT(*) AS n,
                   MIN(date_publication) AS premiere, MAX(date_publication) AS derniere
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE DATE(date_publication) = '{jour}'
            GROUP BY silo, sous_silo_strategique
            ORDER BY silo, sous_silo_strategique
        """).to_dataframe()

        if df.empty:
            print("  (aucun article)")
            continue

        total = 0
        for _, r in df.iterrows():
            print(f"  {r['silo']:<28} | {r['sous_silo_strategique']:<40} | {int(r['n'])} article(s) | {r['premiere']} → {r['derniere']}")
            total += int(r['n'])
        print(f"  {'-'*100}")
        print(f"  TOTAL {jour} : {total} article(s)")


if __name__ == "__main__":
    main()
