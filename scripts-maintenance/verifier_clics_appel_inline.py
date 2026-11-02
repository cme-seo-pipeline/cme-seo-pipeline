"""
CME — Demande operateur (03/11) : y a-t-il eu des clics/interactions sur le
mini-formulaire "avant d'appeler" (bloc en fin d'article, tool='appel-expert-inline'
cote leads_convertis, cible='appel' cote interactions_contenu) depuis sa mise
en ligne le 01/11/2026 ?

Deux sources distinctes, comme pour le popup header (voir CLAUDE.md,
"Popup header — verification des clics depuis le deploiement") :
  1. leads_convertis (tool='appel-expert-inline') : conversions COMPLETES
     (formulaire rempli jusqu'au bouton final).
  2. interactions_contenu (cible='appel', type_evenement in form_vu/
     form_etape/form_abandon) : l'ENTONNOIR complet -- vu, etape telephone
     atteinte, abandon, soumis -- disponible pour ce formulaire car
     journaliserInteraction() le trace depuis sa creation (contrairement au
     popup header, qui ne log aucun evenement equivalent, cf. CLAUDE.md).

Exclut le lead de test deja nettoye (0695410020, 02/11 23:09:28 UTC,
supprime de leads_convertis le 02/11 -- ne devrait plus apparaitre, verifie
quand meme par securite).

LECTURE SEULE.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("📥 1/ leads_convertis, tool='appel-expert-inline' (conversions completes)...\n")
    df_leads = client.query(f"""
        SELECT timestamp, prenom, telephone, source_page, source_post_id, details
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE tool = 'appel-expert-inline'
        ORDER BY timestamp
    """).to_dataframe()

    print(f"✅ {len(df_leads)} lead(s) complet(s) au total (tout l'historique) :")
    for _, row in df_leads.iterrows():
        print(f"  {row['timestamp']}  prenom={row['prenom']!r}  telephone={row['telephone']!r}  source_page={row['source_page']!r}")
    if df_leads.empty:
        print("  (aucun)")

    print("\n" + "=" * 100)
    print("📥 2/ interactions_contenu, cible='appel' (entonnoir complet : vu / etape / abandon)...\n")
    df_funnel = client.query(f"""
        SELECT type_evenement, etape, COUNT(*) AS nb_evenements, COUNT(DISTINCT session_id) AS nb_sessions
        FROM `{PROJECT_ID}.04_pipeline_seo.interactions_contenu`
        WHERE cible = 'appel'
        GROUP BY type_evenement, etape
        ORDER BY type_evenement, etape
    """).to_dataframe()

    if df_funnel.empty:
        print("⚠️ AUCUN evenement 'appel' dans interactions_contenu -- soit personne n'a jamais")
        print("   ouvert/fait defiler jusqu'au bloc 'avant d'appeler', soit le tracking de ce bloc")
        print("   n'est pas (encore) actif sur le site live.")
    else:
        print(f"{'type_evenement':<16}{'etape':<10}{'nb_evenements':<16}{'nb_sessions_distinctes'}")
        for _, row in df_funnel.iterrows():
            print(f"{row['type_evenement']:<16}{str(row['etape']):<10}{row['nb_evenements']:<16}{row['nb_sessions']}")

    print("\n" + "=" * 100)
    print("📥 3/ Premiere et derniere date d'evenement 'appel' (tous types), pour contextualiser...\n")
    df_bornes = client.query(f"""
        SELECT MIN(timestamp) AS premier, MAX(timestamp) AS dernier, COUNT(*) AS total
        FROM `{PROJECT_ID}.04_pipeline_seo.interactions_contenu`
        WHERE cible = 'appel'
    """).to_dataframe()
    if not df_bornes.empty and df_bornes.iloc[0]["total"] > 0:
        print(f"  Premier evenement : {df_bornes.iloc[0]['premier']}")
        print(f"  Dernier evenement : {df_bornes.iloc[0]['dernier']}")
        print(f"  Total tous types  : {df_bornes.iloc[0]['total']}")
    else:
        print("  (aucun evenement)")


if __name__ == "__main__":
    main()
