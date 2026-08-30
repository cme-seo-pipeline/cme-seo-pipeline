FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def rafraichir_leads_app_authentifies(client_bq):
    """CHANTIER SOUVERAINETE SHELL : synchronise les leads des utilisateurs
    connectes a l'app mobile/web (Firestore, sous-collection users/{uid}/leads)
    vers BigQuery. Complete leads_convertis (canal anonyme/tracking-api) pour
    obtenir une vue unifiee des conversions, tous canaux confondus."""
    print("🔗 SYNCHRONISATION LEADS APP AUTHENTIFIES...")
    lignes = []
    try:
        from google.cloud import firestore as firestore_module
        db_fs = firestore_module.Client(project=PROJECT_ID)
        docs = db_fs.collection_group('leads').stream()
        for d in docs:
            data = d.to_dict()
            owner_uid = d.reference.parent.parent.id
            derniere_maj = data.get('derniere_maj')
            lignes.append({
                "lead_id": d.id,
                "owner_uid": owner_uid,
                "tool": data.get('tool', ''),
                "statut": data.get('statut', ''),
                "source_post_id": str(data.get('source_post_id', '') or ''),
                "montant_estime": float(data.get('montant_estime', 0) or 0),
                "economie_estimee": float(data.get('economie_estimee', 0) or 0),
                "details": json.dumps(data.get('details', {}), ensure_ascii=False),
                "derniere_maj": derniere_maj.isoformat() if derniere_maj else None,
                "synced_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"  ⚠️ Erreur lecture Firestore : {e}")
        return 0

    if not lignes:
        print("  ℹ️ Aucun lead trouve dans Firestore")
        return 0

    try:
        from google.cloud import bigquery as bq_module
        table_ref = f"{PROJECT_ID}.04_pipeline_seo.leads_app_authentifies"
        job_config = bq_module.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bq_module.SchemaField("lead_id", "STRING"),
                bq_module.SchemaField("owner_uid", "STRING"),
                bq_module.SchemaField("tool", "STRING"),
                bq_module.SchemaField("statut", "STRING"),
                bq_module.SchemaField("source_post_id", "STRING"),
                bq_module.SchemaField("montant_estime", "FLOAT"),
                bq_module.SchemaField("economie_estimee", "FLOAT"),
                bq_module.SchemaField("details", "STRING"),
                bq_module.SchemaField("derniere_maj", "TIMESTAMP"),
                bq_module.SchemaField("synced_at", "TIMESTAMP"),
            ],
        )
        load_job = client_bq.load_table_from_json(lignes, table_ref, job_config=job_config)
        load_job.result()
        print(f"  ✅ {len(lignes)} leads app synchronises (remplacement complet)")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def rafraichir_leads_app_authentifies" in contenu:
    print("⏭️  PATCH (sync leads Firestore) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (sync leads Firestore) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_fonction, 1)
    print("✅ PATCH (sync leads Firestore) : fonction ajoutee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
