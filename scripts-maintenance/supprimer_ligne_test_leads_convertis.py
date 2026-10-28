"""
CME — Suppression CIBLEE (ECRITURE, pas lecture seule -- exception
documentee ici) de l'UNIQUE ligne parasite identifiee le 28/10/2026 dans
leads_convertis, cree par erreur par un test de diagnostic (POST a corps
vide sur /api/log-lead pour verifier l'existence de la route -- voir
localiser_ligne_test_leads_convertis.py qui l'a localisee avec precision).

Filtre volontairement tres etroit (timestamp exact a la microseconde +
tous les champs identite vides) pour ne risquer AUCUNE autre ligne,
meme en cas de nouvelle ligne arrivee entre-temps sur le meme timestamp
(improbable a la microseconde pres, mais le filtre complet protege
quand meme contre ca).

Confirme le nombre de lignes avant suppression ; refuse si ce n'est pas
exactement 1 (garde-fou).

USAGE :
  python3 supprimer_ligne_test_leads_convertis.py            # dry-run (affiche la ligne)
  python3 supprimer_ligne_test_leads_convertis.py --apply    # supprime reellement
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"
TIMESTAMP_CIBLE = "2026-10-28 15:45:23.088977"

FILTRE = f"""
    TIMESTAMP(timestamp) = TIMESTAMP('{TIMESTAMP_CIBLE}')
    AND tool = '' AND prenom = '' AND nom = '' AND email = '' AND telephone = ''
"""


def main():
    apply_mode = "--apply" in sys.argv
    client = bigquery.Client(project=PROJECT_ID)
    table = f"{PROJECT_ID}.{DATASET_ID}.leads_convertis"

    df = client.query(f"SELECT * FROM `{table}` WHERE {FILTRE}").to_dataframe()
    print(f"🔎 {len(df)} ligne(s) correspondant exactement au filtre :")
    for _, r in df.iterrows():
        print(f"  {dict(r)}")

    if len(df) != 1:
        sys.exit(f"❌ Garde-fou : attendu exactement 1 ligne, trouve {len(df)} -- abandon, aucune suppression.")

    if not apply_mode:
        print("\n(dry-run -- relancer avec --apply pour supprimer reellement cette ligne)")
        return

    query = f"DELETE FROM `{table}` WHERE {FILTRE}"
    job = client.query(query)
    job.result()
    print(f"✅ Ligne supprimee ({job.num_dml_affected_rows} ligne(s) affectee(s)).")


if __name__ == "__main__":
    main()
