FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/auditer-site-technique', methods=['POST'])"

nouvelle_route = '''@app.route('/agent-orcaas-seo-technique', methods=['POST'])
def agent_orcaas_seo_technique_endpoint():
    """AGENT ORCAAS V1 : corrige titres/meta manquants ou dupliques,
    controle total, genere un brief par intervention."""
    from pipeline import agent_orcaas_seo_technique, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = agent_orcaas_seo_technique(client_bq)
            print(f"✅ Agent ORCAAS termine : {nb} corrections")
        except Exception as e:
            print(f"❌ Erreur agent ORCAAS : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "agent": "declenche en arriere-plan"}), 200


'''

if "agent_orcaas_seo_technique_endpoint" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
