"""
CME — 3e passe (motifs elargis) de recherche de cibles 301 pour les 7
sujets du lot de 12 URLs 404 du 25/11/2026 restes sans candidat clair
apres chercher_cibles_301_lot2_bq_2511.py.

LECTURE SEULE.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

REQUETES = [
    ("tarif-bleu-edf-vs-autres-fournisseurs (elargi)", "mot_cle LIKE '%EDF%' OR titre LIKE '%EDF%'"),
    ("comprendre-tarif-de-base-electricite (elargi)", "titre LIKE '%tarif%' AND (titre LIKE '%reglement%' OR titre LIKE '%réglement%' OR mot_cle LIKE '%reglement%' OR mot_cle LIKE '%réglement%')"),
    ("ohm-energie (elargi, sans accent)", "mot_cle LIKE '%fournisseur alternatif%' OR titre LIKE '%fournisseur alternatif%' OR mot_cle LIKE '%comparatif fournisseur%'"),
    ("les-prix-de-kwh (elargi)", "titre LIKE '%prix%kwh%' OR titre LIKE '%prix%kWh%' OR mot_cle LIKE '%prix%kwh%'"),
    ("economies-denergie-guide (elargi)", "titre LIKE '%économies%' AND titre LIKE '%énergie%'"),
    ("reduire-vos-factures-delectricte (elargi)", "titre LIKE '%réduire%facture%' OR mot_cle LIKE '%reduire%facture%' OR titre LIKE '%baisser%facture%'"),
    ("pourquoi-pompe-a-chaleur-preferee-francais (elargi)", "(titre LIKE '%pompe à chaleur%' OR mot_cle LIKE '%pompe a chaleur%') AND (titre LIKE '%2026%' OR titre LIKE '%meilleur%' OR titre LIKE '%populaire%')"),
]


def main():
    client = init_bigquery()
    for label, where_clause in REQUETES:
        print("=" * 100)
        print(f"### {label}")
        print(f"    WHERE {where_clause}")
        print("=" * 100)
        df = client.query(f"""
            SELECT post_id, date_publication, titre, mot_cle, url_wp
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE {where_clause}
            ORDER BY date_publication DESC
            LIMIT 8
        """).to_dataframe()
        if df.empty:
            print("    Aucun resultat.")
        else:
            for _, r in df.iterrows():
                print(f"    - {r['date_publication']} | {r['titre']} | mot_cle={r['mot_cle']!r}")
                print(f"      {r['url_wp']}")
        print()


if __name__ == "__main__":
    main()
