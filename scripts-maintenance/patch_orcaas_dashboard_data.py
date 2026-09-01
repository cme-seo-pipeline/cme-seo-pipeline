FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def agent_orcaas_donnees_dashboard(client_bq):
    """AGENT ORCAAS -- Prepare les donnees reelles du dashboard (couche
    Dashboard/Data Analytics). Retourne un dict JSON-serialisable, la mise
    en forme visuelle (HTML/Chart.js) se fait cote server.py."""
    resultat = {"top_pages": [], "briefs_par_probleme": [], "evaluations_par_verdict": [], "erreur": None}

    try:
        df_pages = client_bq.query(f"""
            SELECT url, impressions, clics, position_moyenne, sessions, bounce_rate_pct, nb_leads
            FROM `{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie`
            WHERE impressions > 0
            ORDER BY impressions DESC LIMIT 10
        """).to_dataframe()
        for _, r in df_pages.iterrows():
            url_courte = r['url'].replace('https://www.comprendre-mon-energie.fr', '')
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
            GROUP BY verdict ORDER BY nb DESC
        """).to_dataframe()
        for _, r in df_evals.iterrows():
            resultat["evaluations_par_verdict"].append({"verdict": r['verdict'], "nb": int(r['nb'])})
    except Exception as e:
        resultat["erreur"] = (resultat["erreur"] or "") + f" evals: {e}"

    return resultat


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def agent_orcaas_donnees_dashboard" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_fonction, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
