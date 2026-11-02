"""
CME — Entonnoir complet (vu / etape / abandon / converti) d'une des deux
variantes du mini-formulaire inline (cme-cta-progressifs.php) : le
formulaire de contact classique insere toutes les ~230 mots
(cible/tool='contact'/'contact-expert-inline') ou le bloc "avant d'appeler"
ajoute en fin d'article (cible/tool='appel'/'appel-expert-inline', mis en
ligne le 01/11/2026).

Deux sources distinctes, comme pour le popup header (voir CLAUDE.md,
"Popup header — verification des clics depuis le deploiement") :
  1. leads_convertis (tool=...) : conversions COMPLETES (formulaire rempli
     jusqu'au bouton final).
  2. interactions_contenu (cible=..., type_evenement in form_vu/form_etape/
     form_abandon) : l'ENTONNOIR complet -- vu, etape telephone atteinte,
     abandon, soumis -- disponible pour les DEUX variantes car
     journaliserInteraction() les trace de la meme maniere (contrairement
     au popup header, qui ne log aucun evenement equivalent, cf. CLAUDE.md).

USAGE :
  python3 verifier_entonnoir_formulaire_inline.py --cible=appel     (defaut)
  python3 verifier_entonnoir_formulaire_inline.py --cible=contact

LECTURE SEULE.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"

CIBLE_VERS_TOOL = {
    "appel": "appel-expert-inline",
    "contact": "contact-expert-inline",
}


def main():
    cible = "appel"
    for arg in sys.argv[1:]:
        if arg.startswith("--cible="):
            cible = arg.split("=", 1)[1]

    if cible not in CIBLE_VERS_TOOL:
        sys.exit(f"❌ --cible doit etre 'appel' ou 'contact' (recu : {cible!r})")

    tool = CIBLE_VERS_TOOL[cible]
    client = bigquery.Client(project=PROJECT_ID)

    print(f"📥 1/ leads_convertis, tool='{tool}' (conversions completes)...\n")
    df_leads = client.query(f"""
        SELECT timestamp, prenom, telephone, source_page, source_post_id, details
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE tool = '{tool}'
        ORDER BY timestamp
    """).to_dataframe()

    print(f"✅ {len(df_leads)} lead(s) complet(s) au total (tout l'historique) :")
    for _, row in df_leads.iterrows():
        print(f"  {row['timestamp']}  prenom={row['prenom']!r}  telephone={row['telephone']!r}  source_page={row['source_page']!r}")
    if df_leads.empty:
        print("  (aucun)")

    print("\n" + "=" * 100)
    print(f"📥 2/ interactions_contenu, cible='{cible}' (entonnoir complet : vu / etape / abandon)...\n")
    df_funnel = client.query(f"""
        SELECT type_evenement, etape, COUNT(*) AS nb_evenements, COUNT(DISTINCT session_id) AS nb_sessions
        FROM `{PROJECT_ID}.04_pipeline_seo.interactions_contenu`
        WHERE cible = '{cible}'
        GROUP BY type_evenement, etape
        ORDER BY type_evenement, etape
    """).to_dataframe()

    if df_funnel.empty:
        print(f"⚠️ AUCUN evenement '{cible}' dans interactions_contenu.")
    else:
        print(f"{'type_evenement':<16}{'etape':<10}{'nb_evenements':<16}{'nb_sessions_distinctes'}")
        for _, row in df_funnel.iterrows():
            print(f"{row['type_evenement']:<16}{str(row['etape']):<10}{row['nb_evenements']:<16}{row['nb_sessions']}")

    print("\n" + "=" * 100)
    print(f"📥 3/ Premiere et derniere date d'evenement '{cible}' (tous types), pour contextualiser...\n")
    df_bornes = client.query(f"""
        SELECT MIN(timestamp) AS premier, MAX(timestamp) AS dernier, COUNT(*) AS total
        FROM `{PROJECT_ID}.04_pipeline_seo.interactions_contenu`
        WHERE cible = '{cible}'
    """).to_dataframe()
    if not df_bornes.empty and df_bornes.iloc[0]["total"] > 0:
        print(f"  Premier evenement : {df_bornes.iloc[0]['premier']}")
        print(f"  Dernier evenement : {df_bornes.iloc[0]['dernier']}")
        print(f"  Total tous types  : {df_bornes.iloc[0]['total']}")
    else:
        print("  (aucun evenement)")


if __name__ == "__main__":
    main()
