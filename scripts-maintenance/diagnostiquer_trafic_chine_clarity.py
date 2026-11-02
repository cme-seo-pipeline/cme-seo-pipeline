"""
CME — Diagnostic LECTURE SEULE (repli apres echec GA4, voir
diagnostiquer_trafic_chine_ga4.py -- le compte de service GCP_SA_KEY_CME
n'a pas acces a la propriete GA4, 403 PERMISSION_DENIED sur les 5
rapports) : caracteriser le trafic Chine signale par l'operateur dans
Microsoft Clarity, a partir des donnees DEJA synchronisees en BigQuery
(`04_pipeline_seo.clarity_insights_quotidien` /
`clarity_insights_par_page`, alimentees par rafraichir_clarity_insights()/
rafraichir_clarity_par_page() dans pipeline/pipeline.py).

Limite connue (documentee dans ces 2 fonctions et dans CLAUDE.md) :
l'API Data Export Clarity ne renvoie qu'un ensemble FIXE de metriques
agregees par projet (pas de dimension croisee pays x engagement) -- on ne
pourra donc PAS repondre "quelle duree de session pour les visiteurs
chinois precisement", seulement :
  1. Le poids de la Chine dans la metrique 'Country' (si presente),
     jour par jour sur la fenetre -- un volume anormalement constant/
     lisse est une signature de bot plus credible qu'une vraie
     variabilite organique.
  2. Les metriques globales du site sur la meme fenetre (EngagementTime,
     ScrollDepth, RageClickCount, PopularPages) a titre de contexte --
     pas filtrables par pays, mais utiles pour voir si l'ensemble du site
     montre des signes de pollution par du trafic non-humain.
  3. La liste de TOUS les noms de metriques reellement presents dans la
     table (utile si 'Country' n'existe pas sous ce nom exact ou si
     Clarity a changé son schema depuis la doc de pipeline.py).

USAGE : python3 diagnostiquer_trafic_chine_clarity.py [--jours=14]
"""
import json
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE_QUOTIDIEN = f"{PROJECT_ID}.04_pipeline_seo.clarity_insights_quotidien"
TABLE_PAR_PAGE = f"{PROJECT_ID}.04_pipeline_seo.clarity_insights_par_page"


def main():
    jours = 14
    for arg in sys.argv:
        if arg.startswith("--jours="):
            jours = int(arg.split("=", 1)[1])

    client = bigquery.Client(project=PROJECT_ID)

    print(f"🔎 Fenetre : {jours} derniers jours\n")

    print("=" * 70)
    print("0) NOMS DE METRIQUES PRESENTS DANS LA TABLE (derniers jours)")
    print("=" * 70)
    df_noms = client.query(f"""
        SELECT DISTINCT metric_name
        FROM `{TABLE_QUOTIDIEN}`
        WHERE date_sync >= DATE_SUB(CURRENT_DATE(), INTERVAL {jours} DAY)
        ORDER BY metric_name
    """).to_dataframe()
    print(df_noms.to_string(index=False) if len(df_noms) else "  (aucune ligne)")

    print("\n" + "=" * 70)
    print("1) METRIQUE 'Country' JOUR PAR JOUR (brut, JSON complet)")
    print("=" * 70)
    df_country = client.query(f"""
        SELECT date_sync, information
        FROM `{TABLE_QUOTIDIEN}`
        WHERE metric_name = 'Country'
          AND date_sync >= DATE_SUB(CURRENT_DATE(), INTERVAL {jours} DAY)
        ORDER BY date_sync
    """).to_dataframe()
    if not len(df_country):
        print("  (aucune ligne pour metric_name='Country' -- voir section 0 pour le nom exact disponible)")
    else:
        for _, row in df_country.iterrows():
            try:
                info = json.loads(row["information"])
            except Exception:
                info = row["information"]
            print(f"  {row['date_sync']} : {info}")

    print("\n" + "=" * 70)
    print("2) METRIQUES GLOBALES DU SITE (contexte, non filtrable par pays)")
    print("=" * 70)
    for metrique in ["EngagementTime", "ScrollDepth", "RageClickCount", "PopularPages", "Browser", "Device"]:
        df_m = client.query(f"""
            SELECT date_sync, information
            FROM `{TABLE_QUOTIDIEN}`
            WHERE metric_name = '{metrique}'
              AND date_sync >= DATE_SUB(CURRENT_DATE(), INTERVAL {jours} DAY)
            ORDER BY date_sync
        """).to_dataframe()
        print(f"\n  -- {metrique} --")
        if not len(df_m):
            print("    (aucune ligne)")
            continue
        for _, row in df_m.iterrows():
            try:
                info = json.loads(row["information"])
            except Exception:
                info = row["information"]
            print(f"    {row['date_sync']} : {info}")


if __name__ == "__main__":
    main()
