FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/api/log-clic', methods=['POST', 'OPTIONS'])"

nouvelle_route = '''@app.route('/auditer-articles', methods=['POST'])
def auditer_articles():
    """
    CHANTIER MISE A JOUR DES ARTICLES PUBLIES : audite tous les candidats
    en pertinence directe et corrige automatiquement, sans validation
    humaine, toute citation reelle devenue obsolete. Tourne en
    arriere-plan (audit de dizaines d'articles = plusieurs minutes).
    Concu pour tourner periodiquement via Cloud Scheduler (mensuel).
    """
    from pipeline import auditer_et_corriger_articles, init_bigquery, CONFIG, WP_CONFIG

    def audit_async():
        try:
            client_bq = init_bigquery()
            resultat = auditer_et_corriger_articles(client_bq, CONFIG, WP_CONFIG)
            print(f"✅ Audit articles termine : {resultat}")
        except Exception as e:
            print(f"❌ Erreur audit articles : {e}")

    thread = threading.Thread(target=audit_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "audit": "declenche en arriere-plan"}), 200


'''

if "auditer_articles" in contenu:
    print("⏭️  PATCH (endpoint audit articles) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (endpoint audit articles) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("✅ PATCH (endpoint audit articles) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
