FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = """    try:
        df_briefs = client_bq.query(f\"\"\"
            SELECT date_execution, stack, url, probleme_detecte, statut
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs`
            ORDER BY date_execution DESC LIMIT 20
        \"\"\").to_dataframe()

        df_evals = client_bq.query(f\"\"\"
            SELECT post_id, verdict, commentaire, jours_depuis_correction
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
            ORDER BY date_evaluation DESC LIMIT 20
        \"\"\").to_dataframe()"""

nouveau = """    try:
        total_briefs = client_bq.query(f\"\"\"
            SELECT COUNT(*) AS total, COUNTIF(statut='corrige') AS corriges, COUNTIF(statut='echec') AS echecs
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs`
        \"\"\").to_dataframe().iloc[0]

        df_briefs = client_bq.query(f\"\"\"
            SELECT date_execution, stack, url, probleme_detecte, statut
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs`
            ORDER BY date_execution DESC LIMIT 20
        \"\"\").to_dataframe()

        total_evals = client_bq.query(f\"\"\"
            SELECT COUNT(*) AS total, verdict FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
            GROUP BY verdict
        \"\"\").to_dataframe()

        df_evals = client_bq.query(f\"\"\"
            SELECT post_id, verdict, commentaire, jours_depuis_correction
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
            ORDER BY date_evaluation DESC LIMIT 20
        \"\"\").to_dataframe()"""

if "total_briefs = client_bq.query" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique (partie 1/2)")

# Deuxieme partie : injecter les totaux dans le texte de contexte donne a l'IA
ancien2 = """    contexte = (
        "DERNIERS BRIEFS (actions d'ORCAAS) :\\n"
        f"{df_briefs.to_string(index=False) if not df_briefs.empty else 'Aucun'}\\n\\n"
        "DERNIERES EVALUATIONS D'IMPACT :\\n"
        f"{df_evals.to_string(index=False) if not df_evals.empty else 'Aucune'}\\n\\n\""""

nouveau2 = """    contexte = (
        f"TOTAL REEL DE CORRECTIONS EFFECTUEES DEPUIS LE DEBUT : {int(total_briefs['total'])} "
        f"({int(total_briefs['corriges'])} reussies, {int(total_briefs['echecs'])} echouees) -- "
        "IMPORTANT : le detail ci-dessous ne montre QUE les 20 plus recentes, pas la totalite. "
        "Utilise TOUJOURS ce total reel dans ta reponse, jamais le nombre de lignes du detail.\\n\\n"
        "DERNIERS BRIEFS (echantillon des 20 plus recents, PAS le total) :\\n"
        f"{df_briefs.to_string(index=False) if not df_briefs.empty else 'Aucun'}\\n\\n"
        "REPARTITION DES EVALUATIONS PAR VERDICT (TOTAL REEL) :\\n"
        f"{total_evals.to_string(index=False) if not total_evals.empty else 'Aucune evaluation'}\\n\\n"
        "DERNIERES EVALUATIONS D'IMPACT (echantillon des 20 plus recentes) :\\n"
        f"{df_evals.to_string(index=False) if not df_evals.empty else 'Aucune'}\\n\\n\""""

if "TOTAL REEL DE CORRECTIONS" in contenu:
    print("SKIP : deja present (partie 2)")
elif ancien2 not in contenu:
    print("ERREUR : ancre 2 non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("OK : patch applique (partie 2/2)")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
