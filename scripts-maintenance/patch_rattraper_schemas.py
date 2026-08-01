FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/api/log-clic', methods=['POST', 'OPTIONS'])"

nouvelle_route = '''@app.route('/rattraper-schemas', methods=['POST'])
def rattraper_schemas():
    """
    Regenere les schemas SVG manquants pour des articles precis, en
    fournissant leurs post_id explicitement (contrairement a
    /rattraper-images, pas de detection automatique possible ici : aucune
    colonne BigQuery ne trace si les schemas ont ete injectes).
    Body JSON requis : {"post_ids": [5093, 5094]}
    """
    from pipeline import (
        nettoyer_et_generer_schemas, init_bigquery,
        CONFIG, WP_CONFIG, PROJECT_ID, DATASET_ID
    )
    import pandas as pd
    data = request.get_json(silent=True) or {}
    post_ids = data.get('post_ids', [])
    if not post_ids:
        return jsonify({"status": "error", "message": "post_ids requis"}), 400
    try:
        client_bq = init_bigquery()
        post_ids_str = ",".join(str(p) for p in post_ids)
        query = f"""
        SELECT post_id, silo, titre
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE post_id IN ({post_ids_str})
        """
        df = client_bq.query(query).to_dataframe()
        if df.empty:
            return jsonify({
                "status": "ok",
                "message": "Aucun article trouve pour ces post_id",
                "count": 0
            }), 200
        df_publications = pd.DataFrame({
            'Post_ID': df['post_id'],
            'Silo': df['silo'],
            'Titre': df['titre'],
        })
        def run_async():
            try:
                nettoyer_et_generer_schemas(df_publications, WP_CONFIG, CONFIG)
                print(f"✅ Rattrapage schemas termine : {len(df_publications)} articles traites")
            except Exception as e:
                print(f"❌ Erreur rattrapage schemas : {e}")
        thread = threading.Thread(target=run_async)
        thread.daemon = True
        thread.start()
        return jsonify({
            "status": "started",
            "count": len(df_publications),
            "post_ids": df['post_id'].tolist()
        }), 202
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


''' + ancre

if "rattraper_schemas" in contenu:
    print("⏭️  PATCH (endpoint rattraper-schemas) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (endpoint rattraper-schemas) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route, 1)
    print("✅ PATCH (endpoint rattraper-schemas) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
