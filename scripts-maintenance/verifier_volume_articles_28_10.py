"""
CME — Vérification ponctuelle (lecture seule) du volume et de la
répartition des articles publiés le 28/10/2026 -- premier run avec le
quota quotidien étendu à 24 articles/jour (commit 6ed2a3a, 27/10/2026,
+10 Solaire récurrent avec angle transactionnel forcé).

Script de diagnostic jetable, pas destiné à rester durablement dans
scripts-maintenance/ (pas de --apply : lecture seule uniquement).

USAGE :
  python3 verifier_volume_articles_28_10.py
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
    jour = "2026-10-28"

    df = client_bq.query(f"""
        SELECT silo, sous_silo_strategique, COUNT(*) AS n,
               MIN(date_publication) AS premiere, MAX(date_publication) AS derniere
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE DATE(date_publication) = '{jour}'
        GROUP BY silo, sous_silo_strategique
        ORDER BY silo, sous_silo_strategique
    """).to_dataframe()

    print(f"{'='*70}")
    print(f"📅 {jour}")
    print(f"{'='*70}")

    if df.empty:
        print("  (aucun article)")
        return

    total = 0
    for _, r in df.iterrows():
        print(f"  {r['silo']:<28} | {r['sous_silo_strategique']:<40} | {int(r['n'])} article(s) | {r['premiere']} → {r['derniere']}")
        total += int(r['n'])
    print(f"  {'-'*100}")
    print(f"  TOTAL {jour} : {total} article(s)")

    print(f"\n{'='*70}")
    print("📝 Titres des articles Solaire (verification angle transactionnel)")
    print(f"{'='*70}")
    df_sol = client_bq.query(f"""
        SELECT sous_silo_strategique, titre, mot_cle, url_wp
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE DATE(date_publication) = '{jour}' AND silo = '4. Solaire'
        ORDER BY sous_silo_strategique
    """).to_dataframe()
    if df_sol.empty:
        print("  (aucun article Solaire aujourd'hui)")
    else:
        for _, r in df_sol.iterrows():
            print(f"  [{r['sous_silo_strategique']}] {r['titre']}")
            print(f"      mot-clé : {r['mot_cle']}")
            print(f"      {r['url_wp']}")


if __name__ == "__main__":
    main()
