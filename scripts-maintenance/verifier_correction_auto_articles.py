"""
CME — Verification de l'etat reel du chantier "correction automatique des
articles publies" (auditer_et_corriger_articles, tourne via audit-mensuel.yml).

Le workflow se termine en succes chaque mois (confirme via l'historique des
runs GitHub Actions), mais un "succes" ne dit pas si le dispositif fait
encore quelque chose d'utile : si les tables sources sont vides ou perimees,
le script tourne, ne trouve aucun candidat, et se termine en succes sans
avoir rien corrige -- silencieusement. Ce script de LECTURE SEULE verifie
l'etat reel des 3 tables dont depend le dispositif :

1. indicateurs_reglementaires : les valeurs reglementaires de reference.
   Si leur date_verification est ancienne, le dispositif compare les
   articles a des valeurs elles-memes obsoletes.
2. mapping_indicateur_sous_silo : associe chaque indicateur aux silos ou il
   est cite en pertinence "directe". Si vide, aucun article n'est jamais
   selectionne comme candidat.
3. corrections_articles_auto : le journal reel de chaque correction
   appliquee. Sa derniere date dit quand le dispositif a REELLEMENT corrige
   quelque chose pour la derniere fois (pas juste tourne sans rien trouver).

Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("="*70)
    print("1. indicateurs_reglementaires — valeurs de reference et fraicheur")
    print("="*70)
    try:
        df = client.query(f"""
            SELECT indicateur, valeur, unite, date_verification
            FROM `{PROJECT_ID}.{DATASET_ID}.indicateurs_reglementaires`
            QUALIFY ROW_NUMBER() OVER (PARTITION BY indicateur ORDER BY date_verification DESC) = 1
            ORDER BY date_verification DESC
        """).to_dataframe()
        print(f"Indicateurs distincts : {len(df)}")
        print(df.to_string())
    except Exception as e:
        print(f"⚠️ Erreur : {e}")

    print("\n" + "="*70)
    print("2. mapping_indicateur_sous_silo — candidats eligibles a l'audit")
    print("="*70)
    try:
        df = client.query(f"""
            SELECT indicateur, silo, sous_silo_strategique, pertinence, COUNT(*) OVER() AS total_lignes
            FROM `{PROJECT_ID}.{DATASET_ID}.mapping_indicateur_sous_silo`
            WHERE pertinence = 'directe'
            LIMIT 30
        """).to_dataframe()
        print(df.to_string())
    except Exception as e:
        print(f"⚠️ Erreur : {e}")

    print("\n" + "="*70)
    print("3. corrections_articles_auto — journal reel des corrections appliquees")
    print("="*70)
    try:
        df = client.query(f"""
            SELECT post_id, titre, indicateur, date_correction, url_wp
            FROM `{PROJECT_ID}.{DATASET_ID}.corrections_articles_auto`
            ORDER BY date_correction DESC
            LIMIT 15
        """).to_dataframe()
        if df.empty:
            print("⚠️ Table vide ou inexistante — AUCUNE correction n'a jamais ete journalisee.")
        else:
            print(f"Derniere correction : {df.iloc[0]['date_correction']}")
            print(df.to_string())
    except Exception as e:
        print(f"⚠️ Erreur (table peut-etre inexistante) : {e}")

    print("\n" + "="*70)
    print("4. Combien d'articles sont actuellement eligibles (jointure reelle) ?")
    print("="*70)
    try:
        df = client.query(f"""
            SELECT DISTINCT m.indicateur, h.post_id, h.titre
            FROM `{PROJECT_ID}.{DATASET_ID}.mapping_indicateur_sous_silo` m
            JOIN `{PROJECT_ID}.{DATASET_ID}.historique_publications` h
                ON h.silo = m.silo AND h.sous_silo_strategique = m.sous_silo_strategique
            WHERE m.pertinence = 'directe'
        """).to_dataframe()
        print(f"Couples (indicateur, article) candidats a l'audit ce mois-ci : {len(df)}")
        if df.empty:
            print("⚠️ 0 candidat -- le dispositif n'a RIEN a auditer avec l'etat actuel des tables.")
    except Exception as e:
        print(f"⚠️ Erreur : {e}")


if __name__ == "__main__":
    main()
