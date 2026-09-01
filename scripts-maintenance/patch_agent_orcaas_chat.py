FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def agent_orcaas_chat(question, client_bq):
    """AGENT ORCAAS -- Interface de conversation (couche 3). Repond a une
    question en langage libre, en s'appuyant EXCLUSIVEMENT sur le contexte
    reel du projet (briefs passes, evaluations d'impact, etat actuel du
    tunnel de conversion) -- jamais en inventant une donnee absente."""
    try:
        df_briefs = client_bq.query(f"""
            SELECT date_execution, stack, url, probleme_detecte, statut
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs`
            ORDER BY date_execution DESC LIMIT 20
        """).to_dataframe()

        df_evals = client_bq.query(f"""
            SELECT post_id, verdict, commentaire, jours_depuis_correction
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
            ORDER BY date_evaluation DESC LIMIT 20
        """).to_dataframe()

        df_tunnel = client_bq.query(f"""
            SELECT url, impressions, clics, position_moyenne, sessions, bounce_rate_pct, nb_leads
            FROM `{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie`
            WHERE impressions > 0
            ORDER BY impressions DESC LIMIT 15
        """).to_dataframe()
    except Exception as e:
        return f"Erreur lors de la recuperation du contexte reel : {e}"

    contexte = (
        "DERNIERS BRIEFS (actions d'ORCAAS) :\\n"
        f"{df_briefs.to_string(index=False) if not df_briefs.empty else 'Aucun'}\\n\\n"
        "DERNIERES EVALUATIONS D'IMPACT :\\n"
        f"{df_evals.to_string(index=False) if not df_evals.empty else 'Aucune'}\\n\\n"
        "TOP 15 PAGES PAR IMPRESSIONS (tunnel de conversion) :\\n"
        f"{df_tunnel.to_string(index=False) if not df_tunnel.empty else 'Aucune'}"
    )

    prompt = (
        "Tu es ORCAAS, l'agent IA SEO qui gere le site comprendre-mon-energie.fr, "
        "avec 3 competences : technique, analytique, commercial. Tu es rigoureux, "
        "honnete (tu ne fabriques jamais de donnee ni de chiffre), et tu t'appuies "
        "UNIQUEMENT sur le contexte reel fourni ci-dessous.\\n\\n"
        f"CONTEXTE REEL DU PROJET :\\n{contexte}\\n\\n"
        f"QUESTION DU PORTEUR DE PROJET :\\n{question}\\n\\n"
        "Reponds de facon claire et concrete, en t'appuyant EXCLUSIVEMENT sur les "
        "donnees ci-dessus. Si tu n'as pas l'information pour repondre precisement, "
        "dis-le clairement plutot que d'inventer."
    )

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": CONFIG['ANTHROPIC_API_KEY'], "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": CONFIG['MODEL'], "max_tokens": 800, "messages": [{"role": "user", "content": prompt}]},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()['content'][0]['text']
    except Exception as e:
        return f"Erreur lors de la generation de la reponse : {e}"


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def agent_orcaas_chat" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_fonction, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
