"""Diagnostic ponctuel lecture seule -- tous les leads comparateur-energie
du 16/11/2026, pour comprendre pourquoi les 4 cibles pastees par
l'operateur ne matchent pas en UTC strict (hypothese : timezone Europe/Paris
affichee par la source que l'operateur a consultee)."""
from google.cloud import bigquery
client = bigquery.Client(project="seo-data-hub-cme")
df = client.query("""
    SELECT timestamp,
           FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', timestamp, 'Europe/Paris') AS ts_paris,
           prenom, nom, telephone, email,
           JSON_EXTRACT_SCALAR(details, '$.fournisseur') AS fournisseur
    FROM `seo-data-hub-cme.04_pipeline_seo.leads_convertis`
    WHERE tool = 'comparateur-energie'
      AND DATE(timestamp, 'Europe/Paris') IN ('2026-11-16', '2026-11-17')
    ORDER BY timestamp
""").to_dataframe()
print(f"{len(df)} ligne(s) comparateur-energie trouvee(s) le 16-17/11 (fenetre Europe/Paris) :\n")
for _, r in df.iterrows():
    print(f"  UTC={r['timestamp']}  Paris={r['ts_paris']}  prenom={r['prenom']!r} nom={r['nom']!r} tel={r['telephone']!r} email={r['email']!r} fournisseur={r['fournisseur']!r}")
