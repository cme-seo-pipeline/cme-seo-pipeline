"""
CME — Diagnostic (lecture seule) : y a-t-il eu des clics/conversions
recents sur les CTA du site (numero header, formulaire inline, bouton),
suite au constat du 24/10/2026 : 0 ligne dans leads_convertis depuis le
22/10 15:20 UTC.

Objectif : distinguer deux hypotheses sans se fier a une seule source --

  A) Vrai creux de trafic/conversion (peu de visiteurs, ou visiteurs qui
     ne cliquent pas) -- dans ce cas GA4 cote sessions sera lui aussi bas
     ou en baisse, et la colonne "conversions" GA4 (qui tourne
     independamment de leads_convertis, cf. diagnostic du 19/10) sera
     elle aussi a zero ou tres basse sur la meme fenetre.
  B) Regression du relais serveur (meme famille que l'incident IAM du
     19/10 sur Cloud Run cme-tracking-api) -- dans ce cas le trafic GA4
     reste normal (les visiteurs cliquent, l'evenement dataLayer part
     bien et GA4 l'enregistre cote client) mais leads_convertis reste a
     zero (le relais serveur vers Cloud Run/Sheets echoue en silence).

Ne modifie rien, n'envoie aucune requete de test vers le site ou Cloud
Run -- uniquement des lectures BigQuery (leads_convertis + 01_raw.ga4_pages).

Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def run(client, titre, sql):
    print("=" * 70)
    print(titre)
    print("=" * 70)
    try:
        df = client.query(sql).to_dataframe()
        if df.empty:
            print("   (0 ligne)")
        else:
            print(df.to_string(index=False))
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")
    print()


def main():
    client = bigquery.Client(project=PROJECT_ID)

    run(client, "1. Fraicheur du sync GA4 -- derniere date disponible dans ga4_pages", f"""
        SELECT MAX(date) AS derniere_date_synchronisee
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
    """)

    run(client, "2. Trafic + conversions GA4 site entier -- 10 derniers jours synchronises", f"""
        SELECT date,
               SUM(sessions) AS sessions_totales,
               SUM(IFNULL(conversions, 0)) AS conversions_ga4
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        GROUP BY date
        ORDER BY date DESC
        LIMIT 10
    """)

    run(client, "3. Trafic + conversions GA4 -- /contactez-un-expert/ seulement, 10 derniers jours", f"""
        SELECT date,
               SUM(sessions) AS sessions,
               SUM(IFNULL(conversions, 0)) AS conversions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE page_path LIKE '%contactez-un-expert%'
        GROUP BY date
        ORDER BY date DESC
        LIMIT 10
    """)

    run(client, "4. Top pages par conversions GA4 -- 10 derniers jours synchronises", f"""
        SELECT page_path,
               SUM(sessions) AS sessions,
               SUM(IFNULL(conversions, 0)) AS conversions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE date >= DATE_SUB(
            (SELECT MAX(date) FROM `{PROJECT_ID}.01_raw.ga4_pages`), INTERVAL 10 DAY
        )
        GROUP BY page_path
        HAVING conversions > 0
        ORDER BY conversions DESC
        LIMIT 20
    """)

    run(client, "5. leads_convertis -- rappel detail depuis le 20/10 (toutes sources)", f"""
        SELECT timestamp, tool, source_page
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE timestamp >= '2026-10-20'
        ORDER BY timestamp DESC
    """)


if __name__ == "__main__":
    main()
