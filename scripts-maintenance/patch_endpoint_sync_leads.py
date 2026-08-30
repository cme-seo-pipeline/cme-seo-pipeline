FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/rafraichir-mapping-urls', methods=['POST'])"

nouvelle_route = '''@app.route('/synchroniser-leads-app', methods=['POST'])
def synchroniser_leads_app():
    """
    CHANTIER SOUVERAINETE SHELL : synchronise les leads des utilisateurs
    connectes a l'app (Firestore) vers BigQuery (leads_app_authentifies).
    """
    from pipeline import rafraichir_leads_app_authentifies, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = rafraichir_leads_app_authentifies(client_bq)
            print(f"✅ Sync leads app terminee : {nb} leads")
        except Exception as e:
            print(f"❌ Erreur sync leads app : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "sync": "declenche en arriere-plan"}), 200


'''

if "synchroniser_leads_app" in contenu:
    print("⏭️  PATCH (endpoint sync leads) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (endpoint sync leads) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("✅ PATCH (endpoint sync leads) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
