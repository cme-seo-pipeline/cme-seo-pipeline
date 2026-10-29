"""
CME — Verifie une hypothese alternative au "bug de tracking des etapes"
(29/10/2026, suite) : plutot qu'un bug, est-ce que les leads reels connus
(Hamila, Corinne, Nomi, Lionel) ont simplement ete soumis AVANT le
deploiement cPanel reel de l'instrumentation form_etape/interactions_contenu
-- l'operateur indique un deploiement "hier apres-midi" (28/10 PM).

Verifie :
  1. Le tout premier evenement jamais enregistre dans interactions_contenu
     (form_vu/form_etape), par type.
  2. S'il existe UNE SEULE ligne interactions_contenu pour le post_id de
     Hamila (5274) autour de son horaire de soumission (28/10 10:55-10:57
     UTC) -- si non, la tracking n'etait pas encore live a ce moment-la,
     et "soumis=0" n'est pas un bug mais une absence de donnee attendue.

LECTURE SEULE.
USAGE : python3 verifier_sequencement_deploiement_tracking.py
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.interactions_contenu"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("1) Premier evenement par type_evenement (MIN timestamp) :")
    df = client.query(f"""
        SELECT type_evenement, MIN(timestamp) AS premiere, COUNT(*) AS nb
        FROM `{TABLE}`
        GROUP BY type_evenement
        ORDER BY premiere
    """).to_dataframe()
    print(df.to_string(index=False))

    print("\n2) Toute ligne interactions_contenu pour post_id=5274 (Hamila) "
          "entre 28/10 10:00 et 12:00 UTC :")
    df2 = client.query(f"""
        SELECT timestamp, type_evenement, etape, session_id
        FROM `{TABLE}`
        WHERE source_post_id = '5274'
          AND timestamp BETWEEN '2026-10-28 10:00:00' AND '2026-10-28 12:00:00'
        ORDER BY timestamp
    """).to_dataframe()
    if df2.empty:
        print("  ⚠️ AUCUNE ligne -- la tracking n'etait probablement pas encore live a ce moment.")
    else:
        print(df2.to_string(index=False))

    print("\n3) Toute ligne interactions_contenu pour post_id=5274, toutes dates :")
    df3 = client.query(f"""
        SELECT timestamp, type_evenement, etape, session_id
        FROM `{TABLE}`
        WHERE source_post_id = '5274'
        ORDER BY timestamp
    """).to_dataframe()
    if df3.empty:
        print("  ⚠️ AUCUNE ligne pour ce post_id, jamais.")
    else:
        print(df3.to_string(index=False))


if __name__ == "__main__":
    main()
