"""
CME — Nettoyage des leads de test crees pendant la session de validation du
correctif telephone/code_postal (02-03/11/2026, commit 5b0bcfd). Demande
operateur explicite : "tu m'affiches les comptes de test pour le nettoyage
au niveau de bigquery et moi je nettoie sheets" -- ce script gere le cote
BigQuery (leads_convertis), le Sheet est nettoye manuellement par
l'operateur (pas d'acces API Sheets depuis ce sandbox).

Les 9 lignes ciblees (voir diagnostiquer_tests_formulaires_0211.py pour le
detail complet) sont TOUTES des leads de test, identifiees par leur
timestamp exact (pas par un filtre large type "telephone de test", pour
etre certain de ne supprimer QUE ces lignes precises, aucune autre) :
  - 2 lignes du bug de double comptage (22:40, avant le fix du 02/11)
  - 2 lignes du meme bug reproduit (22:58, navigateur avec JS en cache)
  - 1 ligne du bug telephone/code_postal inverse (23:01, avant le fix du 03/11)
  - 4 lignes de validation finale, tous formulaires (23:07-23:09, apres le
    fix du 03/11 -- confirment que tout fonctionne, mais restent des
    donnees de test, pas de vrais leads)

Dry-run par defaut (affiche les lignes qui seraient supprimees et leur
nombre). --apply --confirmation=NETTOYAGE-TESTS-0302 pour executer
reellement la suppression.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"

TIMESTAMPS_A_SUPPRIMER = [
    "2026-11-02 22:40:22.487000+00:00",
    "2026-11-02 22:40:23.791000+00:00",
    "2026-11-02 22:58:44.531000+00:00",
    "2026-11-02 22:58:45.534000+00:00",
    "2026-11-02 23:01:57.678000+00:00",
    "2026-11-02 23:07:57.623000+00:00",
    "2026-11-02 23:09:16.154887+00:00",
    "2026-11-02 23:09:28.935832+00:00",
    "2026-11-02 23:09:49.762325+00:00",
]


def main():
    apply_mode = "--apply" in sys.argv
    confirmation = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--confirmation=")), "")

    if apply_mode and confirmation != "NETTOYAGE-TESTS-0302":
        sys.exit("❌ --apply necessite --confirmation=NETTOYAGE-TESTS-0302 (garde-fou volontaire).")

    client = bigquery.Client(project=PROJECT_ID)
    liste_sql = ", ".join(f"TIMESTAMP('{t}')" for t in TIMESTAMPS_A_SUPPRIMER)

    print(f"📥 Verification des {len(TIMESTAMPS_A_SUPPRIMER)} ligne(s) ciblee(s) dans leads_convertis...\n")
    df = client.query(f"""
        SELECT timestamp, tool, prenom, telephone, email, code_postal, source_page
        FROM `{TABLE}`
        WHERE timestamp IN ({liste_sql})
        ORDER BY timestamp
    """).to_dataframe()

    print(f"✅ {len(df)} ligne(s) trouvee(s) sur {len(TIMESTAMPS_A_SUPPRIMER)} timestamp(s) cible(s) :\n")
    print("=" * 100)
    for _, row in df.iterrows():
        print(f"  {row['timestamp']}  tool={row['tool']!r}  prenom={row['prenom']!r}  telephone={row['telephone']!r}  code_postal={row['code_postal']!r}")
    print("=" * 100)

    if len(df) != len(TIMESTAMPS_A_SUPPRIMER):
        print(f"\n⚠️ ATTENTION : {len(TIMESTAMPS_A_SUPPRIMER) - len(df)} timestamp(s) cible(s) introuvable(s) -- deja supprime(s) ou decalage de precision.")

    if not apply_mode:
        print("\n(dry-run -- relancer avec --apply --confirmation=NETTOYAGE-TESTS-0302 pour supprimer reellement ces lignes)")
        return

    print(f"\n🗑️  Suppression de {len(df)} ligne(s)...")
    job = client.query(f"""
        DELETE FROM `{TABLE}`
        WHERE timestamp IN ({liste_sql})
    """)
    job.result()
    print(f"✅ Suppression terminee ({job.num_dml_affected_rows} ligne(s) affectee(s)).")


if __name__ == "__main__":
    main()
