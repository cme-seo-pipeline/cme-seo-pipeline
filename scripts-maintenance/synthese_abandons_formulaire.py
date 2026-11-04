"""
CME — Synthese (lecture seule) des abandons du mini-formulaire inline
(cme-cta-progressifs.php, cf. CLAUDE.md), demande operateur du 04/11/2026
("pour l'abandon du formulaire, est-ce qu'on peut sortir des stats").

Table source : 04_pipeline_seo.interactions_contenu.
Un 'form_abandon' est journalise au plus une fois par page-hide si la
derniere etape connue a progresse au-dela de l'etape 0 (nom/prenom) sans
avoir atteint 'termine' -- voir journaliserInteraction()/visibilitychange
dans cme-cta-progressifs.php. cible = 'contact' ou 'appel' (variante du
formulaire). position_contenu = numero d'occurrence du formulaire dans
l'article (1er, 2e, 3e bouton rencontre), PAS un nombre de mots pour ce
type d'evenement (different de clic_contenu/lecture_position).

Complete les entonnoirs deja suivis par
verifier_entonnoir_formulaire_inline.py (vu/etape/abandon par variante)
et diagnostiquer_entonnoir_par_silo.py (par silo) avec une vue dediee
abandon : par etape, par position d'occurrence, par silo, et le detail
ligne a ligne pour une lecture qualitative (volume encore faible).

LECTURE SEULE -- aucune ecriture. Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 synthese_abandons_formulaire.py [--depuis=2026-10-28]
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"
TABLE = f"{PROJECT_ID}.{DATASET_ID}.interactions_contenu"

DEPUIS_DEFAUT = "2026-10-28"


def parse_args():
    depuis = DEPUIS_DEFAUT
    for arg in sys.argv[1:]:
        if arg.startswith("--depuis="):
            depuis = arg.split("=", 1)[1]
    return depuis


def main():
    depuis = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print(f"📅 Fenetre : depuis le {depuis}\n")

    print("=" * 90)
    print("1/ Abandons par variante (cible) et etape atteinte avant abandon")
    print("=" * 90)
    df1 = client.query(f"""
        SELECT COALESCE(NULLIF(cible,''),'(vide)') AS variante, etape,
               COUNT(*) AS n, COUNT(DISTINCT session_id) AS sessions
        FROM `{TABLE}`
        WHERE DATE(timestamp) >= '{depuis}' AND type_evenement = 'form_abandon'
        GROUP BY variante, etape
        ORDER BY variante, etape
    """).to_dataframe()
    if df1.empty:
        print("  ⚠️ Aucun form_abandon sur cette fenetre.")
    else:
        for _, r in df1.iterrows():
            print(f"  {r['variante']:<12} | etape={r['etape']:<10} : {int(r['n'])} abandon(s), {int(r['sessions'])} session(s)")

    print("\n" + "=" * 90)
    print("2/ Abandons par silo")
    print("=" * 90)
    df2 = client.query(f"""
        SELECT COALESCE(NULLIF(silo,''),'(vide)') AS silo, COUNT(*) AS n
        FROM `{TABLE}`
        WHERE DATE(timestamp) >= '{depuis}' AND type_evenement = 'form_abandon'
        GROUP BY silo
        ORDER BY n DESC
    """).to_dataframe()
    if df2.empty:
        print("  (aucun)")
    else:
        for _, r in df2.iterrows():
            print(f"  {r['silo']:<22} : {int(r['n'])} abandon(s)")

    print("\n" + "=" * 90)
    print("3/ Abandons par position d'occurrence du formulaire dans l'article")
    print("=" * 90)
    df3 = client.query(f"""
        SELECT position_contenu AS occurrence, COUNT(*) AS n
        FROM `{TABLE}`
        WHERE DATE(timestamp) >= '{depuis}' AND type_evenement = 'form_abandon'
        GROUP BY occurrence
        ORDER BY occurrence
    """).to_dataframe()
    if df3.empty:
        print("  (aucun)")
    else:
        for _, r in df3.iterrows():
            print(f"  occurrence n°{int(r['occurrence'])} : {int(r['n'])} abandon(s)")

    print("\n" + "=" * 90)
    print("4/ Detail ligne a ligne (volume encore faible -- lecture qualitative)")
    print("=" * 90)
    df4 = client.query(f"""
        SELECT timestamp, COALESCE(NULLIF(cible,''),'(vide)') AS variante, etape,
               COALESCE(NULLIF(silo,''),'(vide)') AS silo, position_contenu AS occurrence,
               source_page, source_post_id, session_id
        FROM `{TABLE}`
        WHERE DATE(timestamp) >= '{depuis}' AND type_evenement = 'form_abandon'
        ORDER BY timestamp
    """).to_dataframe()
    if df4.empty:
        print("  (aucun)")
    else:
        for _, r in df4.iterrows():
            print(f"  {r['timestamp']} | {r['variante']} | etape={r['etape']} | {r['silo']} | occ#{int(r['occurrence'])} | post_id={r['source_post_id']} | {r['source_page']}")

    print("\n" + "=" * 90)
    print("5/ Contexte -- rapport abandon / etape-telephone-atteinte / soumis, par variante")
    print("=" * 90)
    df5 = client.query(f"""
        SELECT COALESCE(NULLIF(cible,''),'(vide)') AS variante, type_evenement, etape, COUNT(*) AS n
        FROM `{TABLE}`
        WHERE DATE(timestamp) >= '{depuis}'
          AND type_evenement IN ('form_etape', 'form_abandon')
          AND (etape IS NULL OR etape != '0')
        GROUP BY variante, type_evenement, etape
        ORDER BY variante, type_evenement, etape
    """).to_dataframe()
    if df5.empty:
        print("  (aucun)")
    else:
        for _, r in df5.iterrows():
            print(f"  {r['variante']:<12} | {r['type_evenement']:<14} | etape={r['etape']:<10} : {int(r['n'])}")


if __name__ == "__main__":
    main()
