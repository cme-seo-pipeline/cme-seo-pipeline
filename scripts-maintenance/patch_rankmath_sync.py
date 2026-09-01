FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def synchroniser_rankmath(client_bq):
    """CHANTIER G.3 : recupere les donnees SEO RankMath (titre, description,
    mot-cle cible) directement depuis la base WordPress via WP-CLI (SSH,
    IP fixe) — plus rapide et plus fiable que des appels HTTP individuels."""
    print("🔗 SYNCHRONISATION RANKMATH...")
    import io
    import paramiko

    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname="109.234.167.170", port=22, username="jolu5920", pkey=pkey, timeout=15)

        wp_path = "/home/jolu5920/public_html/comprendre-mon-energie.com"
        sql = ("SELECT p.ID, "
               "MAX(CASE WHEN pm.meta_key='rank_math_title' THEN pm.meta_value END), "
               "MAX(CASE WHEN pm.meta_key='rank_math_description' THEN pm.meta_value END), "
               "MAX(CASE WHEN pm.meta_key='rank_math_focus_keyword' THEN pm.meta_value END) "
               "FROM wpwn_posts p LEFT JOIN wpwn_postmeta pm ON p.ID=pm.post_id "
               "AND pm.meta_key IN ('rank_math_title','rank_math_description','rank_math_focus_keyword') "
               "WHERE p.post_status='publish' AND p.post_type IN ('post','page') GROUP BY p.ID")
        cmd = f'wp --path="{wp_path}" db query "{sql}" --skip-column-names'
        stdin, stdout, stderr = client.exec_command(cmd)
        resultat = stdout.read().decode()
        erreur_ssh = stderr.read().decode()
        client.close()

        if erreur_ssh:
            print(f"  ⚠️ Erreur WP-CLI : {erreur_ssh[:300]}")
            return 0
    except Exception as e:
        print(f"  ⚠️ Erreur connexion SSH : {e}")
        return 0

    lignes = []
    for ligne in resultat.strip().split("\\n"):
        if not ligne.strip():
            continue
        parts = ligne.split("\\t")
        if not parts or not parts[0]:
            continue
        try:
            post_id = int(parts[0])
        except ValueError:
            continue
        def _val(i):
            return parts[i] if len(parts) > i and parts[i] != "NULL" else None
        lignes.append({
            "post_id": post_id,
            "rank_math_title": _val(1),
            "rank_math_description": _val(2),
            "rank_math_focus_keyword": _val(3),
            "synced_at": datetime.now().isoformat(),
        })

    if not lignes:
        print("  ℹ️ Aucune donnee RankMath recuperee")
        return 0

    try:
        table_ref = f"{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data"
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bigquery.SchemaField("post_id", "INTEGER"),
                bigquery.SchemaField("rank_math_title", "STRING"),
                bigquery.SchemaField("rank_math_description", "STRING"),
                bigquery.SchemaField("rank_math_focus_keyword", "STRING"),
                bigquery.SchemaField("synced_at", "TIMESTAMP"),
            ],
        )
        load_job = client_bq.load_table_from_json(lignes, table_ref, job_config=job_config)
        load_job.result()
        print(f"  ✅ {len(lignes)} lignes RankMath synchronisees")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def synchroniser_rankmath" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_fonction, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
