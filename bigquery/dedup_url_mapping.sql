CREATE OR REPLACE TABLE `seo-data-hub-cme.04_pipeline_seo.url_mapping` AS
SELECT * EXCEPT(rn)
FROM (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY url_ancien ORDER BY date_migration DESC) AS rn
  FROM `seo-data-hub-cme.04_pipeline_seo.url_mapping`
)
WHERE rn = 1
