"""
CME — Synthese du comportement des visiteurs -> tunnel de conversion
(lecture seule).

Demande operateur du 25/10/2026 : exploiter TOUTES les sources de donnees
deja en place qui capturent du comportement visiteur (pas seulement
leads_convertis), pour en degager une synthese actionnable visant un taux
de conversion de 1% des sessions en leads. Sources exploitees :

1. `04_pipeline_seo.tunnel_conversion_unifie` (vue deja existante dans le
   projet, scripts-maintenance/tunnel_conversion_unifie.sh) -- joint deja
   GSC (impressions/clics/position) + GA4 (sessions/bounce_rate) + Clarity
   (rage clicks, scroll depth) + leads_convertis/leads_app_authentifies
   par post_id/URL. C'est la table la plus proche d'une synthese deja
   prete pour ce besoin -- on l'exploite en priorite plutot que de
   reconstruire les jointures a la main.
2. `04_pipeline_seo.clarity_insights_quotidien` -- metriques Microsoft
   Clarity au niveau du site entier (engagement, device, frustration :
   rage clicks, dead clicks, quickback, erreurs JS, scroll excessif).
3. `01_raw.ga4_pages` -- trafic/sessions/bounce/device sur 30 jours.
4. `04_pipeline_seo.leads_convertis` -- taux de conversion reel, detail
   recent.

LECTURE SEULE. Necessite GOOGLE_APPLICATION_CREDENTIALS.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def run(client, titre, sql):
    print("\n" + "=" * 70)
    print(titre)
    print("=" * 70)
    try:
        df = client.query(sql).to_dataframe()
        if df.empty:
            print("   (0 ligne)")
        else:
            print(df.to_string(index=False))
        return df
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")
        return None


def main():
    client = bigquery.Client(project=PROJECT_ID)

    run(client, "0. Fraicheur des sources (derniere date synchronisee)", f"""
        SELECT
          (SELECT MAX(date) FROM `{PROJECT_ID}.01_raw.ga4_pages`) AS ga4_pages,
          (SELECT MAX(date) FROM `{PROJECT_ID}.01_raw.gsc_queries`) AS gsc_queries,
          (SELECT MAX(date_sync) FROM `{PROJECT_ID}.04_pipeline_seo.clarity_insights_quotidien`) AS clarity_quotidien,
          (SELECT MAX(date_sync) FROM `{PROJECT_ID}.04_pipeline_seo.clarity_insights_par_page`) AS clarity_par_page,
          (SELECT MAX(timestamp) FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`) AS leads_convertis
    """)

    run(client, "1. Vue d'ensemble -- sessions, leads, taux de conversion global (30 derniers jours)", f"""
        SELECT
          SUM(sessions) AS sessions_totales_30j,
          SUM(nb_leads) AS leads_totaux,
          ROUND(100.0 * SUM(nb_leads) / GREATEST(SUM(sessions), 1), 3) AS taux_conversion_pct,
          ROUND(100.0 * SUM(nb_leads) / GREATEST(SUM(sessions), 1) / 1.0, 3) AS objectif_1pct_ecart
        FROM `{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie`
    """)

    run(client, "2. Top 20 pages par trafic -- sessions, rebond, rage clicks, scroll, leads", f"""
        SELECT url, sessions, bounce_rate_pct, rage_click_sessions, scroll_depth_moyen, nb_leads
        FROM `{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie`
        WHERE sessions > 0
        ORDER BY sessions DESC
        LIMIT 20
    """)

    run(client, "3. Pages a FORT trafic mais AUCUN lead (candidates prioritaires d'amelioration)", f"""
        SELECT url, sessions, bounce_rate_pct, rage_click_sessions, scroll_depth_moyen
        FROM `{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie`
        WHERE sessions >= 5 AND nb_leads = 0
        ORDER BY sessions DESC
        LIMIT 20
    """)

    run(client, "4. Pages qui CONVERTISSENT deja (a comprendre pour repliquer)", f"""
        SELECT url, sessions, bounce_rate_pct, rage_click_sessions, scroll_depth_moyen, nb_leads,
               ROUND(100.0 * nb_leads / GREATEST(sessions, 1), 2) AS taux_conversion_pct
        FROM `{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie`
        WHERE nb_leads > 0
        ORDER BY taux_conversion_pct DESC
        LIMIT 20
    """)

    run(client, "5. Signal de frustration -- pages avec rage clicks recents", f"""
        SELECT url, sessions, rage_click_sessions, bounce_rate_pct
        FROM `{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie`
        WHERE rage_click_sessions > 0
        ORDER BY rage_click_sessions DESC
        LIMIT 20
    """)

    run(client, "6. Scroll depth -- distribution (les visiteurs lisent-ils jusqu'au formulaire ?)", f"""
        SELECT
          COUNT(*) AS nb_pages_avec_donnee,
          ROUND(AVG(scroll_depth_moyen), 1) AS scroll_moyen_global,
          ROUND(MIN(scroll_depth_moyen), 1) AS scroll_min,
          ROUND(MAX(scroll_depth_moyen), 1) AS scroll_max
        FROM `{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie`
        WHERE scroll_depth_moyen IS NOT NULL
    """)

    run(client, "7. Clarity -- metriques globales projet, dernieres disponibles (engagement/frustration/device)", f"""
        SELECT date_sync, metric_name, information
        FROM `{PROJECT_ID}.04_pipeline_seo.clarity_insights_quotidien`
        WHERE date_sync = (SELECT MAX(date_sync) FROM `{PROJECT_ID}.04_pipeline_seo.clarity_insights_quotidien`)
        ORDER BY metric_name
    """)

    run(client, "8. Repartition device (GA4, 14 derniers jours) -- mobile vs desktop", f"""
        SELECT device_category, SUM(sessions) AS sessions, ROUND(AVG(bounce_rate) * 100, 1) AS bounce_pct
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE date >= DATE_SUB((SELECT MAX(date) FROM `{PROJECT_ID}.01_raw.ga4_pages`), INTERVAL 14 DAY)
        GROUP BY device_category
        ORDER BY sessions DESC
    """)

    run(client, "9. Requetes GSC a fort volume mais faible CTR (contenu qui n'accroche pas au clic)", f"""
        SELECT query, SUM(impressions) AS impressions, SUM(clics) AS clics,
               ROUND(100.0 * SUM(clics) / GREATEST(SUM(impressions), 1), 2) AS ctr_pct,
               ROUND(AVG(position), 1) AS position_moyenne
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB((SELECT MAX(date) FROM `{PROJECT_ID}.01_raw.gsc_queries`), INTERVAL 30 DAY)
        GROUP BY query
        HAVING impressions >= 50
        ORDER BY ctr_pct ASC
        LIMIT 15
    """)

    run(client, "10. Detail des vrais leads recents (contexte qualitatif)", f"""
        SELECT timestamp, tool, source_page, source_post_id, details
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE tool NOT IN ('diagnostic-relais-test', 'qa-diagnostic-sheets')
        ORDER BY timestamp DESC
        LIMIT 20
    """)


if __name__ == "__main__":
    main()
