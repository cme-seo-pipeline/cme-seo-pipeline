"""
CME — Cartographie des pages pilier candidates, par silo.

Demande operateur du 26/10/2026 (suite du point 4 de la strategie
trafic+conversion du meme jour) : pour chacun des 5 silos du site (Gaz,
Electricite, Aides energetiques, Renovation energetique, Solaire), identifier
LA page qui capte les meilleures stats (impressions/CTR/position GSC +
sessions/leads GA4) pour en faire la "page pilier" du silo, et preparer le
maillage interne (mention en haut de chaque article vers cette page pilier).

Source des metriques -- DEUX requetes separees, pas la vue
tunnel_conversion_unifie seule, pour la raison deja identifiee dans
analyser_potentiel_silos.py (26/10/2026, section 5) : la jointure GSC de
cette vue (via url_normalized) sous-compte fortement impressions/clics. Donc :
- Impressions/clics/position : lus DIRECTEMENT dans 01_raw.gsc_queries,
  groupes par page (pas via la vue).
- Sessions/leads/bounce/scroll : lus dans tunnel_conversion_unifie (ces
  jointures-la, via GA4 et leads_convertis, se sont averees fiables lors du
  diagnostic Electricite du meme jour).
Les deux sources sont ensuite jointes ici par URL normalisee (meme logique
de normalisation que la vue : minuscules, sans protocole/www, sans slash
final), et le silo est derive par le meme decoupage de prefixe que
PAR_PREFIXE dans cme-cta-progressifs.php (gaz / electricite /
aide-energetique / renovation-energetique / solaire).

Score composite (0-100) par page, PROPRE A CHAQUE SILO (normalisation
min-max a l'interieur du silo, pas globale -- un silo avec moins de trafic
dans l'absolu doit pouvoir avoir une page pilier tout de meme) :
  - 35% impressions (reach SEO)
  - 20% CTR (efficacite du titre/snippet)
  - 15% position inversee (1 - position/100, plus la position est basse/
    bonne, mieux c'est)
  - 20% sessions GA4 (trafic reel, pas juste potentiel)
  - 10% bonus fixe si au moins 1 lead attribue (preuve directe de
    conversion -- rare donc traite en bonus plutot qu'en poids continu,
    sinon la quasi-totalite des pages a 0 lead ne se differencierait pas)

LECTURE SEULE. Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
VUE = f"{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie"

NORM = "LOWER(REGEXP_REPLACE(REGEXP_REPLACE({col}, r'^https?://(www\\.)?', ''), r'/$', ''))"

SILO_CASE_SQL = """
  CASE REGEXP_EXTRACT(url_normalized, r'^[^/]+/([a-z0-9-]+)/')
    WHEN 'gaz' THEN 'Gaz'
    WHEN 'electricite' THEN 'Électricité'
    WHEN 'aide-energetique' THEN 'Aides énergétiques'
    WHEN 'renovation-energetique' THEN 'Rénovation énergétique'
    WHEN 'solaire' THEN 'Solaire'
    ELSE NULL
  END
"""


def run(client, titre, sql):
    print("\n" + "=" * 90)
    print(titre)
    print("=" * 90)
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

    sql = f"""
    WITH gsc_page AS (
      SELECT
        {NORM.format(col='page')} AS url_normalized,
        SUM(impressions) AS impressions,
        SUM(clics) AS clics,
        AVG(position) AS position_moyenne
      FROM `{PROJECT_ID}.01_raw.gsc_queries`
      WHERE date >= DATE_SUB((SELECT MAX(date) FROM `{PROJECT_ID}.01_raw.gsc_queries`), INTERVAL 30 DAY)
      GROUP BY url_normalized
    ),
    tunnel AS (
      SELECT
        {NORM.format(col='url')} AS url_normalized,
        url,
        sessions, nb_leads, bounce_rate_pct, scroll_depth_moyen, rage_click_sessions
      FROM `{VUE}`
    ),
    jointes AS (
      SELECT
        COALESCE(t.url, g.url_normalized) AS url,
        COALESCE(g.url_normalized, t.url_normalized) AS url_normalized,
        COALESCE(g.impressions, 0) AS impressions,
        COALESCE(g.clics, 0) AS clics,
        ROUND(100.0 * COALESCE(g.clics, 0) / GREATEST(COALESCE(g.impressions, 0), 1), 2) AS ctr_pct,
        g.position_moyenne,
        COALESCE(t.sessions, 0) AS sessions,
        COALESCE(t.nb_leads, 0) AS nb_leads,
        t.bounce_rate_pct, t.scroll_depth_moyen, t.rage_click_sessions
      FROM gsc_page g
      FULL OUTER JOIN tunnel t ON t.url_normalized = g.url_normalized
    ),
    avec_silo AS (
      SELECT *, {SILO_CASE_SQL} AS silo
      FROM jointes
    ),
    bornes AS (
      SELECT
        silo,
        MAX(impressions) AS max_impr, MAX(ctr_pct) AS max_ctr,
        MAX(sessions) AS max_sess
      FROM avec_silo
      WHERE silo IS NOT NULL
      GROUP BY silo
    ),
    score AS (
      SELECT
        a.*,
        ROUND(
          35.0 * COALESCE(SAFE_DIVIDE(a.impressions, b.max_impr), 0)
          + 20.0 * COALESCE(SAFE_DIVIDE(a.ctr_pct, b.max_ctr), 0)
          + 15.0 * (1.0 - LEAST(COALESCE(a.position_moyenne, 100), 100) / 100.0)
          + 20.0 * COALESCE(SAFE_DIVIDE(a.sessions, b.max_sess), 0)
          + IF(a.nb_leads > 0, 10.0, 0.0)
        , 1) AS score_pilier
      FROM avec_silo a
      JOIN bornes b USING (silo)
      WHERE a.silo IS NOT NULL
    )
    SELECT
      silo, url, impressions, clics, ctr_pct, ROUND(position_moyenne, 1) AS position_moyenne,
      sessions, nb_leads, bounce_rate_pct, scroll_depth_moyen, rage_click_sessions,
      score_pilier,
      ROW_NUMBER() OVER (
        PARTITION BY silo
        ORDER BY score_pilier DESC, nb_leads DESC, impressions DESC, sessions DESC
      ) AS rang
    FROM score
    QUALIFY rang <= 8
    ORDER BY silo, rang
    """
    run(client, "Cartographie -- Top 8 pages par silo, classees par score composite", sql)


if __name__ == "__main__":
    main()
