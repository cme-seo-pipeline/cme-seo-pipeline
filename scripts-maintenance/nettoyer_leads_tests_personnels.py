"""
CME — Nettoyage de leads_convertis : tests personnels de l'operateur +
lignes de diagnostic technique (DRY-RUN par defaut, --apply pour ecrire).

Demande operateur du 29/10/2026, suite a lister_tous_les_leads.py : supprimer
(1) toutes les lignes contenant "Blal"/"Oussama" en prenom ou nom -- ses
propres tests sur les 3 anciens simulateurs (comparateur-energie,
aides-renovation, solaire, juillet-aout 2026) et sur le nouveau formulaire
inline (22-24/10) -- et (2) les lignes tool='diagnostic-relais-test'
(mes propres tests de la chaine de relais, 19/10 et 24/10). Explicitement
PRESERVE : le doublon "HAMILA FATHI" du 28/10 (2 lignes, meme tel/article) --
l'operateur a demande de ne pas y toucher.

Filtre (verifie manuellement contre la liste complete avant ecriture,
lister_tous_les_leads.py du 29/10) :
  LOWER(prenom) LIKE '%blal%' OR LOWER(nom) LIKE '%blal%'
  OR LOWER(prenom) LIKE '%oussama%' OR LOWER(nom) LIKE '%oussama%'
  OR tool = 'diagnostic-relais-test'

Garde-fou : refuse d'ecrire si le nombre de lignes correspondant au filtre
ne correspond pas exactement a celui attendu (verifie manuellement avant
le --apply, passe en argument --attendu=N), pour eviter toute suppression
plus large que prevu si de nouvelles lignes sont arrivees entre-temps.

USAGE :
  python3 nettoyer_leads_tests_personnels.py                     # dry-run
  python3 nettoyer_leads_tests_personnels.py --apply --attendu=28  # ecrit, avec garde-fou
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"

FILTRE = """
    LOWER(prenom) LIKE '%blal%' OR LOWER(nom) LIKE '%blal%'
    OR LOWER(prenom) LIKE '%oussama%' OR LOWER(nom) LIKE '%oussama%'
    OR tool = 'diagnostic-relais-test'
"""


def parse_args():
    apply_ = "--apply" in sys.argv
    attendu = None
    for arg in sys.argv:
        if arg.startswith("--attendu="):
            attendu = int(arg.split("=", 1)[1])
    return apply_, attendu


def main():
    apply_, attendu = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print("📋 Lignes correspondant au filtre (candidates a la suppression) :")
    df = client.query(f"""
        SELECT timestamp, tool, prenom, nom, telephone, email
        FROM `{TABLE}`
        WHERE {FILTRE}
        ORDER BY timestamp DESC
    """).to_dataframe()
    print(df.to_string(index=False))
    nb = len(df)
    print(f"\nTotal candidates : {nb}")

    if not apply_:
        print("\n(dry-run -- aucune ecriture. Relancer avec --apply --attendu=N pour supprimer.)")
        return

    if attendu is None or nb != attendu:
        sys.exit(f"❌ Garde-fou : {nb} lignes trouvees, --attendu={attendu} -- abandon sans ecrire.")

    print(f"\n✍️ Suppression de {nb} lignes...")
    job = client.query(f"DELETE FROM `{TABLE}` WHERE {FILTRE}")
    job.result()
    print(f"✅ {job.num_dml_affected_rows} ligne(s) supprimee(s).")


if __name__ == "__main__":
    main()
