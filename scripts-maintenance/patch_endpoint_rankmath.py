FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/auditer-site-technique', methods=['POST'])"

nouvelle_route = '''@app.route('/synchroniser-rankmath', methods=['POST'])
def synchroniser_rankmath_endpoint():
    """CHANTIER G.3 : synchronise les donnees SEO RankMath vers BigQuery."""
    from pipeline import synchroniser_rankmath, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = synchroniser_rankmath(client_bq)
            print(f"✅ Sync RankMath terminee : {nb} lignes")
        except Exception as e:
            print(f"❌ Erreur sync RankMath : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "sync": "declenche en arriere-plan"}), 200


'''

if "synchroniser_rankmath_endpoint" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
