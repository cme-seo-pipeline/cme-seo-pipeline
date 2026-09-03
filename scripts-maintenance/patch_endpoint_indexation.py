FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/auditer-site-technique', methods=['POST'])"

nouvelle_route = '''@app.route('/synchroniser-indexation', methods=['POST'])
def synchroniser_indexation_endpoint():
    """CHANTIER INDEXATION : verifie l'indexation Google reelle de chaque page."""
    from pipeline import synchroniser_indexation, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = synchroniser_indexation(client_bq)
            print(f"✅ Sync indexation terminee : {nb} pages")
        except Exception as e:
            print(f"❌ Erreur sync indexation : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "sync": "declenche en arriere-plan"}), 200


'''

if "synchroniser_indexation_endpoint" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
