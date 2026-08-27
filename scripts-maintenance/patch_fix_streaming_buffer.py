FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''    try:
        client_bq.query(f"""
        DELETE FROM `{PROJECT_ID}.02_cleaned.wp_url_mapping` WHERE TRUE
        """).result()
        client_bq.insert_rows_json(f"{PROJECT_ID}.02_cleaned.wp_url_mapping", lignes)
        print(f"  ✅ {len(lignes)} correspondances URL → post_id mises a jour")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0'''

nouveau = '''    try:
        from google.cloud import bigquery as bq_module
        table_ref = f"{PROJECT_ID}.02_cleaned.wp_url_mapping"
        job_config = bq_module.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bq_module.SchemaField("post_id", "INTEGER"),
                bq_module.SchemaField("url", "STRING"),
                bq_module.SchemaField("url_normalized", "STRING"),
                bq_module.SchemaField("date_maj", "TIMESTAMP"),
            ],
        )
        # Job de chargement (remplacement atomique complet) plutot que
        # DELETE + insertion en streaming : evite le blocage "streaming
        # buffer" de BigQuery quand la table vient d'etre rafraichie
        # recemment (le DELETE echoue silencieusement dans ce cas).
        load_job = client_bq.load_table_from_json(lignes, table_ref, job_config=job_config)
        load_job.result()
        print(f"  ✅ {len(lignes)} correspondances URL → post_id mises a jour (remplacement complet)")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0'''

if "load_table_from_json" in contenu:
    print("⏭️  PATCH (fix streaming buffer wp_url_mapping) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (fix streaming buffer wp_url_mapping) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (fix streaming buffer wp_url_mapping) : job de chargement WRITE_TRUNCATE")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
