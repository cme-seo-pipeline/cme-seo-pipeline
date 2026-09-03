FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''@app.route('/synchroniser-indexation', methods=['POST'])
def synchroniser_indexation_endpoint():
    """CHANTIER INDEXATION : verifie l'indexation Google reelle de chaque page."""
    from pipeline import synchroniser_indexation, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = synchroniser_indexation(client_bq)
            print(f"✅ Sync indexation terminee : {nb} pages")
        except Exception as e:
            print(f"❌ Erreur sync indexation : {e}")'''

nouveau = '''@app.route('/synchroniser-indexation', methods=['POST'])
def synchroniser_indexation_endpoint():
    """CHANTIER INDEXATION : verifie l'indexation Google reelle de chaque
    page. Parametre optionnel ?limite=N pour tester sur un petit lot."""
    from pipeline import synchroniser_indexation, init_bigquery

    limite = request.args.get('limite')
    limite = int(limite) if limite else None

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = synchroniser_indexation(client_bq, limite=limite)
            print(f"✅ Sync indexation terminee : {nb} pages")
        except Exception as e:
            print(f"❌ Erreur sync indexation : {e}")'''

if "limite = request.args.get('limite')" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
