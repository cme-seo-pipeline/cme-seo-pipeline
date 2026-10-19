"""
CME — Etat des lieux trafic + conversion (lecture seule).

Prepare l'etude "augmenter le trafic et la conversion" demandee par
l'operateur. Verifie en particulier une hypothese cle : depuis la
migration des CTA vers /contactez-un-expert/ (chantier oct. 2026), plus
aucun systeme ne journalise de conversion (ni soumission de formulaire, ni
clic sur le numero de telephone du header) -- log-lead/log-clic dans
tracking-api/server.py ne sont appeles QUE par le JS des 3 anciens
simulateurs, qui ne sont plus les destinations des CTA. Ce script mesure
l'ampleur du trou (combien de trafic atterrit sur la page de contact sans
qu'on sache ce qui s'y passe) plutot que de le supposer.

Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("="*70)
    print("1. leads_convertis — derniere activite, par mois")
    print("="*70)
    try:
        df = client.query(f"""
            SELECT FORMAT_TIMESTAMP('%Y-%m', timestamp) AS mois, tool, COUNT(*) AS nb_leads
            FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
            GROUP BY mois, tool
            ORDER BY mois DESC, nb_leads DESC
            LIMIT 20
        """).to_dataframe()
        print(df.to_string())
    except Exception as e:
        print(f"⚠️ Erreur : {e}")

    print("\n" + "="*70)
    print("2. Trafic + conversions GA4 — /contactez-un-expert/ (donnees synchronisees)")
    print("="*70)
    try:
        df = client.query(f"""
            SELECT date, sessions, page_views, bounce_rate, conversions
            FROM `{PROJECT_ID}.01_raw.ga4_pages`
            WHERE page_path LIKE '%contactez-un-expert%'
            ORDER BY date DESC
            LIMIT 60
        """).to_dataframe()
        if df.empty:
            print("⚠️ Aucune ligne GA4 pour cette page -- elle n'apparait meme pas dans le sync.")
        else:
            print(f"Total sessions : {int(df['sessions'].sum())} — Total conversions (GA4) : {int(df['conversions'].sum())}")
            print(df.to_string())
    except Exception as e:
        print(f"⚠️ Erreur : {e}")

    print("\n" + "="*70)
    print("2bis. Conversions GA4 (colonne native) — site entier, 30 derniers jours synchronises")
    print("="*70)
    try:
        df = client.query(f"""
            SELECT page_path, SUM(sessions) AS sessions, SUM(conversions) AS conversions
            FROM `{PROJECT_ID}.01_raw.ga4_pages`
            GROUP BY page_path
            HAVING conversions > 0
            ORDER BY conversions DESC
            LIMIT 20
        """).to_dataframe()
        if df.empty:
            print("⚠️ AUCUNE page n'a de conversions GA4 > 0 sur toute la periode synchronisee.")
        else:
            print(df.to_string())
    except Exception as e:
        print(f"⚠️ Erreur : {e}")

    print("\n" + "="*70)
    print("3. Trafic global du site — tendance sur les 60 derniers jours (GA4)")
    print("="*70)
    try:
        df = client.query(f"""
            SELECT date, SUM(sessions) AS sessions_totales
            FROM `{PROJECT_ID}.01_raw.ga4_pages`
            GROUP BY date
            ORDER BY date DESC
            LIMIT 60
        """).to_dataframe()
        print(df.to_string())
    except Exception as e:
        print(f"⚠️ Erreur : {e}")

    print("\n" + "="*70)
    print("4. vue_arbre_performance — rollup par silo (si disponible)")
    print("="*70)
    try:
        df = client.query(f"""
            SELECT *
            FROM `{PROJECT_ID}.04_pipeline_seo.vue_arbre_performance`
            LIMIT 10
        """).to_dataframe()
        print(df.to_string())
    except Exception as e:
        print(f"⚠️ Erreur : {e}")


if __name__ == "__main__":
    main()
