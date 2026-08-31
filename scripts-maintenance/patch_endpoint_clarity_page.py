FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/synchroniser-clarity', methods=['POST'])"

nouvelle_route = '''@app.route('/synchroniser-clarity-par-page', methods=['POST'])
def synchroniser_clarity_par_page():
    """CHANTIER G.2 : synchronise les insights Clarity PAR PAGE vers BigQuery."""
    from pipeline import rafraichir_clarity_par_page, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = rafraichir_clarity_par_page(client_bq)
            print(f"✅ Sync Clarity par page terminee : {nb} lignes")
        except Exception as e:
            print(f"❌ Erreur sync Clarity par page : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "sync": "declenche en arriere-plan"}), 200


'''

if "synchroniser_clarity_par_page" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
