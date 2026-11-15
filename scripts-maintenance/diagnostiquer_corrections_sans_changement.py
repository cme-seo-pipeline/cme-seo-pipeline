"""
CME — Diagnostic (15/11/2026) : combien de corrections "automatiques"
loguees dans `corrections_articles_auto` n'ont en realite AUCUN
changement visible (passage_avant == passage_apres), + verification de
la fiabilite des sources utilisees par l'audit mensuel :
- fraicheur de `indicateurs_reglementaires` (la donnee de reference) ;
- coherence de `mapping_indicateur_sous_silo` (pertinence='directe') --
  tout indicateur mappe existe-t-il bien dans indicateurs_reglementaires,
  ou l'audit le saute-t-il silencieusement (verdicts.py, ligne
  `if row['indicateur'] not in valeurs: continue`) ?

Lecture seule.
"""
import sys
import re

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"


def normaliser(texte):
    if texte is None:
        return ""
    return re.sub(r'\s+', ' ', texte).strip()


def main():
    client = bigquery.Client(project=PROJECT_ID)

    # 1) Historique complet des corrections -- combien sont des no-op.
    query_hist = f"""
        SELECT post_id, titre, indicateur, passage_avant, passage_apres,
               date_correction, url_wp
        FROM `{PROJECT_ID}.{DATASET_ID}.corrections_articles_auto`
        ORDER BY date_correction
    """
    try:
        df = client.query(query_hist).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery (corrections_articles_auto) : {e}")

    print(f"{'='*90}")
    print("HISTORIQUE COMPLET corrections_articles_auto -- corrections sans changement reel")
    print(f"{'='*90}")
    print(f"Total de lignes dans la table : {len(df)}\n")

    if df.empty:
        print("Table vide.")
    else:
        df["no_op"] = df.apply(
            lambda r: normaliser(r["passage_avant"]) == normaliser(r["passage_apres"]), axis=1
        )
        nb_noop = int(df["no_op"].sum())
        print(f"Corrections SANS changement reel (avant == apres) : {nb_noop} / {len(df)}\n")

        if nb_noop:
            print("Detail des no-op par date :")
            noop_par_date = df[df["no_op"]].groupby(
                df[df["no_op"]]["date_correction"].astype(str).str.slice(0, 10)
            ).size()
            for jour, nb in noop_par_date.items():
                print(f"  {jour} : {nb} correction(s) sans changement reel")

            print("\nDetail des no-op par indicateur :")
            noop_par_indic = df[df["no_op"]].groupby("indicateur").size().sort_values(ascending=False)
            for indic, nb in noop_par_indic.items():
                print(f"  {indic:<35} {nb}")

            print(f"\nListe complete des post_id concernes :")
            print(sorted(df[df["no_op"]]["post_id"].unique().tolist()))

        # Pour comparaison -- les corrections AVEC changement reel.
        nb_reel = len(df) - nb_noop
        print(f"\nCorrections AVEC changement reel : {nb_reel} / {len(df)}")

    # 2) Fraicheur des indicateurs reglementaires (source de verite de l'audit).
    print(f"\n{'='*90}")
    print("FRAICHEUR DE indicateurs_reglementaires (derniere valeur connue par indicateur)")
    print(f"{'='*90}")
    query_fraicheur = f"""
        SELECT indicateur, valeur, unite, date_verification,
               DATE_DIFF(CURRENT_DATE(), DATE(date_verification), DAY) AS jours_depuis_verif
        FROM `{PROJECT_ID}.{DATASET_ID}.indicateurs_reglementaires`
        QUALIFY ROW_NUMBER() OVER (PARTITION BY indicateur ORDER BY date_verification DESC) = 1
        ORDER BY jours_depuis_verif DESC
    """
    try:
        df_fr = client.query(query_fraicheur).to_dataframe()
    except Exception as e:
        print(f"❌ Erreur BigQuery (indicateurs_reglementaires) : {e}")
        df_fr = None

    if df_fr is not None:
        for _, row in df_fr.iterrows():
            alerte = "⚠️ " if row["jours_depuis_verif"] > 7 else ""
            print(f"  {alerte}{row['indicateur']:<35} valeur={row['valeur']:<12} "
                  f"unite={row['unite']:<10} derniere verif. il y a {row['jours_depuis_verif']} jour(s) "
                  f"({row['date_verification']})")

    # 3) Coherence mapping_indicateur_sous_silo (pertinence='directe') vs
    #    indicateurs reellement presents dans indicateurs_reglementaires --
    #    un indicateur mappe mais absent de la table fait sauter TOUS ses
    #    articles candidats silencieusement (continue, pas de log).
    print(f"\n{'='*90}")
    print("COHERENCE mapping_indicateur_sous_silo (pertinence='directe') vs indicateurs_reglementaires")
    print(f"{'='*90}")
    query_mapping = f"""
        SELECT DISTINCT m.indicateur,
               m.indicateur IN (SELECT DISTINCT indicateur FROM `{PROJECT_ID}.{DATASET_ID}.indicateurs_reglementaires`) AS present_dans_indicateurs
        FROM `{PROJECT_ID}.{DATASET_ID}.mapping_indicateur_sous_silo` m
        WHERE m.pertinence = 'directe'
    """
    try:
        df_map = client.query(query_mapping).to_dataframe()
    except Exception as e:
        print(f"❌ Erreur BigQuery (mapping_indicateur_sous_silo) : {e}")
        df_map = None

    if df_map is not None:
        manquants = df_map[~df_map["present_dans_indicateurs"]]
        if manquants.empty:
            print("✅ Tous les indicateurs mappes en pertinence='directe' existent bien "
                  "dans indicateurs_reglementaires -- aucun candidat saute silencieusement.")
        else:
            print(f"⚠️ {len(manquants)} indicateur(s) mappe(s) en 'directe' mais ABSENT(S) de "
                  f"indicateurs_reglementaires -- tous leurs articles candidats sont sautes "
                  f"silencieusement par auditer_et_corriger_articles() :")
            for _, row in manquants.iterrows():
                print(f"  - {row['indicateur']}")


if __name__ == "__main__":
    main()
