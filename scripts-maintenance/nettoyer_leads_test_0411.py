"""
CME — Nettoie (apres validation operateur) les 3 leads de test generes le
04/11/2026 lors de la verification en conditions reelles du nouveau
formulaire a un seul ecran (wordpress-mu-plugins/cme-cta-progressifs.php)
et du popup header (cme-tracking-conversion.php). Meme numero de test que
les incidents precedents ("Lionel"/"QA-TEST"/popup header, voir CLAUDE.md) :
0695410020.

Cible par TIMESTAMP EXACT (pas un simple filtre sur le numero, pour ne
jamais risquer de toucher une autre ligne) -- les 3 timestamps viennent de
diagnostiquer_leads_test_0411.py :
  - 2026-11-04 18:43:58.875618 UTC (tool=appel-expert-inline)
  - 2026-11-04 18:44:07.874395 UTC (tool=contact-expert-inline)
  - 2026-11-04 18:44:32.072074 UTC (tool=appel-header-formulaire)

DRY-RUN PAR DEFAUT -- n'affiche que ce qui SERAIT supprime.
Suppression reelle : --apply --confirmation=SUPPRIMER

Le Sheet "Leads Formulaire Article" correspondant est nettoye separement
et manuellement par l'operateur (pas d'acces API Sheets depuis ce
sandbox, meme precedent que les incidents cites plus haut).

USAGE :
  python3 nettoyer_leads_test_0411.py                              # dry-run
  python3 nettoyer_leads_test_0411.py --apply --confirmation=SUPPRIMER
"""
import sys

from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"
TABLE = f"{PROJECT_ID}.{DATASET_ID}.leads_convertis"

NUMERO_TEST = "0695410020"
TIMESTAMPS_CIBLES = [
    "2026-11-04 18:43:58.875618",
    "2026-11-04 18:44:07.874395",
    "2026-11-04 18:44:32.072074",
]


def parse_args():
    apply = "--apply" in sys.argv[1:]
    confirmation = ""
    for arg in sys.argv[1:]:
        if arg.startswith("--confirmation="):
            confirmation = arg.split("=", 1)[1]
    return apply, confirmation


def main():
    apply, confirmation = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    ts_list = ", ".join(f"TIMESTAMP('{t}')" for t in TIMESTAMPS_CIBLES)

    print("Lignes correspondant exactement aux timestamps cibles (verification avant suppression) :")
    df = client.query(f"""
        SELECT timestamp, tool, prenom, telephone, details
        FROM `{TABLE}`
        WHERE timestamp IN ({ts_list}) AND telephone = '{NUMERO_TEST}'
        ORDER BY timestamp
    """).to_dataframe()
    if df.empty:
        print("  (aucune ligne trouvee -- rien a supprimer, peut-etre deja nettoye)")
        return
    for _, r in df.iterrows():
        print(f"  {r['timestamp']} | tool={r['tool']} | prenom={r['prenom']!r} | tel={r['telephone']!r} | details={r['details']}")
    print(f"\n{len(df)} ligne(s) correspondante(s).")

    if not apply:
        print("\n[DRY-RUN] Aucune suppression effectuee. Relancer avec --apply --confirmation=SUPPRIMER pour supprimer reellement.")
        return

    if confirmation != "SUPPRIMER":
        sys.exit("❌ --apply requiert --confirmation=SUPPRIMER (garde-fou, suppression permanente)")

    job = client.query(f"""
        DELETE FROM `{TABLE}`
        WHERE timestamp IN ({ts_list}) AND telephone = '{NUMERO_TEST}'
    """)
    job.result()
    print(f"\n✅ {job.num_dml_affected_rows} ligne(s) supprimee(s) de leads_convertis.")


if __name__ == "__main__":
    main()
