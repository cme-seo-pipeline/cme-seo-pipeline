bq query --use_legacy_sql=false --location=EU "
CREATE OR REPLACE VIEW \`seo-data-hub-cme.03_final.seo_opportunities\` AS
WITH
mapping AS (
  SELECT post_id, url_normalized
  FROM \`seo-data-hub-cme.02_cleaned.wp_url_mapping\`
),
gsc AS (
  SELECT
    page AS url, query,
    CASE
      WHEN LOWER(REGEXP_REPLACE(NORMALIZE(silo, NFD), r'\pM', '')) LIKE '%gaz%' THEN '1. Gaz'
      WHEN LOWER(REGEXP_REPLACE(NORMALIZE(silo, NFD), r'\pM', '')) LIKE '%renovation%' THEN '2. Rénovation Énergétique'
      WHEN LOWER(REGEXP_REPLACE(NORMALIZE(silo, NFD), r'\pM', '')) LIKE '%aide%' THEN '3. Aide Énergétique'
      WHEN LOWER(REGEXP_REPLACE(NORMALIZE(silo, NFD), r'\pM', '')) LIKE '%solaire%' THEN '4. Solaire'
      WHEN LOWER(REGEXP_REPLACE(NORMALIZE(silo, NFD), r'\pM', '')) LIKE '%electric%' THEN '5. Électricité'
      ELSE silo
    END AS silo,
    CASE
      WHEN sous_silo = 'contrat' AND silo LIKE '%lectric%' THEN 'contrat-electricite'
      WHEN sous_silo = 'chauffage' AND silo LIKE '%lectric%' THEN 'chauffage-electricite'
      WHEN sous_silo = 'facture' AND silo LIKE '%lectric%' THEN 'facture-electricite'
      WHEN sous_silo = 'comparatifs-fournisseurs' AND silo LIKE '%lectric%' THEN 'comparatifs-fournisseurs-electricite'
      ELSE sous_silo
    END AS sous_silo,
    SUM(impressions) AS impressions, SUM(clics) AS clics,
    AVG(position) AS position, AVG(ctr) AS ctr,
    -- CORRECTIF STRUCTUREL : normalisation identique a celle utilisee
    -- pour construire wp_url_mapping (protocole/www/slash final retires)
    LOWER(REGEXP_REPLACE(REGEXP_REPLACE(page, r'^https?://(www\.)?', ''), r'/\$', '')) AS url_normalized
  FROM \`seo-data-hub-cme.01_raw.gsc_queries\`
  WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    AND silo != '' AND LENGTH(silo) > 3
    AND (sous_silo IS NULL OR NOT STARTS_WITH(sous_silo, '#'))
  GROUP BY page, query, silo, sous_silo, url_normalized
),
ga4 AS (
  SELECT page_url AS url,
    SUM(sessions) AS sessions, AVG(bounce_rate) AS bounce_rate,
    AVG(avg_session_duration) AS avg_duration, SUM(conversions) AS conversions,
    LOWER(REGEXP_REPLACE(REGEXP_REPLACE(page_url, r'^https?://(www\.)?', ''), r'/\$', '')) AS url_normalized
  FROM \`seo-data-hub-cme.01_raw.ga4_pages\`
  WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY page_url, url_normalized
),
-- Resolution URL -> post_id (identifiant stable, immunise contre les
-- restructurations d'URL) pour chaque source, avant toute jointure entre elles
gsc_resolved AS (
  SELECT g.*, m.post_id
  FROM gsc g
  LEFT JOIN mapping m ON m.url_normalized = g.url_normalized
),
ga4_resolved AS (
  SELECT a.*, m.post_id
  FROM ga4 a
  LEFT JOIN mapping m ON m.url_normalized = a.url_normalized
),
publie AS (
  SELECT silo,
    LOWER(REGEXP_REPLACE(REGEXP_REPLACE(
      NORMALIZE(REPLACE(REPLACE(sous_silo_strategique,' ','-'),'_','-'), NFD),
      r'\pM', ''), r\"[''\`]\", '')) AS sous_silo_norm,
    MAX(date_publication) AS derniere_pub, COUNT(*) AS nb_articles_90j
  FROM \`seo-data-hub-cme.04_pipeline_seo.historique_publications\`
  WHERE date_publication >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
  GROUP BY silo, sous_silo_norm
)
SELECT
  g.url, g.silo, g.sous_silo, g.query,
  CAST(g.impressions AS INT64) AS impressions,
  CAST(g.clics AS INT64) AS clics,
  ROUND(g.position,1) AS position,
  ROUND(g.ctr*100,2) AS ctr_pct,
  COALESCE(a.sessions,0) AS sessions,
  ROUND(a.bounce_rate*100,1) AS bounce_rate_pct,
  COALESCE(a.conversions,0) AS conversions,
  p.derniere_pub,
  COALESCE(p.nb_articles_90j,0) AS nb_articles_90j,
  DATE_DIFF(CURRENT_DATE(),
    COALESCE(DATE(p.derniere_pub),DATE('2020-01-01')),DAY) AS jours_depuis_pub,
  ROUND(
    (g.impressions * GREATEST(0,35-g.position) / GREATEST(g.ctr,0.005))
    * (CASE WHEN a.bounce_rate IS NULL THEN 1 ELSE 1+GREATEST(0,a.bounce_rate-0.5) END)
    / GREATEST(1,90.0/GREATEST(
        DATE_DIFF(CURRENT_DATE(),
          COALESCE(DATE(p.derniere_pub),DATE('2020-01-01')),DAY),1))
  ,0) AS score_opportunite
FROM gsc_resolved g
-- CORRECTIF STRUCTUREL : jointure sur post_id (identifiant stable),
-- plus jamais sur l'URL brute (fragile face aux restructurations)
LEFT JOIN ga4_resolved a ON a.post_id = g.post_id AND g.post_id IS NOT NULL
LEFT JOIN publie p ON p.silo=g.silo
  AND LOWER(REGEXP_REPLACE(REGEXP_REPLACE(
        NORMALIZE(REPLACE(REPLACE(g.sous_silo,' ','-'),'_','-'), NFD),
        r'\pM', ''), r\"[''\`]\", '')) = p.sous_silo_norm
WHERE g.position BETWEEN 5 AND 42 AND g.impressions > 5
ORDER BY score_opportunite DESC
"
