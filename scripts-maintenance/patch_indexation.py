FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def synchroniser_indexation(client_bq):
    """CHANTIER INDEXATION : verifie pour chaque page connue si Google l'a
    reellement indexee (URL Inspection API de Search Console) -- differe
    des metriques GSC habituelles, qui ne montrent que les pages DEJA
    visibles en recherche."""
    print("SYNCHRONISATION INDEXATION GOOGLE...")

    from google.oauth2 import service_account
    import google.auth.transport.requests

    try:
        cle = os.environ.get("SA_GTM_PRIVATE_KEY", "")
        creds = service_account.Credentials.from_service_account_info(
            json.loads(cle),
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        creds.refresh(google.auth.transport.requests.Request())
    except Exception as e:
        print(f"  Erreur authentification : {e}")
        return 0

    try:
        query = f"SELECT post_id, url FROM `{PROJECT_ID}.02_cleaned.wp_url_mapping`"
        df = client_bq.query(query).to_dataframe()
    except Exception as e:
        print(f"  Erreur lecture wp_url_mapping : {e}")
        return 0

    lignes = []
    for _, row in df.iterrows():
        post_id = int(row['post_id'])
        url = row['url']
        entree = {
            "post_id": post_id, "url": url,
            "coverage_state": None, "verdict": None, "robots_txt_state": None,
            "indexing_state": None, "page_fetch_state": None,
            "last_crawl_time": None, "crawled_as": None,
            "erreur": None, "checked_at": datetime.now().isoformat(),
        }
        try:
            body = {"inspectionUrl": url, "siteUrl": "https://www.comprendre-mon-energie.fr/"}
            r = requests.post(
                "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
                json=body, timeout=20
            )
            if r.status_code == 200:
                result = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
                entree["coverage_state"] = result.get("coverageState")
                entree["verdict"] = result.get("verdict")
                entree["robots_txt_state"] = result.get("robotsTxtState")
                entree["indexing_state"] = result.get("indexingState")
                entree["page_fetch_state"] = result.get("pageFetchState")
                entree["last_crawl_time"] = result.get("lastCrawlTime")
                entree["crawled_as"] = result.get("crawledAs")
            else:
                entree["erreur"] = f"HTTP {r.status_code}: {r.text[:150]}"
        except Exception as e:
            entree["erreur"] = str(e)[:200]

        lignes.append(entree)

    if not lignes:
        print("  Aucune page a verifier")
        return 0

    try:
        table_ref = f"{PROJECT_ID}.04_pipeline_seo.indexation_google"
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bigquery.SchemaField("post_id", "INTEGER"),
                bigquery.SchemaField("url", "STRING"),
                bigquery.SchemaField("coverage_state", "STRING"),
                bigquery.SchemaField("verdict", "STRING"),
                bigquery.SchemaField("robots_txt_state", "STRING"),
                bigquery.SchemaField("indexing_state", "STRING"),
                bigquery.SchemaField("page_fetch_state", "STRING"),
                bigquery.SchemaField("last_crawl_time", "TIMESTAMP"),
                bigquery.SchemaField("crawled_as", "STRING"),
                bigquery.SchemaField("erreur", "STRING"),
                bigquery.SchemaField("checked_at", "TIMESTAMP"),
            ],
        )
        load_job = client_bq.load_table_from_json(lignes, table_ref, job_config=job_config)
        load_job.result()
        print(f"  {len(lignes)} pages verifiees")
    except Exception as e:
        print(f"  Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def synchroniser_indexation" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_fonction, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
