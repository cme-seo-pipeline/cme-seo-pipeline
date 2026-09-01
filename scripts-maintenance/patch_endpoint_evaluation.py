FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/auditer-site-technique', methods=['POST'])"

nouvelle_route = '''@app.route('/agent-orcaas-evaluer', methods=['POST'])
def agent_orcaas_evaluer_endpoint():
    """AGENT ORCAAS : evalue l'impact reel des corrections passees (GSC avant/apres)."""
    from pipeline import agent_orcaas_evaluer_impact, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = agent_orcaas_evaluer_impact(client_bq)
            print(f"✅ Evaluation ORCAAS terminee : {nb} evaluations")
        except Exception as e:
            print(f"❌ Erreur evaluation ORCAAS : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "evaluation": "declenchee en arriere-plan"}), 200


'''

if "agent_orcaas_evaluer_endpoint" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
