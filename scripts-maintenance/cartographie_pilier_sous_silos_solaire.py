"""
CME — Cartographie des pages pilier, par SOUS-silo de Solaire.

Clarification operateur du 26/10/2026 : le chantier "page pilier + maillage"
ne porte QUE sur le silo Solaire, decoupe par ses 5 vrais sous-silos
(chauffe-eau-solaire, panneaux-solaires, batterie-panneaux-solaires,
systeme-solaire-combine, kit-solaire -- voir
lister_sous_silos_solaire.py), pas sur les 5 silos principaux du site
(malentendu de la cartographie precedente, cartographie_pages_pilier.py,
desormais hors-perimetre pour ce chantier precis).

Meme methode que cartographie_pages_pilier.py (score composite 0-100 :
35% impressions, 20% CTR, 15% position inversee, 20% sessions GA4, +10
bonus si >=1 lead), mais partitionne par sous-silo (2e segment d'URL sous
/solaire/) au lieu du silo entier. Memes sources et memes precautions
(impressions/clics/position lus directement dans 01_raw.gsc_queries pour
eviter le sous-comptage de jointure deja identifie dans
analyser_potentiel_silos.py ; sessions/leads repris de
tunnel_conversion_unifie).

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
        url, sessions, nb_leads, bounce_rate_pct, scroll_depth_moyen, rage_click_sessions
      FROM `{VUE}`
    ),
    mapping_solaire AS (
      -- Univers complet des articles Solaire (via wp_url_mapping, pas seulement
      -- ceux ayant des donnees GSC/GA4) pour ne rater aucun candidat pilier.
      SELECT
        post_id, url,
        {NORM.format(col='url')} AS url_normalized,
        REGEXP_EXTRACT(LOWER(url), r'/solaire/([a-z0-9-]+)/') AS sous_silo
      FROM `{PROJECT_ID}.02_cleaned.wp_url_mapping`
      WHERE REGEXP_CONTAINS(LOWER(url), r'/solaire/[a-z0-9-]+/[a-z0-9-]+/?$')
    ),
    jointes AS (
      SELECT
        m.sous_silo, m.url,
        COALESCE(g.impressions, 0) AS impressions,
        COALESCE(g.clics, 0) AS clics,
        ROUND(100.0 * COALESCE(g.clics, 0) / GREATEST(COALESCE(g.impressions, 0), 1), 2) AS ctr_pct,
        g.position_moyenne,
        COALESCE(t.sessions, 0) AS sessions,
        COALESCE(t.nb_leads, 0) AS nb_leads,
        t.bounce_rate_pct, t.scroll_depth_moyen, t.rage_click_sessions
      FROM mapping_solaire m
      LEFT JOIN gsc_page g ON g.url_normalized = m.url_normalized
      LEFT JOIN tunnel t ON t.url_normalized = m.url_normalized
    ),
    bornes AS (
      SELECT sous_silo, MAX(impressions) AS max_impr, MAX(ctr_pct) AS max_ctr, MAX(sessions) AS max_sess
      FROM jointes
      GROUP BY sous_silo
    ),
    score AS (
      SELECT
        j.*,
        ROUND(
          35.0 * COALESCE(SAFE_DIVIDE(j.impressions, b.max_impr), 0)
          + 20.0 * COALESCE(SAFE_DIVIDE(j.ctr_pct, b.max_ctr), 0)
          + 15.0 * (1.0 - LEAST(COALESCE(j.position_moyenne, 100), 100) / 100.0)
          + 20.0 * COALESCE(SAFE_DIVIDE(j.sessions, b.max_sess), 0)
          + IF(j.nb_leads > 0, 10.0, 0.0)
        , 1) AS score_pilier
      FROM jointes j
      JOIN bornes b USING (sous_silo)
    )
    SELECT
      sous_silo, url, impressions, clics, ctr_pct, ROUND(position_moyenne, 1) AS position_moyenne,
      sessions, nb_leads, bounce_rate_pct, scroll_depth_moyen, rage_click_sessions,
      score_pilier,
      ROW_NUMBER() OVER (
        PARTITION BY sous_silo
        ORDER BY score_pilier DESC, nb_leads DESC, impressions DESC, sessions DESC
      ) AS rang
    FROM score
    QUALIFY rang <= 9
    ORDER BY sous_silo, rang
    """
    print("=" * 100)
    print("Cartographie pilier -- TOUS les articles, par sous-silo Solaire (classes par score composite)")
    print("=" * 100)
    try:
        df = client.query(sql).to_dataframe()
        print(df.to_string(index=False))
    except Exception as e:
        print(f"❌ Erreur SQL : {e}")


if __name__ == "__main__":
    main()
