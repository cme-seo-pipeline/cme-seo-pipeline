"""
CME -- Nettoyage de 4 leads de TEST crees dans leads_convertis le 16/11/2026
pendant la session de validation/diagnostic du comparateur-energie (chantier
revert d'urgence du 16-17/11, voir CLAUDE.md) -- demande operateur explicite
le 17/11/2026 : "la suppression de ces 4 tests depuis BigQuery", avec le
detail exact des 4 lignes colle dans la conversation.

Les 4 lignes cibles (tool='comparateur-energie' dans leads_convertis,
source_page='comparateur-energie-electricite-gaz') :
  1. 16:02:35 UTC -- prenom='TEST-DIAGNOSTIC', telephone='06 00 00 00 00',
     email de test @example.invalid -- lead synthetique d'un script de
     diagnostic du relais (pas un vrai navigateur).
  2-4. 18:19:31 / 18:58:29 / 19:19:32 UTC -- prenom='Oussama Blal', meme
     telephone '2126 94 37 49 91' -- tests manuels de l'operateur sur le
     comparateur (Engie/Primeo Energie/Alpiq), avant la decouverte du bug
     catastrophique qui a mene au revert complet le meme soir.

Identification PRECISE par (tool, timestamp tronque a la seconde,
telephone) -- pas un filtre large par telephone de test seul, pour ne
retirer QUE ces 4 lignes exactes, aucune autre (meme principe que les
nettoyages de leads de test precedents : nettoyer_leads_test_0211_0302.py,
nettoyer_leads_test_popup_header.py). TIMESTAMP_TRUNC(..., SECOND) car
l'operateur a colle des valeurs a la seconde (sans microsecondes) -- la
colonne reelle en a probablement, une egalite stricte sans troncature
ne matcherait jamais.

Dry-run par defaut (affiche les lignes qui seraient supprimees).
--apply --confirmation=NETTOYAGE-COMPARATEUR-1611 pour executer la
suppression reelle. Necessite les credentials GCP (GOOGLE_APPLICATION_CREDENTIALS,
deja configures par le workflow GitHub Actions -- jamais en dur ici).
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"

# (timestamp UTC a la seconde, telephone) -- cle d'identification precise
CIBLES = [
    ("2026-11-16 16:02:35", "06 00 00 00 00"),
    ("2026-11-16 18:19:31", "2126 94 37 49 91"),
    ("2026-11-16 18:58:29", "2126 94 37 49 91"),
    ("2026-11-16 19:19:32", "2126 94 37 49 91"),
]


def clause_sql():
    parties = []
    for ts, tel in CIBLES:
        tel_sql = tel.replace("'", "\\'")
        parties.append(
            f"(TIMESTAMP_TRUNC(timestamp, SECOND) = TIMESTAMP('{ts}') AND telephone = '{tel_sql}')"
        )
    return " OR ".join(parties)


def main():
    apply_mode = "--apply" in sys.argv
    confirmation = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--confirmation=")), "")

    if apply_mode and confirmation != "NETTOYAGE-COMPARATEUR-1611":
        sys.exit("❌ --apply necessite --confirmation=NETTOYAGE-COMPARATEUR-1611 (garde-fou volontaire).")

    client = bigquery.Client(project=PROJECT_ID)
    where = f"tool = 'comparateur-energie' AND ({clause_sql()})"

    print(f"📥 Verification des {len(CIBLES)} ligne(s) ciblee(s) dans leads_convertis...\n")
    df = client.query(f"""
        SELECT timestamp, tool, prenom, nom, email, telephone,
               JSON_EXTRACT_SCALAR(details, '$.fournisseur') AS fournisseur,
               JSON_EXTRACT_SCALAR(details, '$.offre') AS offre,
               source_page
        FROM `{TABLE}`
        WHERE {where}
        ORDER BY timestamp
    """).to_dataframe()

    print(f"✅ {len(df)} ligne(s) trouvee(s) sur {len(CIBLES)} cible(s) :\n")
    print("=" * 110)
    for _, row in df.iterrows():
        print(f"  {row['timestamp']}  prenom={row['prenom']!r}  nom={row['nom']!r}  tel={row['telephone']!r}  "
              f"email={row['email']!r}  fournisseur={row['fournisseur']!r}  offre={row['offre']!r}")
    print("=" * 110)

    if len(df) != len(CIBLES):
        print(f"\n⚠️ ATTENTION : {len(CIBLES) - len(df)} cible(s) introuvable(s) -- deja supprimee(s) ou ecart de donnees.")
        if apply_mode:
            sys.exit("❌ Abandon de --apply : le nombre de lignes trouvees ne correspond pas au nombre de cibles. Verifier manuellement avant de reessayer.")

    if not apply_mode:
        print("\n(dry-run -- relancer avec --apply --confirmation=NETTOYAGE-COMPARATEUR-1611 pour supprimer reellement ces lignes)")
        return

    print(f"\n🗑️  Suppression de {len(df)} ligne(s)...")
    job = client.query(f"""
        DELETE FROM `{TABLE}`
        WHERE {where}
    """)
    job.result()
    print(f"✅ Suppression terminee ({job.num_dml_affected_rows} ligne(s) affectee(s)).")


if __name__ == "__main__":
    main()
