FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/api/log-clic', methods=['POST', 'OPTIONS'])"

nouvelle_route = '''@app.route('/rattraper-facebook', methods=['POST'])
def rattraper_facebook():
    """
    Republie sur Facebook des articles precis (post_id explicites), en
    reutilisant exactement la meme fonction que le pipeline quotidien
    (publier_tous_facebook) : meme extraction d'introduction, meme emoji
    par silo, meme filet de securite IA, meme logging BigQuery.
    Body JSON requis : {"post_ids": [4964, 4966]}
    """
    from pipeline import (
        publier_tous_facebook, init_bigquery,
        CONFIG, FACEBOOK_CONFIG, WP_CONFIG, PROJECT_ID, DATASET_ID
    )
    import pandas as pd
    import requests as req
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
        contenus = []
        for post_id in df['post_id']:
            try:
                r = req.get(
                    f"{WP_CONFIG['url']}/wp-json/wp/v2/posts/{post_id}",
                    timeout=15
                )
                contenus.append(r.json()['content']['rendered'] if r.status_code == 200 else '')
            except Exception:
                contenus.append('')
        df_publications = pd.DataFrame({
            'Post_ID': df['post_id'],
            'Silo': df['silo'],
            'Titre': df['titre'],
            'Contenu_HTML': contenus,
        })
        def run_async():
            try:
                publier_tous_facebook(df_publications, client_bq, CONFIG, FACEBOOK_CONFIG)
                print(f"✅ Rattrapage Facebook termine : {len(df_publications)} articles traites")
            except Exception as e:
                print(f"❌ Erreur rattrapage Facebook : {e}")
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


'''

if "rattraper_facebook" in contenu:
    print("⏭️  PATCH (endpoint rattraper-facebook) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (endpoint rattraper-facebook) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("✅ PATCH (endpoint rattraper-facebook) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
