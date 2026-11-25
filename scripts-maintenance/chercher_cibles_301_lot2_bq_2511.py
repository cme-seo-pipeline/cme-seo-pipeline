"""
CME — Deuxieme passe de recherche de cibles 301 pour le lot de 12 URLs
404 du 25/11/2026 : la recherche par mot-cle via l'API publique WP
(chercher_cibles_301_lot2_2511.py) s'est revelee trop bruitee (recherche
WP = simple correspondance de mots, pas de pertinence semantique) --
cette passe interroge directement historique_publications (BigQuery, le
log du pipeline avec titre/mot_cle/url_wp exacts) par LIKE sur des motifs
plus precis, pour chaque sujet encore sans candidat clair.

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
    ("tarif-bleu-edf-vs-autres-fournisseurs", "titre LIKE '%tarif bleu%' OR mot_cle LIKE '%tarif bleu%' OR titre LIKE '%tarif réglementé%' OR mot_cle LIKE '%tarif reglemente%'"),
    ("prime-energie-cee-comment-ca-marche", "titre LIKE '%CEE%' OR mot_cle LIKE '%CEE%' OR titre LIKE '%prime energie%' OR titre LIKE '%prime énergie%' OR mot_cle LIKE '%prime energie%'"),
    ("comprendre-ma-facture-delectricite", "titre LIKE '%comprendre%facture%' OR mot_cle LIKE '%comprendre%facture%électricité%' OR mot_cle LIKE '%comprendre facture electricite%'"),
    ("comprendre-tarif-de-base-electricite", "titre LIKE '%tarif de base%' OR mot_cle LIKE '%tarif de base%'"),
    ("ohm-energie", "titre LIKE '%Ohm Energie%' OR mot_cle LIKE '%ohm energie%' OR titre LIKE '%Ohm%' OR mot_cle LIKE '%ohm%'"),
    ("les-prix-de-kwh", "titre LIKE '%prix du kwh%' OR titre LIKE '%prix du kWh%' OR mot_cle LIKE '%prix du kwh%' OR mot_cle LIKE '%prix kwh%'"),
    ("economies-denergie-le-guide-pratique", "titre LIKE '%économies d%énergie%guide%' OR mot_cle LIKE '%economies energie guide%' OR titre LIKE '%guide%économies%'"),
    ("reduire-vos-factures-delectricte", "titre LIKE '%réduire%facture%électricité%' OR mot_cle LIKE '%reduire facture electricite%'"),
    ("pourquoi-pompe-a-chaleur-preferee-francais", "titre LIKE '%pompe à chaleur%préférée%' OR titre LIKE '%pompe a chaleur%francais%' OR mot_cle LIKE '%pompe a chaleur%francais%'"),
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
            LIMIT 10
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
