"""
CME — Creation (idempotente) des deux tables d'historisation du bilan CTR
(ECRITURE/DDL, PAS lecture seule -- meme exception documentee que
creer_table_interactions_contenu.py).

Contexte (21/11/2026) : demande operateur d'historiser le bilan CTR
hebdomadaire (jusqu'ici purement ad-hoc/glissant via
auditer_ctr_potentiel_perdu.py, aucune ecriture) pour pouvoir comparer
semaine/mois/trimestre/semestre/annee. Decisions prises avec l'operateur
(echange du 21/11) :
  - Stockage : table BigQuery dediee ("LA plus stratégique et durable sur
    le long terme") -- pas de relais Google Sheets pour ce besoin precis.
  - Les comparaisons mois/trimestre/semestre/annee se calculent par simple
    agregation SQL des lignes hebdomadaires deja stockees ici -- AUCUNE
    nouvelle requete GSC a ces granularites ("la plus stratégique et
    rigoureuse") -- voir comparer_bilan_ctr.py.
  - Les DEUX niveaux de detail sont historises chaque semaine ("Les deux
    (recommandé)") : le bilan par silo ET le top articles sous-performants.
  - Cadence hebdomadaire deplacee au MERCREDI (pas lundi ni vendredi) --
    voir historiser_bilan_ctr_hebdo.py pour la justification complete
    (delai de fiabilite GSC `GSC_LAG=3`, cme-gsc-to-bq.gs -- un run du
    lundi n'aurait pas encore de donnees fiables pour le samedi/dimanche
    de la semaine qui vient de se terminer ; le mercredi est le premier
    jour qui garantit une semaine lundi-dimanche entierement fiable).

Deux tables, dataset `04_pipeline_seo`, chacune partitionnee par jour sur
`periode_debut` (le lundi de la semaine mesuree) :

1. `bilan_ctr_historique_silo` -- un bilan agrege par (periode, silo),
   recalculable a toute granularite superieure par simple SUM/recombinaison
   ponderee par impressions (voir comparer_bilan_ctr.py) :
   - `position_moyenne` est deja ponderee par impressions au niveau de la
     semaine (SUM(position*impressions)/SUM(impressions)) -- c'est ce qui
     permet de la re-ponderer correctement a un niveau plus large sans
     jamais faire une moyenne simple de moyennes.
   - `ctr_attendu` est calcule a partir de cette position_moyenne via la
     meme grille sectorielle que auditer_ctr_potentiel_perdu.py (import
     direct, pas de duplication/derive possible de la grille).

2. `bilan_ctr_historique_articles` -- le TOP articles "bien positionnes
   mais CTR faible" de la semaine (meme logique de selection que
   auditer_ctr_potentiel_perdu.py), un `rang` par ligne pour permettre de
   retrouver facilement le classement de chaque semaine passee.

Execution via le pont GitHub Actions (maintenance-a-la-demande.yml) :
necessite les memes credentials BigQuery (GOOGLE_APPLICATION_CREDENTIALS)
que les scripts de lecture habituels. create_table(..., exists_ok=True) :
sans effet si les tables existent deja (reexecutable sans risque).

A executer UNE SEULE FOIS, avant tout premier run de
historiser_bilan_ctr_hebdo.py -- meme precaution d'ordre que documentee
pour interactions_contenu (la table doit exister avant toute tentative
d'insertion, sinon les lignes sont silencieusement perdues).

USAGE :
  python3 creer_tables_historique_ctr.py
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET = "04_pipeline_seo"

TABLE_SILO = "bilan_ctr_historique_silo"
TABLE_ARTICLES = "bilan_ctr_historique_articles"

SCHEMA_SILO = [
    bigquery.SchemaField("periode_debut", "DATE"),    # lundi de la semaine mesuree
    bigquery.SchemaField("periode_fin", "DATE"),       # dimanche de la semaine mesuree
    bigquery.SchemaField("silo", "STRING"),
    bigquery.SchemaField("clics", "INTEGER"),
    bigquery.SchemaField("impressions", "INTEGER"),
    bigquery.SchemaField("position_moyenne", "FLOAT"),  # ponderee par impressions
    bigquery.SchemaField("ctr_reel", "FLOAT"),
    bigquery.SchemaField("ctr_attendu", "FLOAT"),        # derive de position_moyenne, grille sectorielle
    bigquery.SchemaField("ecart_pts", "FLOAT"),          # (ctr_attendu - ctr_reel) * 100
    bigquery.SchemaField("date_calcul", "TIMESTAMP"),    # horodatage du run d'historisation
]

SCHEMA_ARTICLES = [
    bigquery.SchemaField("periode_debut", "DATE"),
    bigquery.SchemaField("periode_fin", "DATE"),
    bigquery.SchemaField("rang", "INTEGER"),             # classement de la semaine (1 = pire ecart)
    bigquery.SchemaField("url", "STRING"),
    bigquery.SchemaField("silo", "STRING"),
    bigquery.SchemaField("sous_silo", "STRING"),
    bigquery.SchemaField("position_moyenne", "FLOAT"),
    bigquery.SchemaField("impressions", "INTEGER"),
    bigquery.SchemaField("clics_reels", "INTEGER"),
    bigquery.SchemaField("ctr_reel", "FLOAT"),
    bigquery.SchemaField("ctr_attendu", "FLOAT"),
    bigquery.SchemaField("ecart_pts", "FLOAT"),
    bigquery.SchemaField("clics_manques_estimes", "FLOAT"),
    bigquery.SchemaField("date_calcul", "TIMESTAMP"),
]


def creer_table(client, nom_table, schema):
    table_ref = f"{PROJECT_ID}.{DATASET}.{nom_table}"
    table = bigquery.Table(table_ref, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY, field="periode_debut"
    )
    resultat = client.create_table(table, exists_ok=True)
    print(f"✅ Table prete : {resultat.full_table_id} (partitionnee par jour sur 'periode_debut')")

    verif = client.get_table(table_ref)
    print("   Schema effectif :")
    for champ in verif.schema:
        print(f"     - {champ.name} ({champ.field_type})")


def main():
    client = bigquery.Client(project=PROJECT_ID)
    creer_table(client, TABLE_SILO, SCHEMA_SILO)
    print()
    creer_table(client, TABLE_ARTICLES, SCHEMA_ARTICLES)


if __name__ == "__main__":
    main()
