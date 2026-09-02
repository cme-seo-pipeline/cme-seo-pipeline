FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ANCRE_DEBUT = "def agent_orcaas_donnees_dashboard(client_bq"
ANCRE_FIN = "def rafraichir_indicateurs_reglementaires(client_bq):"

idx_debut = contenu.find(ANCRE_DEBUT)
idx_fin = contenu.find(ANCRE_FIN)

if idx_debut == -1 or idx_fin == -1 or idx_fin < idx_debut:
    print("ERREUR : ancres non trouvees ou dans le mauvais ordre, arret sans modification")
elif "ThreadPoolExecutor" in contenu[idx_debut:idx_fin]:
    print("SKIP : deja present")
else:
    nouvelles_fonctions = '''def _dash_top_pages(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT page AS url, SUM(impressions) AS impressions, SUM(clics) AS clics, AVG(position) AS position_moyenne
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE date BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY page ORDER BY impressions DESC LIMIT 10
        """).to_dataframe()
        liste = []
        for _, r in df.iterrows():
            url_courte = r['url'].replace('https://www.comprendre-mon-energie.fr', '') if r['url'] else ''
            liste.append({
                "url": url_courte if url_courte else "/",
                "impressions": int(r['impressions']) if pd.notna(r['impressions']) else 0,
                "clics": int(r['clics']) if pd.notna(r['clics']) else 0,
                "position": round(float(r['position_moyenne']), 1) if pd.notna(r['position_moyenne']) else None,
            })
        return ("top_pages", liste, None)
    except Exception as e:
        return ("top_pages", [], f"top_pages: {e}")


def _dash_briefs(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT probleme_detecte, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs`
            WHERE DATE(date_execution) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY probleme_detecte ORDER BY nb DESC
        """).to_dataframe()
        liste = [{"probleme": r['probleme_detecte'], "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("briefs_par_probleme", liste, None)
    except Exception as e:
        return ("briefs_par_probleme", [], f"briefs: {e}")


def _dash_evals(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT verdict, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
            WHERE DATE(date_evaluation) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY verdict ORDER BY nb DESC
        """).to_dataframe()
        liste = [{"verdict": r['verdict'], "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("evaluations_par_verdict", liste, None)
    except Exception as e:
        return ("evaluations_par_verdict", [], f"evals: {e}")


def _dash_opportunites(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT url, MAX(score_opportunite) AS score_opportunite, MIN(position) AS position
            FROM `{PROJECT_ID}.03_final.seo_opportunities`
            GROUP BY url ORDER BY score_opportunite DESC LIMIT 10
        """).to_dataframe()
        liste = []
        for _, r in df.iterrows():
            url_courte = r['url'].replace('https://www.comprendre-mon-energie.fr', '') if r['url'] else ''
            liste.append({
                "url": url_courte if url_courte else "/",
                "score": round(float(r['score_opportunite']), 1) if pd.notna(r['score_opportunite']) else 0,
                "position": round(float(r['position']), 1) if pd.notna(r['position']) else None,
            })
        return ("opportunites", liste, None)
    except Exception as e:
        return ("opportunites", [], f"opportunites: {e}")


def _dash_rankmath(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT COUNTIF(rank_math_focus_keyword IS NOT NULL) AS avec, COUNTIF(rank_math_focus_keyword IS NULL) AS sans
            FROM `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data`
        """).to_dataframe()
        if df.empty:
            return ("rankmath_couverture", {"avec_mot_cle": 0, "sans_mot_cle": 0}, None)
        valeur = {
            "avec_mot_cle": int(df.iloc[0]['avec']) if pd.notna(df.iloc[0]['avec']) else 0,
            "sans_mot_cle": int(df.iloc[0]['sans']) if pd.notna(df.iloc[0]['sans']) else 0,
        }
        return ("rankmath_couverture", valeur, None)
    except Exception as e:
        return ("rankmath_couverture", {"avec_mot_cle": 0, "sans_mot_cle": 0}, f"rankmath: {e}")


def _dash_audit(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT
              CASE WHEN status_code = 200 THEN '200 OK'
                   WHEN status_code >= 300 AND status_code < 400 THEN 'Redirection'
                   WHEN status_code >= 400 THEN 'Erreur'
                   ELSE 'Autre' END AS categorie,
              COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.audit_technique_site`
            GROUP BY categorie
        """).to_dataframe()
        liste = [{"categorie": r['categorie'], "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("audit_technique", liste, None)
    except Exception as e:
        return ("audit_technique", [], f"audit: {e}")


def _dash_leads(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT tool, COUNT(*) AS nb FROM (
              SELECT tool, timestamp AS date_lead FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
              UNION ALL
              SELECT tool, derniere_maj AS date_lead FROM `{PROJECT_ID}.04_pipeline_seo.leads_app_authentifies`
            )
            WHERE DATE(date_lead) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY tool ORDER BY nb DESC
        """).to_dataframe()
        liste = [{"outil": r['tool'], "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("leads_par_outil", liste, None)
    except Exception as e:
        return ("leads_par_outil", [], f"leads: {e}")


def _dash_publications(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT silo, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
            WHERE DATE(date_publication) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY silo ORDER BY nb DESC
        """).to_dataframe()
        liste = [{"silo": r['silo'], "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("publications_par_silo", liste, None)
    except Exception as e:
        return ("publications_par_silo", [], f"publications: {e}")


def agent_orcaas_donnees_dashboard(client_bq, date_debut=None, date_fin=None):
    """AGENT ORCAAS -- Prepare les donnees reelles du dashboard (couche
    Dashboard/Data Analytics). Filtrable par date (date_debut/date_fin,
    format AAAA-MM-JJ). Les 8 requetes s'executent EN PARALLELE
    (ThreadPoolExecutor) plutot qu'en serie -- chaque requete BigQuery a un
    cout de demarrage fixe (1-3s), qui s'additionnait auparavant (dizaines
    de secondes constatees en usage reel). En parallele, le temps total
    approche celui de la requete la plus lente, pas leur somme."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

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

    taches = [_dash_top_pages, _dash_briefs, _dash_evals, _dash_opportunites,
              _dash_rankmath, _dash_audit, _dash_leads, _dash_publications]

    erreurs = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(t, client_bq, date_debut, date_fin) for t in taches]
        for future in as_completed(futures):
            try:
                cle, valeur, erreur = future.result()
                resultat[cle] = valeur
                if erreur:
                    erreurs.append(erreur)
            except Exception as e:
                erreurs.append(f"tache: {e}")

    if erreurs:
        resultat["erreur"] = " | ".join(erreurs)

    return resultat


'''
    contenu = contenu[:idx_debut] + nouvelles_fonctions + contenu[idx_fin:]
    with open(FICHIER, "w", encoding="utf-8") as f:
        f.write(contenu)
    print("OK : fonction remplacee (parallelisee)")
