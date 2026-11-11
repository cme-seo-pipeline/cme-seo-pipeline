"""
CME — Suppression de 4 lignes de test dans leads_convertis, confirmees par
l'operateur le 11/11/2026 ("on supprime ces lignes, car on a ete mes
tests") suite a l'export du meme jour
(export_leads_depuis_0111_et_articles_top.py) : 2 paires a 1 seconde
d'intervalle le 02/11 (13:08 et 13:31), tool='contact-expert-formulaire',
tous les champs vides (prenom/telephone/email/code_postal), alternant
/contactez-un-expert/ et /demande-confirmee/ -- signature du bug de
double-comptage du formulaire de contact documente/corrige ce meme jour
(voir CLAUDE.md, "Leads du vrai formulaire de contact -- double comptage").
Ce sont les 4 seules lignes de ce tool sur toute la table (confirme par
verifier_leads_formulaire_contact_expert.py le 02/11 : "4 lignes sur 60
jours, toutes du jour meme").

Filtre volontairement resserre (tool + date + champs vides) plutot que des
timestamps en dur, mais le dry-run AFFICHE chaque ligne avec son timestamp
complet (microseconde) pour verification visuelle avant tout --apply --
meme garde-fou qu'avant : si le dry-run ne montre pas exactement les 4
lignes attendues, ne pas lancer --apply.

Dry-run par defaut. --apply --confirmation=SUPPRESSION-TEST-0211 pour
executer reellement la suppression. Le Sheet correspondant est nettoye
manuellement par l'operateur (pas d'acces API Sheets depuis ce sandbox --
meme precedent que les incidents "Lionel"/"QA-TEST popup header").
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"

WHERE_CLAUSE = """
    tool = 'contact-expert-formulaire'
    AND DATE(timestamp) = '2026-11-02'
    AND (prenom IS NULL OR TRIM(prenom) = '')
    AND (telephone IS NULL OR TRIM(telephone) = '')
"""


def main():
    apply_mode = "--apply" in sys.argv
    confirmation = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--confirmation=")), "")

    if apply_mode and confirmation != "SUPPRESSION-TEST-0211":
        sys.exit("❌ --apply necessite --confirmation=SUPPRESSION-TEST-0211 (garde-fou volontaire).")

    client = bigquery.Client(project=PROJECT_ID)

    print("📥 Lignes correspondant au filtre (contact-expert-formulaire, 02/11, champs vides) :\n")
    df = client.query(f"""
        SELECT timestamp, tool, prenom, telephone, email, code_postal, source_page
        FROM `{TABLE}`
        WHERE {WHERE_CLAUSE}
        ORDER BY timestamp
    """).to_dataframe()

    print("=" * 100)
    for _, row in df.iterrows():
        print(f"  {row['timestamp']}  tool={row['tool']!r}  prenom={row['prenom']!r}  telephone={row['telephone']!r}  page={row['source_page']!r}")
    print("=" * 100)
    print(f"\n✅ {len(df)} ligne(s) trouvee(s) (attendu : 4, voir le constat du 02/11 -- 4 lignes au total pour ce tool, toutes ce jour-la).")

    if len(df) != 4:
        print("\n⚠️ ATTENTION : le nombre de lignes ne correspond pas aux 4 attendues -- ne pas appliquer sans revalider manuellement.")

    if not apply_mode:
        print("\n(dry-run -- relancer avec --apply --confirmation=SUPPRESSION-TEST-0211 pour supprimer reellement ces lignes)")
        return

    print(f"\n🗑️  Suppression de {len(df)} ligne(s)...")
    job = client.query(f"""
        DELETE FROM `{TABLE}`
        WHERE {WHERE_CLAUSE}
    """)
    job.result()
    print(f"✅ Suppression terminee ({job.num_dml_affected_rows} ligne(s) affectee(s)).")


if __name__ == "__main__":
    main()
