FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''    try:
        df_evals = client_bq.query(f"""
            SELECT verdict, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
            GROUP BY verdict ORDER BY nb DESC
        """).to_dataframe()
        for _, r in df_evals.iterrows():
            resultat["evaluations_par_verdict"].append({"verdict": r['verdict'], "nb": int(r['nb'])})
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" evals: {e}"

    return resultat'''

nouveau = '''    try:
        df_evals = client_bq.query(f"""
            SELECT verdict, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
            GROUP BY verdict ORDER BY nb DESC
        """).to_dataframe()
        for _, r in df_evals.iterrows():
            resultat["evaluations_par_verdict"].append({"verdict": r['verdict'], "nb": int(r['nb'])})
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" evals: {e}"

    resultat["opportunites"] = []
    try:
        df_opp = client_bq.query(f"""
            SELECT url, silo, score_opportunite, position, impressions
            FROM `{PROJECT_ID}.03_final.seo_opportunities`
            ORDER BY score_opportunite DESC LIMIT 10
        """).to_dataframe()
        for _, r in df_opp.iterrows():
            url_courte = r['url'].replace('https://www.comprendre-mon-energie.fr', '') if r['url'] else ''
            resultat["opportunites"].append({
                "url": url_courte if url_courte else "/",
                "score": round(float(r['score_opportunite']), 1) if pd.notna(r['score_opportunite']) else 0,
                "position": round(float(r['position']), 1) if pd.notna(r['position']) else None,
            })
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" opportunites: {e}"

    resultat["rankmath_couverture"] = {"avec_mot_cle": 0, "sans_mot_cle": 0}
    try:
        df_rm = client_bq.query(f"""
            SELECT COUNTIF(rank_math_focus_keyword IS NOT NULL) AS avec, COUNTIF(rank_math_focus_keyword IS NULL) AS sans
            FROM `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data`
        """).to_dataframe()
        if not df_rm.empty:
            resultat["rankmath_couverture"] = {
                "avec_mot_cle": int(df_rm.iloc[0]['avec']) if pd.notna(df_rm.iloc[0]['avec']) else 0,
                "sans_mot_cle": int(df_rm.iloc[0]['sans']) if pd.notna(df_rm.iloc[0]['sans']) else 0,
            }
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" rankmath: {e}"

    resultat["audit_technique"] = []
    try:
        df_audit = client_bq.query(f"""
            SELECT
              CASE WHEN status_code = 200 THEN '200 OK'
                   WHEN status_code >= 300 AND status_code < 400 THEN 'Redirection'
                   WHEN status_code >= 400 THEN 'Erreur'
                   ELSE 'Autre' END AS categorie,
              COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.audit_technique_site`
            GROUP BY categorie
        """).to_dataframe()
        for _, r in df_audit.iterrows():
            resultat["audit_technique"].append({"categorie": r['categorie'], "nb": int(r['nb'])})
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" audit: {e}"

    resultat["leads_par_outil"] = []
    try:
        df_leads = client_bq.query(f"""
            SELECT tool, COUNT(*) AS nb FROM (
              SELECT tool FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
              UNION ALL
              SELECT tool FROM `{PROJECT_ID}.04_pipeline_seo.leads_app_authentifies`
            )
            GROUP BY tool ORDER BY nb DESC
        """).to_dataframe()
        for _, r in df_leads.iterrows():
            resultat["leads_par_outil"].append({"outil": r['tool'], "nb": int(r['nb'])})
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" leads: {e}"

    resultat["publications_par_silo"] = []
    try:
        df_pub = client_bq.query(f"""
            SELECT silo, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
            GROUP BY silo ORDER BY nb DESC
        """).to_dataframe()
        for _, r in df_pub.iterrows():
            resultat["publications_par_silo"].append({"silo": r['silo'], "nb": int(r['nb'])})
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" publications: {e}"

    return resultat'''

if "resultat[\"opportunites\"]" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
