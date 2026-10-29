"""
CME — Classement des leads reels par POSITION du mini-formulaire rempli
(1er, 2e, 3e... bouton inseré dans l'article, cf. details.position du
payload contact-expert-inline). Demande operateur du 29/10/2026, pour
clore la session sur un indicateur unique avant de croiser cette donnee
avec les zones de clic/retention (interactions_contenu) une fois assez
de volume accumule.

LECTURE SEULE.
Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 classer_position_formulaire_leads.py
"""
import json
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"


def main():
    client = bigquery.Client(project=PROJECT_ID)
    df = client.query(f"""
        SELECT timestamp, telephone, details
        FROM `{TABLE}`
        WHERE tool = 'contact-expert-inline'
        ORDER BY timestamp DESC
    """).to_dataframe()

    positions = []
    for _, row in df.iterrows():
        try:
            d = json.loads(row["details"]) if row["details"] else {}
        except Exception:
            d = {}
        pos = d.get("position")
        if pos is not None:
            positions.append(int(pos))

    print(f"📊 {len(positions)} soumission(s) de formulaire avec position connue "
          f"(sur {len(df)} ligne(s) contact-expert-inline au total)\n")

    from collections import Counter
    compte = Counter(positions)
    total = len(positions)
    print("Classement par position du formulaire (1er bouton rencontré = position 1) :")
    for pos, nb in sorted(compte.items(), key=lambda x: -x[1]):
        pct = nb / total * 100 if total else 0
        print(f"  Position {pos} : {nb} lead(s) ({pct:.0f}%)")

    print(f"\n⚠️ Echantillon de {total} soumissions seulement -- indicatif, pas "
          f"encore statistiquement solide (fenetre de test en cours).")


if __name__ == "__main__":
    main()
