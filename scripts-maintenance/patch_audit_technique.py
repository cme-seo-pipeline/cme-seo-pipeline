FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def auditer_site_technique(client_bq):
    """CHANTIER G.3 : robot d'audit technique maison. Verifie chaque page
    connue (wp_url_mapping) : code de reponse, chaine de redirection,
    titre/meta/H1. Remplace Screaming Frog (licence + VM ecartees, decision
    du 31/08) — s'appuie sur les 437 URLs deja connues, pas de decouverte
    par crawl necessaire."""
    print("🔗 AUDIT TECHNIQUE DU SITE...")
    try:
        query = f"SELECT post_id, url FROM `{PROJECT_ID}.02_cleaned.wp_url_mapping`"
        df = client_bq.query(query).to_dataframe()
    except Exception as e:
        print(f"  ⚠️ Erreur lecture wp_url_mapping : {e}")
        return 0

    lignes = []
    for _, row in df.iterrows():
        post_id = int(row['post_id'])
        url = row['url']
        entree = {
            "post_id": post_id, "url": url, "status_code": None,
            "url_finale": None, "nb_redirections": 0,
            "titre": None, "titre_longueur": None,
            "meta_description": None, "meta_description_longueur": None,
            "h1_liste": None, "nb_h1": None,
            "erreur": None, "audite_le": datetime.now().isoformat(),
        }
        try:
            resp = requests.get(url, timeout=15, allow_redirects=True)
            entree["status_code"] = resp.status_code
            entree["url_finale"] = resp.url
            entree["nb_redirections"] = len(resp.history)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                titre_tag = soup.find('title')
                titre = titre_tag.get_text().strip() if titre_tag else None
                entree["titre"] = titre
                entree["titre_longueur"] = len(titre) if titre else 0
                meta_tag = soup.find('meta', attrs={'name': 'description'})
                meta = meta_tag.get('content', '').strip() if meta_tag else None
                entree["meta_description"] = meta
                entree["meta_description_longueur"] = len(meta) if meta else 0
                h1_tags = soup.find_all('h1')
                h1_textes = [h.get_text().strip() for h in h1_tags]
                entree["h1_liste"] = json.dumps(h1_textes, ensure_ascii=False)
                entree["nb_h1"] = len(h1_textes)
        except Exception as e:
            entree["erreur"] = str(e)[:200]
        lignes.append(entree)

    if not lignes:
        print("  ℹ️ Aucune page a auditer")
        return 0

    try:
        table_ref = f"{PROJECT_ID}.04_pipeline_seo.audit_technique_site"
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bigquery.SchemaField("post_id", "INTEGER"),
                bigquery.SchemaField("url", "STRING"),
                bigquery.SchemaField("status_code", "INTEGER"),
                bigquery.SchemaField("url_finale", "STRING"),
                bigquery.SchemaField("nb_redirections", "INTEGER"),
                bigquery.SchemaField("titre", "STRING"),
                bigquery.SchemaField("titre_longueur", "INTEGER"),
                bigquery.SchemaField("meta_description", "STRING"),
                bigquery.SchemaField("meta_description_longueur", "INTEGER"),
                bigquery.SchemaField("h1_liste", "STRING"),
                bigquery.SchemaField("nb_h1", "INTEGER"),
                bigquery.SchemaField("erreur", "STRING"),
                bigquery.SchemaField("audite_le", "TIMESTAMP"),
            ],
        )
        load_job = client_bq.load_table_from_json(lignes, table_ref, job_config=job_config)
        load_job.result()
        print(f"  ✅ {len(lignes)} pages auditees (remplacement complet)")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def auditer_site_technique" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_fonction, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
