"""
CME — Ajoute la colonne `temps_ms` a la table interactions_contenu
(ECRITURE/DDL, PAS lecture seule -- meme exception documentee que
creer_table_interactions_contenu.py).

Contexte (01/11/2026) : demande operateur de capturer aussi le TEMPS
ecoule (pas seulement la position en mots/scroll) pour chaque clic et
chaque jalon de lecture, afin de decider ou/quand placer le 1er
formulaire (ex. hypothese "apres ~15 secondes de lecture, soit ~150
mots"). La position seule (deja capturee via `position_contenu`/
`scroll_pct`) ne dit rien sur le TEMPS necessaire pour l'atteindre --
deux lecteurs peuvent atteindre 150 mots a des vitesses tres differentes,
d'ou le besoin de cette colonne pour correler position ET temps.

`temps_ms` = millisecondes ecoulees depuis le chargement de la page
jusqu'a l'evenement (clic, jalon de lecture, etape de formulaire, vue).
INTEGER, nullable -- les lignes existantes (avant ce changement) restent
valides avec cette colonne a NULL, aucune migration de donnees requise.

ALTER TABLE ADD COLUMN IF NOT EXISTS -- idempotent, reexecutable sans
risque si la colonne existe deja.

Execution via le pont GitHub Actions (maintenance-a-la-demande.yml) :
necessite GOOGLE_APPLICATION_CREDENTIALS (meme credentials BigQuery que
les scripts habituels).

USAGE :
  python3 ajouter_colonne_temps_ms_interactions.py
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE_REF = f"{PROJECT_ID}.04_pipeline_seo.interactions_contenu"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        ALTER TABLE `{TABLE_REF}`
        ADD COLUMN IF NOT EXISTS temps_ms INT64
    """
    print(f"Execution : {query.strip()}")
    job = client.query(query)
    job.result()
    print("✅ Colonne temps_ms presente (ajoutee ou deja existante).")

    table = client.get_table(TABLE_REF)
    print("\nSchema effectif :")
    for champ in table.schema:
        print(f"  - {champ.name} ({champ.field_type})")


if __name__ == "__main__":
    main()
