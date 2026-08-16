FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/api/log-clic', methods=['POST', 'OPTIONS'])"

nouvelle_route = '''@app.route('/rafraichir-indicateurs', methods=['POST'])
def rafraichir_indicateurs():
    """
    Rafraichit les indicateurs reglementaires (CRE Gaz/Elec, ANAH Aides)
    depuis les sources officielles. Concu pour tourner periodiquement via
    Cloud Scheduler (hebdomadaire), independamment du run de redaction.
    """
    from pipeline import rafraichir_indicateurs_reglementaires, init_bigquery
    try:
        client_bq = init_bigquery()
        nb = rafraichir_indicateurs_reglementaires(client_bq)
        return jsonify({"status": "ok", "lignes_inserees": nb}), 200
    except Exception as e:
        return jsonify({"status": "error", "erreur": str(e)}), 500


'''

if "rafraichir_indicateurs" in contenu:
    print("⏭️  PATCH (endpoint rafraichissement) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (endpoint rafraichissement) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("✅ PATCH (endpoint rafraichissement) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
