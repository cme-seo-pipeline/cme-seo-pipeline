"""
CME -- Analyse comparative (lecture seule) : le comparateur-energie
augmenterait-il le taux de conversion par rapport au mini-formulaire inline
actuel ('contact-expert-inline'), et quels risques mesurables ?

Demande operateur (17/11/2026), explicitement en amont de toute reprise du
chantier d'integration (aucune action corrective ici, aucune ecriture) :
"je veux savoir en integrant le comparateur, est ce que cela va augmenter
le taux de conversion ou non, et est ce qu'il y a des risques aussi".

Trois sources, toutes lecture seule :
1. leads_convertis, tool LIKE '%comparateur%' ou tool IN des anciens noms
   plausibles -- volume de leads REELS historiques (hors tests), par mois,
   pour voir s'il existe une base de comparaison anterieure a la
   consolidation CTA d'octobre 2026 (voir CLAUDE.md, "Les CTA simulateurs
   -> page de contact unique").
2. 01_raw.ga4_pages -- sessions/pageviews historiques sur la page
   comparateur-energie-electricite-gaz, pour tenter un denominateur reel
   (taux de conversion = leads / sessions, comme pour contact-expert-inline).
3. historique_publications -- pour situer la fenetre temporelle ou le
   comparateur a ete une destination de CTA active (avant le remplacement
   d'octobre par /contactez-un-expert/), par recoupement avec les dates
   GSC/GA4 disponibles sur cette page.

Objectif : fournir un ORDRE DE GRANDEUR reel (pas une estimation theorique)
pour comparer a 0,8% (contact-expert-inline, deja mesure), et documenter
les risques structurels constates (friction formulaire, complexite
technique, risque de regression deja materialise le 16-17/11).
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("📥 1/ leads_convertis -- tous les 'tool' distincts contenant 'comparateur' ou lies aux anciens simulateurs...\n")
    df_tools = client.query(f"""
        SELECT tool, COUNT(*) AS nb, MIN(timestamp) AS premier, MAX(timestamp) AS dernier
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE LOWER(tool) LIKE '%comparateur%'
           OR LOWER(tool) LIKE '%simulateur%'
        GROUP BY tool
        ORDER BY premier
    """).to_dataframe()
    if df_tools.empty:
        print("  ⚠️ Aucune ligne historique trouvee pour un tool comparateur/simulateur (hors ce qui vient d'etre nettoye).")
    else:
        for _, row in df_tools.iterrows():
            print(f"  tool={row['tool']!r:<30} nb={row['nb']:<6} premier={row['premier']}  dernier={row['dernier']}")

    print("\n" + "=" * 100)
    print("📥 2/ Detail mensuel des leads 'comparateur-energie' (hors leads de test identifies le 17/11)...\n")
    df_mensuel = client.query(f"""
        SELECT FORMAT_TIMESTAMP('%Y-%m', timestamp) AS mois, COUNT(*) AS nb_leads
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE tool = 'comparateur-energie'
        GROUP BY mois
        ORDER BY mois
    """).to_dataframe()
    if df_mensuel.empty:
        print("  (aucune ligne -- cohérent si tout l'historique etait fait de tests, deja nettoyes)")
    else:
        for _, row in df_mensuel.iterrows():
            print(f"  {row['mois']}  -> {row['nb_leads']} lead(s)")

    print("\n" + "=" * 100)
    print("📥 3/ Schema de 01_raw.ga4_pages (pour verifier les colonnes disponibles)...\n")
    table_ref = client.dataset("01_raw").table("ga4_pages")
    table = client.get_table(table_ref)
    noms_colonnes = [f.name for f in table.schema]
    print(f"  Colonnes : {noms_colonnes}")

    print("\n" + "=" * 100)
    print("📥 4/ Trafic GA4 historique sur la page comparateur-energie-electricite-gaz (si colonnes trouvees)...\n")
    colonnes_dispo = set(noms_colonnes)
    col_sessions_candidats = [c for c in ["sessions", "sessionCount", "activeUsers", "screenPageViews", "pageviews"] if c in colonnes_dispo]
    if "pagePath" not in colonnes_dispo or not col_sessions_candidats:
        print(f"  ⚠️ Impossible de construire la requete automatiquement -- colonnes candidates trouvees : {col_sessions_candidats}, pagePath present={'pagePath' in colonnes_dispo}")
    else:
        col = col_sessions_candidats[0]
        df_ga4 = client.query(f"""
            SELECT FORMAT_DATE('%Y-%m', date) AS mois, SUM({col}) AS total_{col}
            FROM `{PROJECT_ID}.01_raw.ga4_pages`
            WHERE pagePath LIKE '%comparateur-energie%'
            GROUP BY mois
            ORDER BY mois
        """).to_dataframe()
        if df_ga4.empty:
            print(f"  (aucune ligne GA4 pour cette page -- colonne utilisee : {col})")
        else:
            print(f"  (colonne utilisee : {col})")
            for _, row in df_ga4.iterrows():
                print(f"  {row['mois']}  -> {row[f'total_{col}']}")

    print("\n" + "=" * 100)
    print("📥 5/ Pour comparaison directe -- rappel du denominateur contact-expert-inline (deja mesure le 17/11) :\n")
    print("  15 leads / 1887 sessions ayant vu le mini-formulaire ≈ 0,8%")


if __name__ == "__main__":
    main()
