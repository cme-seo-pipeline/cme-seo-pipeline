bq query --use_legacy_sql=false --location=EU "
CREATE OR REPLACE VIEW \`seo-data-hub-cme.04_pipeline_seo.leads_par_page\` AS
SELECT
  l.timestamp,
  l.tool,
  l.montant_estime,
  l.economie_estimee,
  l.source_post_id,
  m.url AS page_source,
  -- Silo/sous-silo recuperes depuis seo_opportunities quand la page y est
  -- presente (donnee la plus recente disponible pour cette URL)
  ANY_VALUE(o.silo) AS silo,
  ANY_VALUE(o.sous_silo) AS sous_silo
FROM \`seo-data-hub-cme.04_pipeline_seo.leads_convertis\` l
LEFT JOIN \`seo-data-hub-cme.02_cleaned.wp_url_mapping\` m
  ON CAST(l.source_post_id AS INT64) = m.post_id
LEFT JOIN \`seo-data-hub-cme.03_final.seo_opportunities\` o
  ON o.url = m.url
GROUP BY l.timestamp, l.tool, l.montant_estime, l.economie_estimee, l.source_post_id, m.url
"
