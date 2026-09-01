FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def agent_orcaas_evaluer_impact(client_bq):
    """AGENT ORCAAS -- Boucle d'evaluation. Pour chaque correction passee
    (agent_orcaas_briefs, statut='corrige') pas encore evaluee, compare les
    metriques GSC avant/apres pour mesurer l'impact reel. Ferme la boucle
    apprentissage : l'agent peut consulter ses propres resultats avant sa
    prochaine decision, plutot que d'agir sans jamais verifier."""
    print("AGENT ORCAAS -- Evaluation d'impact...")

    query = f"""
    SELECT b.brief_id, b.post_id, b.date_execution, m.url
    FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs` b
    JOIN `{PROJECT_ID}.02_cleaned.wp_url_mapping` m ON m.post_id = b.post_id
    WHERE b.statut = 'corrige'
      AND b.brief_id NOT IN (
        SELECT brief_id FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
      )
    """
    try:
        df_briefs = client_bq.query(query).to_dataframe()
    except Exception as e:
        print(f"  Erreur lecture briefs : {e}")
        return 0

    if df_briefs.empty:
        print("  Aucun brief a evaluer")
        return 0

    lignes = []
    for _, row in df_briefs.iterrows():
        post_id = int(row['post_id'])
        url = row['url']
        date_correction = row['date_execution']
        brief_id = row['brief_id']

        maintenant = datetime.now(date_correction.tzinfo) if date_correction.tzinfo else datetime.now()
        jours_ecoules = (maintenant - date_correction).days

        url_norm = url.lower()
        for prefixe in ("https://www.", "http://www.", "https://", "http://"):
            if url_norm.startswith(prefixe):
                url_norm = url_norm[len(prefixe):]
                break
        url_norm = url_norm.rstrip("/")

        query_metriques = f"""
        SELECT
          SUM(CASE WHEN date < DATE('{date_correction.date()}') AND date >= DATE_SUB(DATE('{date_correction.date()}'), INTERVAL 30 DAY) THEN impressions ELSE 0 END) AS impressions_avant,
          SUM(CASE WHEN date < DATE('{date_correction.date()}') AND date >= DATE_SUB(DATE('{date_correction.date()}'), INTERVAL 30 DAY) THEN clics ELSE 0 END) AS clics_avant,
          AVG(CASE WHEN date < DATE('{date_correction.date()}') AND date >= DATE_SUB(DATE('{date_correction.date()}'), INTERVAL 30 DAY) THEN position END) AS position_avant,
          SUM(CASE WHEN date >= DATE('{date_correction.date()}') THEN impressions ELSE 0 END) AS impressions_apres,
          SUM(CASE WHEN date >= DATE('{date_correction.date()}') THEN clics ELSE 0 END) AS clics_apres,
          AVG(CASE WHEN date >= DATE('{date_correction.date()}') THEN position END) AS position_apres
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE LOWER(REGEXP_REPLACE(REGEXP_REPLACE(page, r'^https?://(www\\.)?', ''), r'/$', '')) = '{url_norm}'
        """
        try:
            df_m = client_bq.query(query_metriques).to_dataframe()
        except Exception as e:
            continue

        if df_m.empty:
            continue

        r = df_m.iloc[0]
        imp_avant = int(r['impressions_avant'] or 0)
        clics_avant = int(r['clics_avant'] or 0)
        pos_avant = float(r['position_avant']) if r['position_avant'] is not None else None
        imp_apres = int(r['impressions_apres'] or 0)
        clics_apres = int(r['clics_apres'] or 0)
        pos_apres = float(r['position_apres']) if r['position_apres'] is not None else None

        ctr_avant = (clics_avant / imp_avant) if imp_avant > 0 else None
        ctr_apres = (clics_apres / imp_apres) if imp_apres > 0 else None

        if jours_ecoules < 7 or imp_apres < 10:
            verdict = "donnees_insuffisantes"
            commentaire = f"{jours_ecoules}j ecoules, {imp_apres} impressions apres -- attendre davantage avant de conclure"
        elif ctr_avant is not None and ctr_apres is not None:
            if ctr_apres > ctr_avant * 1.1:
                verdict = "amelioration"
                commentaire = f"CTR {ctr_avant*100:.1f}% -> {ctr_apres*100:.1f}%"
            elif ctr_apres < ctr_avant * 0.9:
                verdict = "degradation"
                commentaire = f"CTR {ctr_avant*100:.1f}% -> {ctr_apres*100:.1f}%"
            else:
                verdict = "stable"
                commentaire = f"CTR {ctr_avant*100:.1f}% -> {ctr_apres*100:.1f}% (variation faible)"
        else:
            verdict = "donnees_insuffisantes"
            commentaire = "CTR non calculable (0 impression sur une des periodes)"

        lignes.append({
            "brief_id": brief_id, "post_id": post_id,
            "date_evaluation": datetime.now().isoformat(),
            "jours_depuis_correction": jours_ecoules,
            "impressions_avant": imp_avant, "clics_avant": clics_avant,
            "ctr_avant": ctr_avant, "position_avant": pos_avant,
            "impressions_apres": imp_apres, "clics_apres": clics_apres,
            "ctr_apres": ctr_apres, "position_apres": pos_apres,
            "verdict": verdict, "commentaire": commentaire,
        })

    if not lignes:
        print("  Aucune evaluation generee")
        return 0

    try:
        errors = client_bq.insert_rows_json(
            f"{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations", lignes
        )
        if errors:
            print(f"  Erreurs insertion : {errors}")
            return 0
    except Exception as e:
        print(f"  Erreur ecriture BigQuery : {e}")
        return 0

    print(f"  {len(lignes)} evaluations enregistrees")
    return len(lignes)


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def agent_orcaas_evaluer_impact" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_fonction, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
