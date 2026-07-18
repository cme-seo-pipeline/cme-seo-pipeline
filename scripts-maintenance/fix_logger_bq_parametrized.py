with open('pipeline.py', 'r') as f:
    content = f.read()

old = '''def logger_publication_bq(client_bq, post_id, silo, titre,
                          mot_cle, url_wp, run_id, sous_silo_strategique, image_id=None):
    """Log publication dans BQ avec retry x3 pour robustesse."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            df_check = client_bq.query(f"""
            SELECT COUNT(*) as nb
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE post_id = {post_id}
            """).to_dataframe()

            if df_check['nb'].iloc[0] > 0:
                query = f"""
                UPDATE `{PROJECT_ID}.{DATASET_ID}.historique_publications`
                SET date_publication = CURRENT_TIMESTAMP(),
                    silo = '{silo.replace("'", "''")}',
                    titre = '{titre.replace("'", "''")}',
                    mot_cle = '{mot_cle.replace("'", "''")}',
                    url_wp = '{url_wp}',
                    run_id = '{run_id}',
                    sous_silo_strategique = '{sous_silo_strategique}',
                    image_id = {"'" + image_id + "'" if image_id else 'NULL'}
                WHERE post_id = {post_id}
                """
            else:
                query = f"""
                INSERT INTO `{PROJECT_ID}.{DATASET_ID}.historique_publications`
                (date_publication, post_id, silo, titre, mot_cle,
                 url_wp, run_id, sous_silo_strategique, image_id)
                VALUES (CURRENT_TIMESTAMP(), {post_id},
                    '{silo.replace("'", "''")}',
                    '{titre.replace("'", "''")}',
                    '{mot_cle.replace("'", "''")}',
                    '{url_wp}', '{run_id}',
                    '{sous_silo_strategique.replace("'", "''")}',
                    {"'" + image_id + "'" if image_id else 'NULL'})
                """
            client_bq.query(query).result()
            return True'''

new = '''def logger_publication_bq(client_bq, post_id, silo, titre,
                          mot_cle, url_wp, run_id, sous_silo_strategique, image_id=None):
    """Log publication dans BQ avec retry x3. Requetes parametrees :
    aucun risque d'echappement casse par des apostrophes/guillemets/accents,
    quel que soit le contenu (titre, silo, sous-silo...)."""
    from google.cloud import bigquery
    max_retries = 3
    for attempt in range(max_retries):
        try:
            df_check = client_bq.query(
                f"""SELECT COUNT(*) as nb
                FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
                WHERE post_id = @post_id""",
                job_config=bigquery.QueryJobConfig(query_parameters=[
                    bigquery.ScalarQueryParameter("post_id", "INT64", post_id)
                ])
            ).to_dataframe()

            params = [
                bigquery.ScalarQueryParameter("post_id", "INT64", post_id),
                bigquery.ScalarQueryParameter("silo", "STRING", silo),
                bigquery.ScalarQueryParameter("titre", "STRING", titre),
                bigquery.ScalarQueryParameter("mot_cle", "STRING", mot_cle),
                bigquery.ScalarQueryParameter("url_wp", "STRING", url_wp),
                bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
                bigquery.ScalarQueryParameter("sous_silo", "STRING", sous_silo_strategique),
                bigquery.ScalarQueryParameter("image_id", "STRING", image_id),
            ]

            if df_check['nb'].iloc[0] > 0:
                query = """
                UPDATE `{}.{}.historique_publications`
                SET date_publication = CURRENT_TIMESTAMP(),
                    silo = @silo,
                    titre = @titre,
                    mot_cle = @mot_cle,
                    url_wp = @url_wp,
                    run_id = @run_id,
                    sous_silo_strategique = @sous_silo,
                    image_id = @image_id
                WHERE post_id = @post_id
                """.format(PROJECT_ID, DATASET_ID)
            else:
                query = """
                INSERT INTO `{}.{}.historique_publications`
                (date_publication, post_id, silo, titre, mot_cle,
                 url_wp, run_id, sous_silo_strategique, image_id)
                VALUES (CURRENT_TIMESTAMP(), @post_id, @silo, @titre, @mot_cle,
                    @url_wp, @run_id, @sous_silo, @image_id)
                """.format(PROJECT_ID, DATASET_ID)

            client_bq.query(
                query,
                job_config=bigquery.QueryJobConfig(query_parameters=params)
            ).result()
            return True'''

if old in content:
    content = content.replace(old, new, 1)
    print("✅ logger_publication_bq converti en requetes parametrees")
else:
    print("❌ Pattern non trouvé")

with open('pipeline.py', 'w') as f:
    f.write(content)
