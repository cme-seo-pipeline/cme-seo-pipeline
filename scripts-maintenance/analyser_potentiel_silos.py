"""
CME — Match par silo : trafic organique SEO vs potentiel de conversion leads.

Demande operateur du 26/10/2026 : avant que la nouvelle instrumentation
`interactions_contenu` (cartographie des clics / abandon par etape du
formulaire, voir CLAUDE.md section "Cartographie des clics...") n'ait
accumule assez de trafic pour etre exploitable, preparer une lecture
complementaire qui, elle, EST deja exploitable avec les donnees existantes :
par silo (et sous-silo), quel est le trafic organique SEO (impressions/
clics/position GSC) en regard du potentiel de conversion reel (sessions ->
leads) ? Objectif : reperer les silos a fort trafic mais faible conversion
(optimiser le tunnel plutot que chercher plus de trafic) vs les silos a
trafic plus modeste mais forte conversion (candidats a pousser en SEO,
investissement avec le meilleur retour marginal).

Source de donnees : reutilise la vue deja existante
`04_pipeline_seo.tunnel_conversion_unifie` (voir
scripts-maintenance/tunnel_conversion_unifie.sh) qui joint deja GSC
(impressions/clics/position, 30j) + GA4 (sessions, 30j) + leads_convertis/
leads_app_authentifies (nb_leads, par post_id -- donc uniquement les leads
attribuables a un article precis, essentiellement contact-expert-inline ;
les leads du vrai formulaire de contact et les appels telephoniques ne sont
pas attribuables a un article/silo precis et sont volontairement hors
perimetre ici). Pas de nouvelle jointure a reconstruire -- le silo est
derive de `url` par le meme decoupage de prefixe que celui deja utilise
cote JS par `cme-cta-progressifs.php` (PAR_PREFIXE : gaz / electricite /
aide-energetique / renovation-energetique / solaire).

LECTURE SEULE. Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement
(fourni par le runner GitHub Actions via maintenance-a-la-demande.yml).
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
VUE = f"{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie"

# Meme decoupage de prefixe que PAR_PREFIXE dans cme-cta-progressifs.php
SILO_CASE_SQL = """
  CASE REGEXP_EXTRACT(url, r'(?:https?://)?(?:www\\.)?[^/]+/([a-z0-9-]+)/')
    WHEN 'gaz' THEN 'Gaz'
    WHEN 'electricite' THEN 'Électricité'
    WHEN 'aide-energetique' THEN 'Aides énergétiques'
    WHEN 'renovation-energetique' THEN 'Rénovation énergétique'
    WHEN 'solaire' THEN 'Solaire'
    ELSE 'Autre / hors silo'
  END
"""


def run(client, titre, sql):
    print("\n" + "=" * 78)
    print(titre)
    print("=" * 78)
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

    run(client, "0. Fraicheur / perimetre -- articles mappes dans la vue, par silo", f"""
        SELECT {SILO_CASE_SQL} AS silo, COUNT(*) AS nb_articles
        FROM `{VUE}`
        GROUP BY silo
        ORDER BY nb_articles DESC
    """)

    df1 = run(client, "1. Trafic organique SEO par silo (30 derniers jours, GSC)", f"""
        SELECT
          {SILO_CASE_SQL} AS silo,
          SUM(impressions) AS impressions,
          SUM(clics) AS clics,
          ROUND(100.0 * SUM(clics) / GREATEST(SUM(impressions), 1), 2) AS ctr_pct,
          ROUND(AVG(position_moyenne), 1) AS position_moyenne
        FROM `{VUE}`
        GROUP BY silo
        ORDER BY impressions DESC
    """)

    df2 = run(client, "2. Potentiel de conversion par silo (sessions GA4 -> leads attribues a un article, 30j trafic / tous leads historiques)", f"""
        SELECT
          {SILO_CASE_SQL} AS silo,
          SUM(sessions) AS sessions_30j,
          SUM(nb_leads) AS leads_totaux,
          ROUND(100.0 * SUM(nb_leads) / GREATEST(SUM(sessions), 1), 3) AS taux_conversion_pct
        FROM `{VUE}`
        GROUP BY silo
        ORDER BY taux_conversion_pct DESC
    """)

    run(client, "3. Match cote a cote -- rang trafic SEO vs rang potentiel de conversion", f"""
        WITH par_silo AS (
          SELECT
            {SILO_CASE_SQL} AS silo,
            SUM(impressions) AS impressions,
            SUM(clics) AS clics,
            SUM(sessions) AS sessions,
            SUM(nb_leads) AS leads,
            ROUND(100.0 * SUM(nb_leads) / GREATEST(SUM(sessions), 1), 3) AS taux_conversion_pct
          FROM `{VUE}`
          GROUP BY silo
        )
        SELECT
          silo, impressions, clics, sessions, leads, taux_conversion_pct,
          RANK() OVER (ORDER BY impressions DESC) AS rang_trafic_seo,
          RANK() OVER (ORDER BY taux_conversion_pct DESC) AS rang_conversion
        FROM par_silo
        WHERE silo != 'Autre / hors silo'
        ORDER BY impressions DESC
    """)

    run(client, "4. Top 10 requetes GSC a fort volume / faible CTR, PAR SILO (opportunite de trafic organique supplementaire)", f"""
        SELECT
          CASE
            WHEN silo IS NULL THEN 'Non classe'
            ELSE silo
          END AS silo,
          query, impressions, clics, ctr_pct, position_moyenne
        FROM (
          SELECT
            silo, query,
            SUM(impressions) AS impressions,
            SUM(clics) AS clics,
            ROUND(100.0 * SUM(clics) / GREATEST(SUM(impressions), 1), 2) AS ctr_pct,
            ROUND(AVG(position), 1) AS position_moyenne,
            ROW_NUMBER() OVER (PARTITION BY silo ORDER BY SUM(impressions) DESC) AS rang
          FROM `{PROJECT_ID}.01_raw.gsc_queries`
          WHERE date >= DATE_SUB((SELECT MAX(date) FROM `{PROJECT_ID}.01_raw.gsc_queries`), INTERVAL 30 DAY)
          GROUP BY silo, query
          HAVING impressions >= 50 AND ctr_pct <= 2.0
        )
        WHERE rang <= 3
        ORDER BY silo, impressions DESC
    """)


if __name__ == "__main__":
    main()
