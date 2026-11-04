"""
CME — Diagnostic ponctuel (lecture seule) : pourquoi temps_ms apparait
toujours NULL dans lecture_position (constate par
synthese_zones_clic_retention.py le 04/11/2026). Jetable.

USAGE : python3 diagnostiquer_temps_ms_vide.py
"""
import sys
try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("missing")
client = bigquery.Client(project="seo-data-hub-cme")
df = client.query("""
    SELECT COUNT(*) AS total,
           COUNTIF(temps_ms IS NULL) AS n_null,
           COUNTIF(temps_ms IS NOT NULL) AS n_non_null,
           MIN(timestamp) AS premier_non_null_ts
    FROM `seo-data-hub-cme.04_pipeline_seo.interactions_contenu`
    WHERE type_evenement = 'lecture_position'
""").to_dataframe()
print(df.to_string(index=False))

df2 = client.query("""
    SELECT timestamp, temps_ms
    FROM `seo-data-hub-cme.04_pipeline_seo.interactions_contenu`
    WHERE type_evenement = 'lecture_position' AND temps_ms IS NOT NULL
    ORDER BY timestamp DESC LIMIT 5
""").to_dataframe()
print(df2.to_string(index=False))
