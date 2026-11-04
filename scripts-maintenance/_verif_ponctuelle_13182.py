"""Verification ponctuelle (lecture seule) du detail d'un evenement precis."""
import sys
from google.cloud import bigquery

client = bigquery.Client(project="seo-data-hub-cme")
df = client.query("""
    SELECT timestamp, type_evenement, cible, etape, position_contenu, source_post_id
    FROM `seo-data-hub-cme.04_pipeline_seo.interactions_contenu`
    WHERE source_post_id = '13182' AND type_evenement IN ('form_vu', 'form_abandon', 'form_etape')
    ORDER BY timestamp
""").to_dataframe()
print(df.to_string(index=False))
