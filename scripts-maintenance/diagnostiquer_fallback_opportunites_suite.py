"""
CME — Diagnostic (16/11/2026, suite immediate) : le premier passage de
diagnostiquer_fallback_opportunites.py a montre que les 20 sous-silos du
quota actuel ont TOUS 0 ligne dans 03_final.seo_opportunities, alors que
la vue contient bel et bien 521 lignes au total (157 sur silo='1. Gaz',
158 sur '5. Électricité', 143 sur '3. Aide Énergétique', 31 sur
'4. Solaire'). Hypothese testee ici : un decalage de LIBELLE exact entre
le `sous_silo` produit par la vue (CASE/REGEXP dans
fix_seo_opportunities_postid.sh) et les chaines litterales utilisees par
QUOTAS_SOUS_SILO dans pipeline.py (WHERE sous_silo = '...', egalite
stricte, sensible a l'accentuation/l'apostrophe/la casse/espaces).

Lecture seule.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print(f"{'='*95}")
    print("TOUS LES COUPLES (silo, sous_silo) REELLEMENT PRESENTS DANS seo_opportunities")
    print(f"{'='*95}")
    df = client.query(f"""
        SELECT silo, sous_silo, COUNT(*) AS lignes,
               MIN(jours_depuis_pub) AS min_jours, MAX(score_opportunite) AS meilleur_score
        FROM `{PROJECT_ID}.03_final.seo_opportunities`
        GROUP BY silo, sous_silo
        ORDER BY silo, lignes DESC
    """).to_dataframe()
    with __import__("pandas").option_context("display.max_rows", 200, "display.width", 160):
        print(df.to_string(index=False))

    print(f"\n{'='*95}")
    print("REPR() DES LIBELLES EXACTS (pour reperer un espace/accent invisible)")
    print(f"{'='*95}")
    for _, row in df.iterrows():
        print(f"  silo={row['silo']!r:35} sous_silo={row['sous_silo']!r}")


if __name__ == "__main__":
    main()
