FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/api/log-clic', methods=['POST', 'OPTIONS'])"

nouvelle_route = '''@app.route('/rafraichir-mapping-urls', methods=['POST'])
def rafraichir_mapping_urls():
    """
    CHANTIER GROWTH ENGINEERING : reconstruit la correspondance URL -> post_id
    WordPress (table 02_cleaned.wp_url_mapping), utilisee par la vue
    seo_opportunities pour joindre GSC/GA4 sur un identifiant stable plutot
    que sur l'URL brute. Concu pour tourner quotidiennement, avant le run
    principal.
    """
    from pipeline import rafraichir_wp_url_mapping, init_bigquery

    def refresh_async():
        try:
            client_bq = init_bigquery()
            nb = rafraichir_wp_url_mapping(client_bq)
            print(f"✅ Mapping URL->post_id termine : {nb} correspondances")
        except Exception as e:
            print(f"❌ Erreur mapping URL->post_id : {e}")

    thread = threading.Thread(target=refresh_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "mapping": "declenche en arriere-plan"}), 200


'''

if "rafraichir_mapping_urls" in contenu:
    print("⏭️  PATCH (endpoint mapping URLs) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (endpoint mapping URLs) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("✅ PATCH (endpoint mapping URLs) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
