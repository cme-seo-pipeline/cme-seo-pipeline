FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''    resultat["opportunites"] = []
    try:
        df_opp = client_bq.query(f"""
            SELECT url, silo, score_opportunite, position, impressions
            FROM `{PROJECT_ID}.03_final.seo_opportunities`
            ORDER BY score_opportunite DESC LIMIT 10
        """).to_dataframe()'''

nouveau = '''    resultat["opportunites"] = []
    try:
        # CORRECTIF : seo_opportunities a une ligne par requete de recherche,
        # pas par page -- une meme page ciblee par plusieurs requetes
        # apparaissait donc plusieurs fois dans le dashboard. On agrege
        # desormais par URL (meilleur score, meilleure position, impressions
        # cumulees) pour une vraie vue par page.
        df_opp = client_bq.query(f"""
            SELECT url, ANY_VALUE(silo) AS silo,
                   MAX(score_opportunite) AS score_opportunite,
                   MIN(position) AS position,
                   SUM(impressions) AS impressions
            FROM `{PROJECT_ID}.03_final.seo_opportunities`
            GROUP BY url
            ORDER BY score_opportunite DESC LIMIT 10
        """).to_dataframe()'''

if "ANY_VALUE(silo)" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
