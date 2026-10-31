"""
CME — Diagnostic (lecture seule) des 3 echecs consecutifs de
publication-quotidienne.yml les 24, 25 et 26/10/2026 (confirmes via
`gh run list` : failure les 3 jours, success avant et apres). Les logs
d'execution du run GitHub Actions ne sont pas lisibles depuis le sandbox
Claude Code (stockage blob hors de la liste blanche du proxy, limite deja
documentee dans CLAUDE.md) -- ce script reconstitue le point de panne
probable a partir des traces laissees dans BigQuery/WordPress par chaque
etape du pipeline, sans avoir besoin du texte d'erreur exact.

Etapes de run_pipeline(), dans l'ordre, et leur trace verifiable :
  1. selectionner_silos_a_traiter / scraping / briefs -> pas de trace
     directe, mais SI rediger_et_publier a tourne, ces etapes ont forcement
     reussi avant elle.
  2. rediger_et_publier -> lignes dans historique_publications ce jour-la.
  3. nettoyer_et_generer_schemas -> pas trace en base (SVG injectes dans le
     contenu WP directement, pas de colonne dediee) -- non verifiable ici.
  4. generer_featured_images -> colonne image_id renseignee sur les lignes
     du jour dans historique_publications.
  5. Facebook/Instagram + notification -> pas de trace BigQuery (hors
     perimetre de ce diagnostic).

LECTURE SEULE.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

JOURS = ["2026-10-24", "2026-10-25", "2026-10-26"]


def main():
    client_bq = init_bigquery()

    for jour in JOURS:
        print("=" * 80)
        print(f"JOUR : {jour}")
        print("=" * 80)
        df = client_bq.query(f"""
            SELECT post_id, date_publication, silo, sous_silo_strategique,
                   titre, image_id, type_publication
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE DATE(date_publication) = '{jour}'
            ORDER BY date_publication
        """).to_dataframe()

        if df.empty:
            print("  ⚠️ AUCUN article publie ce jour-la -- echec survenu AVANT ou PENDANT")
            print("     rediger_et_publier (selection/scraping/briefs/redaction/publication)")
            continue

        print(f"  {len(df)} article(s) publie(s) ce jour-la.")
        print(f"  Premiere publication : {df['date_publication'].min()}")
        print(f"  Derniere publication : {df['date_publication'].max()}")

        nb_avec_image = df['image_id'].notna().sum()
        nb_sans_image = len(df) - nb_avec_image
        print(f"  Image a la une : {nb_avec_image}/{len(df)} ont une image_id renseignee")
        if nb_sans_image > 0:
            print(f"  ⚠️ {nb_sans_image} article(s) SANS image_id -- echec probable pendant ou juste")
            print(f"     apres generer_featured_images() pour ces articles")
            print("     Articles concernes :")
            for _, r in df[df['image_id'].isna()].iterrows():
                print(f"       post_id={r['post_id']} | {r['titre'][:70]!r} | {r['sous_silo_strategique']}")
        else:
            print("  ✅ Toutes les images a la une sont presentes -- l'echec est survenu APRES")
            print("     generer_featured_images() (SVG dejas injectes directement dans le HTML,")
            print("     donc deja faits avant les images ; reste donc Facebook/Instagram ou")
            print("     la notification comme etapes suspectes pour cette journee).")
        print()


if __name__ == "__main__":
    main()
