FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/synchroniser-leads-app', methods=['POST'])"

nouvelle_route = '''@app.route('/synchroniser-clarity', methods=['POST'])
def synchroniser_clarity():
    """
    CHANTIER SOUVERAINETE SHELL : synchronise les insights Microsoft
    Clarity vers BigQuery (clarity_insights_quotidien).
    """
    from pipeline import rafraichir_clarity_insights, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = rafraichir_clarity_insights(client_bq)
            print(f"✅ Sync Clarity terminee : {nb} metriques")
        except Exception as e:
            print(f"❌ Erreur sync Clarity : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "sync": "declenche en arriere-plan"}), 200


'''

if "synchroniser_clarity" in contenu:
    print("⏭️  PATCH (endpoint sync Clarity) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (endpoint sync Clarity) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("✅ PATCH (endpoint sync Clarity) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
