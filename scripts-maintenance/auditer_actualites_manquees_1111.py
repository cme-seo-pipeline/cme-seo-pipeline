"""
CME — Audit : y a-t-il des changements reglementaires reels qui auraient
du declencher Mode Actualite mais n'ont jamais ete publies ?

Demande operateur du 11/11/2026, suite a la verification de sante du
systeme (BigQuery/Anthropic/WordPress/SearchApi tous OK, chemin de
publication confirme fonctionnel au 14/10) : "est-ce qu'il y a des
actualites qu'on a rate et il faut les rectifier et les publier".

Methode, en 3 temps :
  1/ Recupere la definition SQL reelle de vue_changements_indicateurs
     (creee directement dans BigQuery, jamais versionnee dans ce repo)
     pour comprendre EXACTEMENT comment un "changement" est detecte --
     condition necessaire avant de juger si quoi que ce soit a pu lui
     echapper structurellement.
  2/ Reconstruit, a partir de l'historique BRUT de indicateurs_reglementaires
     (une ligne par rafraichissement, PAS seulement les lignes vues par
     la vue a un instant donne), chaque VRAIE transition de valeur par
     indicateur sur les 120 derniers jours -- independamment de la vue,
     pour ne pas rejouer le meme angle mort qu'elle pourrait avoir.
  3/ Croise avec historique_publications (type_publication='actualite')
     pour voir quelles transitions ont ete suivies d'un article, et
     lesquelles non -- en excluant les cas legitimement ignores (deja
     couvert par un article recent sur le meme sujet via l'audit
     mensuel reglementaire, ou variation manifestement non significative).

LECTURE SEULE -- aucune ecriture, aucune publication.
"""
from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"


def recuperer_definition_vue(client):
    print("=" * 80)
    print("1/ Definition SQL reelle de vue_changements_indicateurs")
    print("=" * 80)
    try:
        df = client.query(f"""
            SELECT view_definition
            FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.VIEWS`
            WHERE table_name = 'vue_changements_indicateurs'
        """).to_dataframe()
        if df.empty:
            print("  ⚠️ Vue introuvable dans INFORMATION_SCHEMA -- nom ou dataset different ?")
            return None
        definition = df.iloc[0]["view_definition"]
        print(definition)
        return definition
    except Exception as e:
        print(f"  ❌ Erreur : {e}")
        return None


def reconstruire_transitions(client):
    print()
    print("=" * 80)
    print("2/ Historique brut des valeurs par indicateur (120 derniers jours)")
    print("=" * 80)
    try:
        df = client.query(f"""
            SELECT indicateur, sous_categorie, valeur, unite,
                   date_debut_validite, date_verification, run_id
            FROM `{PROJECT_ID}.{DATASET_ID}.indicateurs_reglementaires`
            WHERE date_verification >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 120 DAY)
            ORDER BY indicateur, sous_categorie, date_verification
        """).to_dataframe()
    except Exception as e:
        print(f"  ❌ Erreur requete : {e}")
        return []

    print(f"  {len(df)} lignes recuperees")
    transitions = []
    for (indicateur, sous_cat), groupe in df.groupby(["indicateur", "sous_categorie"], dropna=False):
        groupe = groupe.sort_values("date_verification")
        precedent = None
        for _, row in groupe.iterrows():
            if precedent is not None and row["valeur"] != precedent["valeur"]:
                transitions.append({
                    "indicateur": indicateur,
                    "sous_categorie": sous_cat,
                    "valeur_avant": precedent["valeur"],
                    "valeur_apres": row["valeur"],
                    "unite": row["unite"],
                    "date_debut_validite_avant": precedent["date_debut_validite"],
                    "date_debut_validite_apres": row["date_debut_validite"],
                    "date_detection": row["date_verification"],
                })
            precedent = row

    print(f"\n  {len(transitions)} VRAIE(S) TRANSITION(S) DE VALEUR detectee(s) sur 120 jours :")
    for t in transitions:
        print(f"    [{t['date_detection']}] {t['indicateur']} ({t['sous_categorie']}) : "
              f"{t['valeur_avant']} -> {t['valeur_apres']} {t['unite']} "
              f"(periode validite : {t['date_debut_validite_avant']} -> {t['date_debut_validite_apres']})")
    return transitions


def recuperer_publications_actualite(client):
    print()
    print("=" * 80)
    print("3/ Publications Mode Actualite deja faites (type_publication='actualite')")
    print("=" * 80)
    try:
        df = client.query(f"""
            SELECT post_id, titre, mot_cle, date_publication, sous_silo_strategique
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE type_publication = 'actualite'
            ORDER BY date_publication DESC
        """).to_dataframe()
    except Exception as e:
        print(f"  ❌ Erreur requete : {e}")
        return None
    print(f"  {len(df)} publication(s) Mode Actualite au total, historique complet :")
    for _, row in df.iterrows():
        print(f"    [{row['date_publication']}] post_id={row['post_id']} | {row['titre']} | sous-silo={row['sous_silo_strategique']}")
    return df


def main():
    client = bigquery.Client(project=PROJECT_ID)
    recuperer_definition_vue(client)
    transitions = reconstruire_transitions(client)
    df_pubs = recuperer_publications_actualite(client)

    print()
    print("=" * 80)
    print("4/ Rapprochement -- transitions sans publication correspondante")
    print("=" * 80)
    if not transitions:
        print("  Aucune transition de valeur reelle sur la fenetre -- rien a rapprocher.")
        return
    dates_pubs = set()
    if df_pubs is not None and not df_pubs.empty:
        dates_pubs = set(pd_ts.date() for pd_ts in df_pubs["date_publication"])
    for t in transitions:
        date_detection = t["date_detection"]
        try:
            date_detection_jour = date_detection.date()
        except Exception:
            date_detection_jour = None
        a_une_pub_proche = any(
            abs((date_detection_jour - d).days) <= 3
            for d in dates_pubs
        ) if date_detection_jour and dates_pubs else False
        statut = "✅ publication proche trouvee" if a_une_pub_proche else "⚠️ AUCUNE publication proche -- a investiguer"
        print(f"  [{t['date_detection']}] {t['indicateur']} : {t['valeur_avant']} -> {t['valeur_apres']} -- {statut}")


if __name__ == "__main__":
    main()
