"""
CME — Creation (idempotente) de la table interactions_contenu (ECRITURE/DDL,
PAS lecture seule -- exception documentee ici et dans CLAUDE.md).

Contexte (26/10/2026) : demande operateur d'approfondir l'analyse du tunnel
de conversion avec une vraie cartographie des zones de clic dans les
articles + la progression du mini-formulaire etape par etape. Aucune des
sources existantes (API Clarity synchronisee, GA4, leads_convertis) ne
contient ce niveau de detail -- voir l'echange avec l'operateur du 25-26/10 :
l'API Data Export de Clarity n'expose qu'un ensemble fixe de metriques
agregees (Browser/Country/Device/EngagementTime/RageClickCount/ScrollDepth/
PopularPages/...), jamais de position de clic ni de heatmap (ca n'existe
que dans le tableau de bord Clarity, pas via l'API).

D'ou cette nouvelle table, alimentee par un nouveau relais (voir
tracking-api/server.py route /api/log-interaction, et le relais WordPress
/wp-json/cme/v1/log-interaction dans cme-tracking-conversion.php), elle-meme
remplie par deux nouveaux trackers JS :
  - cme-tracking-conversion.php : clics sur liens/images a l'interieur du
    contenu des articles (type_evenement='clic_contenu').
  - cme-cta-progressifs.php : visibilite du mini-formulaire, progression
    etape par etape, abandon (type_evenement='form_vu'/'form_etape'/
    'form_abandon').

Schema volontairement unifie (une seule table pour les deux trackers) --
les colonnes non pertinentes a un type_evenement donne restent vides,
plus simple que de multiplier les tables pour un volume de donnees modeste
(quelques centaines de lignes/jour au trafic actuel).

Execution via le pont GitHub Actions (maintenance-a-la-demande.yml) :
necessite les memes credentials BigQuery (GOOGLE_APPLICATION_CREDENTIALS)
que les scripts de lecture habituels. create_table(..., exists_ok=True) :
sans effet si la table existe deja (reexecutable sans risque).
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET = "04_pipeline_seo"
TABLE = "interactions_contenu"

SCHEMA = [
    bigquery.SchemaField("timestamp", "TIMESTAMP"),
    bigquery.SchemaField("type_evenement", "STRING"),   # clic_contenu | form_vu | form_etape | form_abandon
    bigquery.SchemaField("cible", "STRING"),            # clic_contenu : lien_interne | lien_externe | image
    bigquery.SchemaField("section", "STRING"),          # clic_contenu : texte du dernier titre h2/h3 avant le clic
    bigquery.SchemaField("texte", "STRING"),            # clic_contenu : texte du lien / alt de l'image, tronque
    bigquery.SchemaField("position_contenu", "INTEGER"),  # clic_contenu : mots avant le clic | form_* : numero d'occurrence du formulaire (n)
    bigquery.SchemaField("etape", "STRING"),            # form_etape/form_abandon : '0' | '1' | 'termine'
    bigquery.SchemaField("scroll_pct", "FLOAT"),
    bigquery.SchemaField("silo", "STRING"),
    bigquery.SchemaField("session_id", "STRING"),       # anonyme, genere cote client par chargement de page
    bigquery.SchemaField("source_page", "STRING"),
    bigquery.SchemaField("source_post_id", "STRING"),
    bigquery.SchemaField("user_agent", "STRING"),
]


def main():
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"
    table = bigquery.Table(table_ref, schema=SCHEMA)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY, field="timestamp"
    )
    resultat = client.create_table(table, exists_ok=True)
    print(f"✅ Table prete : {resultat.full_table_id} (partitionnee par jour sur 'timestamp')")

    # Confirme le schema effectif (utile si la table existait deja avec un
    # schema potentiellement different d'un essai precedent).
    verif = client.get_table(table_ref)
    print("\nSchema effectif :")
    for champ in verif.schema:
        print(f"  - {champ.name} ({champ.field_type})")


if __name__ == "__main__":
    main()
