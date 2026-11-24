"""
CME — Ajoute 2 colonnes a la table leads_convertis (ECRITURE/DDL, PAS
lecture seule -- meme exception documentee que
creer_table_interactions_contenu.py / ajouter_colonne_temps_ms_interactions.py).

Contexte (24/11/2026) : demande operateur d'etendre le mini-formulaire
inline "contact-expert-inline" (wordpress-mu-plugins/cme-cta-progressifs.php,
variante 'contact' UNIQUEMENT -- pas 'appel') de 2 a 6 champs, affiches par
paires de 2 sur 3 ecrans ("2 -> 2 -> 2") : nom et prenom, telephone,
appartement ou maison, proprietaire ou locataire, code postal, adresse
e-mail.

`email` et `code_postal` ont deja leurs colonnes dans leads_convertis
(presentes dans le schema original du formulaire, avant sa reduction a 2
champs le 24/10/2026 -- voir CLAUDE.md) -- simplement vides pour
contact-expert-inline depuis cette date, aucune migration necessaire pour
elles. Les 2 nouveaux champs qualifiants (type de logement, statut
d'occupation) n'ont en revanche JAMAIS existe dans ce schema -- d'ou ce
script.

Choix delibere de 2 colonnes dediees plutot que de les glisser dans le
champ JSON generique `details` (deja utilise pour position/silo) : ce sont
des donnees de qualification de lead que l'operateur voudra tres
probablement filtrer/analyser directement (en SQL comme dans l'onglet
Google Sheets), pas seulement consulter au cas par cas -- meme logique que
les colonnes dediees deja en place pour code_postal/email plutot qu'un
blob.

STRING, nullable, les deux -- les lignes existantes (tous les autres
`tool`, et les anciennes soumissions contact-expert-inline/
appel-expert-inline/appel-header-formulaire/contact-expert-formulaire)
restent valides avec ces 2 colonnes a NULL, aucune migration de donnees
requise. La variante 'appel' (bouton d'appel, hors perimetre de cette
demande) n'enverra jamais ces 2 champs -- NULL pour elle aussi, par
construction, pas une anomalie.

ALTER TABLE ADD COLUMN IF NOT EXISTS -- idempotent, reexecutable sans
risque si les colonnes existent deja.

A executer UNE SEULE FOIS, avant tout deploiement du nouveau payload cote
tracking-api/server.py et cme-cta-progressifs.php -- meme precaution
d'ordre que documentee pour interactions_contenu/temps_ms (la colonne doit
exister avant qu'une insertion ne tente de l'utiliser, sinon BigQuery
rejette la ligne entiere plutot que de l'accepter avec un champ ignore).

Execution via le pont GitHub Actions (maintenance-a-la-demande.yml) :
necessite GOOGLE_APPLICATION_CREDENTIALS (memes credentials BigQuery que
les scripts habituels).

USAGE :
  python3 ajouter_colonnes_logement_leads.py
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE_REF = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    requetes = [
        f"ALTER TABLE `{TABLE_REF}` ADD COLUMN IF NOT EXISTS type_logement STRING",
        f"ALTER TABLE `{TABLE_REF}` ADD COLUMN IF NOT EXISTS statut_occupation STRING",
    ]
    for q in requetes:
        print(f"Execution : {q}")
        job = client.query(q)
        job.result()
    print("✅ Colonnes type_logement / statut_occupation presentes (ajoutees ou deja existantes).")

    table = client.get_table(TABLE_REF)
    print("\nSchema effectif :")
    for champ in table.schema:
        print(f"  - {champ.name} ({champ.field_type})")


if __name__ == "__main__":
    main()
