FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ANCRE_DEBUT = "def agent_orcaas_donnees_dashboard(client_bq):"
ANCRE_FIN = "def rafraichir_indicateurs_reglementaires(client_bq):"

idx_debut = contenu.find(ANCRE_DEBUT)
idx_fin = contenu.find(ANCRE_FIN)

if idx_debut == -1 or idx_fin == -1 or idx_fin < idx_debut:
    print("ERREUR : ancres non trouvees ou dans le mauvais ordre, arret sans modification")
elif "date_debut=None" in contenu[idx_debut:idx_fin]:
    print("SKIP : deja present")
else:
    nouvelle_fonction = '''def agent_orcaas_donnees_dashboard(client_bq, date_debut=None, date_fin=None):
    """AGENT ORCAAS -- Prepare les donnees reelles du dashboard (couche
    Dashboard/Data Analytics). Filtrable par date (date_debut/date_fin,
    format AAAA-MM-JJ) pour les sections temporelles (pages GSC, briefs,
    leads, publications). Les sections d'etat actuel (couverture RankMath,
    sante technique) restent toujours l'etat present, non filtrees par
    date -- filtrer "l'etat technique actuel du site" sur une periode
    passee n'aurait pas de sens. Retourne un dict JSON-serialisable."""
    if not date_debut:
        date_debut = (datetime.now().date() - timedelta(days=30)).isoformat()
    if not date_fin:
        date_fin = datetime.now().date().isoformat()

    resultat = {
        "date_debut": date_debut, "date_fin": date_fin,
        "top_pages": [], "briefs_par_probleme": [], "evaluations_par_verdict": [],
        "opportunites": [], "rankmath_couverture": {"avec_mot_cle": 0, "sans_mot_cle": 0},
        "audit_technique": [], "leads_par_outil": [], "publications_par_silo": [],
        "erreur": None,
    }

    try:
        df_pages = client_bq.query(f"""
            SELECT page AS url, SUM(impressions) AS impressions, SUM(clics) AS clics, AVG(position) AS position_moyenne
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE date BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY page
            ORDER BY impressions DESC LIMIT 10
        """).to_dataframe()
        for _, r in df_pages.iterrows():
            url_courte = r['url'].replace('https://www.comprendre-mon-energie.fr', '') if r['url'] else ''
            resultat["top_pages"].append({
                "url": url_courte if url_courte else "/",
                "impressions": int(r['impressions']) if pd.notna(r['impressions']) else 0,
                "clics": int(r['clics']) if pd.notna(r['clics']) else 0,
                "position": round(float(r['position_moyenne']), 1) if pd.notna(r['position_moyenne']) else None,
            })
    except Exception as e:
        resultat["erreur"] = f"top_pages: {e}"

    try:
        df_briefs = client_bq.query(f"""
            SELECT probleme_detecte, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs`
            WHERE DATE(date_execution) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY probleme_detecte ORDER BY nb DESC
        """).to_dataframe()
        for _, r in df_briefs.iterrows():
            resultat["briefs_par_probleme"].append({"probleme": r['probleme_detecte'], "nb": int(r['nb'])})
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" briefs: {e}"

    try:
        df_evals = client_bq.query(f"""
            SELECT verdict, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
            WHERE DATE(date_evaluation) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY verdict ORDER BY nb DESC
        """).to_dataframe()
        for _, r in df_evals.iterrows():
            resultat["evaluations_par_verdict"].append({"verdict": r['verdict'], "nb": int(r['nb'])})
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" evals: {e}"

    try:
        df_opp = client_bq.query(f"""
            SELECT url, ANY_VALUE(silo) AS silo,
                   MAX(score_opportunite) AS score_opportunite,
                   MIN(position) AS position,
                   SUM(impressions) AS impressions
            FROM `{PROJECT_ID}.03_final.seo_opportunities`
            GROUP BY url
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

    try:
        df_leads = client_bq.query(f"""
            SELECT tool, COUNT(*) AS nb FROM (
              SELECT tool, timestamp AS date_lead FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
              UNION ALL
              SELECT tool, derniere_maj AS date_lead FROM `{PROJECT_ID}.04_pipeline_seo.leads_app_authentifies`
            )
            WHERE DATE(date_lead) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY tool ORDER BY nb DESC
        """).to_dataframe()
        for _, r in df_leads.iterrows():
            resultat["leads_par_outil"].append({"outil": r['tool'], "nb": int(r['nb'])})
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" leads: {e}"

    try:
        df_pub = client_bq.query(f"""
            SELECT silo, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
            WHERE DATE(date_publication) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY silo ORDER BY nb DESC
        """).to_dataframe()
        for _, r in df_pub.iterrows():
            resultat["publications_par_silo"].append({"silo": r['silo'], "nb": int(r['nb'])})
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" publications: {e}"

    return resultat


'''
    contenu = contenu[:idx_debut] + nouvelle_fonction + contenu[idx_fin:]
    with open(FICHIER, "w", encoding="utf-8") as f:
        f.write(contenu)
    print("OK : fonction remplacee (filtrable par date)")
