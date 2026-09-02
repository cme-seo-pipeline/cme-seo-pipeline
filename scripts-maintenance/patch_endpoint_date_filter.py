FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''@app.route('/orcaas-dashboard-data', methods=['GET'])
def orcaas_dashboard_data_endpoint():
    """Donnees JSON du dashboard (page publique, appelee en arriere-plan par /orcaas)."""
    from pipeline import agent_orcaas_donnees_dashboard, init_bigquery
    try:
        client_bq = init_bigquery()
        donnees = agent_orcaas_donnees_dashboard(client_bq)
        return jsonify(donnees), 200
    except Exception as e:
        return jsonify({"top_pages": [], "briefs_par_probleme": [], "evaluations_par_verdict": [], "erreur": str(e)}), 500'''

nouveau = '''@app.route('/orcaas-dashboard-data', methods=['GET'])
def orcaas_dashboard_data_endpoint():
    """Donnees JSON du dashboard (page publique, appelee en arriere-plan par
    /orcaas). Parametres optionnels : ?date_debut=AAAA-MM-JJ&date_fin=AAAA-MM-JJ
    (par defaut : 30 derniers jours)."""
    from pipeline import agent_orcaas_donnees_dashboard, init_bigquery
    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    try:
        client_bq = init_bigquery()
        donnees = agent_orcaas_donnees_dashboard(client_bq, date_debut, date_fin)
        return jsonify(donnees), 200
    except Exception as e:
        return jsonify({"top_pages": [], "briefs_par_probleme": [], "evaluations_par_verdict": [], "erreur": str(e)}), 500'''

if "date_debut = request.args.get" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
