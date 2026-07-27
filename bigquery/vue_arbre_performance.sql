CREATE OR REPLACE VIEW `seo-data-hub-cme.04_pipeline_seo.vue_arbre_performance` AS

WITH articles_dedupliques AS (
  SELECT * EXCEPT(rn_dedup)
  FROM (
    SELECT *,
      ROW_NUMBER() OVER (PARTITION BY post_id ORDER BY date_publication DESC) AS rn_dedup
    FROM `seo-data-hub-cme.04_pipeline_seo.historique_publications`
  )
  WHERE rn_dedup = 1
),

gsc_par_url AS (
  SELECT
    url,
    REGEXP_REPLACE(url, r'^https?://[^/]+', '') AS chemin,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clics,
    SUM(sum_position) AS somme_position
  FROM `seo-data-hub-cme.searchconsole.searchdata_url_impression`
  GROUP BY url, chemin
),

conversions_par_article AS (
  SELECT
    CAST(source_post_id AS INT64) AS post_id,
    COUNT(*) AS conversions
  FROM `seo-data-hub-cme.04_pipeline_seo.leads_convertis`
  WHERE source_post_id IS NOT NULL AND source_post_id != ''
  GROUP BY post_id
),

base AS (
  SELECT
    ad.silo AS silo_pipeline,
    ad.sous_silo_strategique AS sous_silo_pipeline,
    ad.titre AS titre_pipeline,
    ad.post_id,
    ad.date_publication,
    COALESCE(ad.url_wp, gsc.url) AS url,
    COALESCE(gsc.impressions, 0) AS impressions,
    COALESCE(gsc.clics, 0) AS clics,
    COALESCE(gsc.somme_position, 0) AS somme_position
  FROM articles_dedupliques ad
  FULL OUTER JOIN gsc_par_url gsc
    ON TRIM(LOWER(ad.url_wp)) = TRIM(LOWER(gsc.url))
),

-- FIX : ajout de TRIM(LOWER()) des deux cotes de la jointure url_mapping
-- (une difference de casse empechait certains rattachements pourtant deja
-- presents dans la table, ex: /aide-etat-thermostat-connecte/)
enrichi AS (
  SELECT
    b.*,
    um.silo AS silo_migre,
    um.sous_silo AS sous_silo_migre
  FROM base b
  LEFT JOIN `seo-data-hub-cme.04_pipeline_seo.url_mapping` um
    ON b.silo_pipeline IS NULL
    AND TRIM(LOWER(REGEXP_REPLACE(b.url, r'^https?://[^/]+', ''))) = TRIM(LOWER(um.url_ancien))
)

SELECT
  COALESCE(
    e.silo_pipeline,
    e.silo_migre,
    CASE
      WHEN e.url LIKE '%electricite%' THEN '5. Électricité'
      WHEN e.url LIKE '%/gaz/%' OR e.url LIKE '%-gaz-%' OR e.url LIKE '%-gaz/%' THEN '1. Gaz'
      WHEN e.url LIKE '%solaire%' OR e.url LIKE '%panneau%' THEN '4. Solaire'
      WHEN e.url LIKE '%renovation%' OR e.url LIKE '%isolation%' OR e.url LIKE '%pompe-a-chaleur%' THEN '2. Rénovation Énergétique'
      WHEN e.url LIKE '%aide%energ%' OR e.url LIKE '%maprimerenov%' OR e.url LIKE '%cheque-energie%' THEN '3. Aide Énergétique'
      ELSE 'Hors silo (page non trackée)'
    END
  ) AS silo,
  COALESCE(e.sous_silo_pipeline, e.sous_silo_migre, 'Non classé') AS sous_silo,
  COALESCE(e.titre_pipeline, REGEXP_EXTRACT(e.url, r'/([^/]+)/?$')) AS titre_article,
  e.url,
  e.post_id,
  e.date_publication,
  e.impressions,
  e.clics,
  e.somme_position,
  COALESCE(conv.conversions, 0) AS conversions

FROM enrichi e
LEFT JOIN conversions_par_article conv
  ON e.post_id = conv.post_id
