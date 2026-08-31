bq query --use_legacy_sql=false --location=EU "
CREATE OR REPLACE VIEW \`seo-data-hub-cme.04_pipeline_seo.tunnel_conversion_unifie\` AS
WITH
mapping AS (
  SELECT post_id, url, url_normalized FROM \`seo-data-hub-cme.02_cleaned.wp_url_mapping\`
),
gsc_agg AS (
  SELECT
    LOWER(REGEXP_REPLACE(REGEXP_REPLACE(page, r'^https?://(www\.)?', ''), r'/\$', '')) AS url_normalized,
    SUM(impressions) AS impressions, SUM(clics) AS clics, AVG(position) AS position_moyenne
  FROM \`seo-data-hub-cme.01_raw.gsc_queries\`
  WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY url_normalized
),
ga4_agg AS (
  SELECT
    LOWER(REGEXP_REPLACE(REGEXP_REPLACE(page_url, r'^https?://(www\.)?', ''), r'/\$', '')) AS url_normalized,
    SUM(sessions) AS sessions, AVG(bounce_rate) AS bounce_rate
  FROM \`seo-data-hub-cme.01_raw.ga4_pages\`
  WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY url_normalized
),
clarity_agg AS (
  SELECT
    LOWER(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(url, r'\\?.*\$', ''), r'^https?://(www\.)?', ''), r'/\$', '')) AS url_normalized,
    MAX(CASE WHEN metric_name = 'RageClickCount' THEN SAFE_CAST(JSON_EXTRACT_SCALAR(donnees, '\$.sessionsCount') AS INT64) END) AS rage_click_sessions,
    MAX(CASE WHEN metric_name = 'ScrollDepth' THEN SAFE_CAST(JSON_EXTRACT_SCALAR(donnees, '\$.averageScrollDepth') AS FLOAT64) END) AS scroll_depth_moyen
  FROM \`seo-data-hub-cme.04_pipeline_seo.clarity_insights_par_page\`
  WHERE date_sync >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY url_normalized
),
leads_anonymes AS (
  SELECT SAFE_CAST(source_post_id AS INT64) AS post_id, COUNT(*) AS nb, SUM(economie_estimee) AS eco
  FROM \`seo-data-hub-cme.04_pipeline_seo.leads_convertis\`
  GROUP BY post_id
),
leads_auth AS (
  SELECT SAFE_CAST(source_post_id AS INT64) AS post_id, COUNT(*) AS nb, SUM(economie_estimee) AS eco
  FROM \`seo-data-hub-cme.04_pipeline_seo.leads_app_authentifies\`
  GROUP BY post_id
),
leads_final AS (
  SELECT post_id, SUM(nb) AS nb_leads, SUM(eco) AS economie_totale
  FROM (SELECT * FROM leads_anonymes UNION ALL SELECT * FROM leads_auth)
  WHERE post_id IS NOT NULL
  GROUP BY post_id
)
SELECT
  m.post_id, m.url,
  COALESCE(g.impressions, 0) AS impressions,
  COALESCE(g.clics, 0) AS clics,
  ROUND(g.position_moyenne, 1) AS position_moyenne,
  COALESCE(a.sessions, 0) AS sessions,
  ROUND(a.bounce_rate * 100, 1) AS bounce_rate_pct,
  c.rage_click_sessions,
  ROUND(c.scroll_depth_moyen, 1) AS scroll_depth_moyen,
  COALESCE(l.nb_leads, 0) AS nb_leads,
  COALESCE(l.economie_totale, 0) AS economie_totale_estimee
FROM mapping m
LEFT JOIN gsc_agg g ON g.url_normalized = m.url_normalized
LEFT JOIN ga4_agg a ON a.url_normalized = m.url_normalized
LEFT JOIN clarity_agg c ON c.url_normalized = m.url_normalized
LEFT JOIN leads_final l ON l.post_id = m.post_id
ORDER BY impressions DESC
"
