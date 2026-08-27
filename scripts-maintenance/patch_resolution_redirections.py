FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''    if not lignes:
        print("  ⚠️ Aucun post recupere, mapping non mis a jour")
        return 0

    try:
        from google.cloud import bigquery as bq_module'''

nouveau = '''    if not lignes:
        print("  ⚠️ Aucun post recupere, mapping non mis a jour")
        return 0

    # CHANTIER GROWTH ENGINEERING (suite) : resolution des anciennes URLs.
    # Google Search Console peut encore rapporter des URLs d'avant une
    # restructuration du site (l'index Google met du temps a se mettre a
    # jour). WordPress redirige proprement (301) ces anciennes URLs vers
    # les nouvelles, mais notre mapping ne le savait pas jusqu'ici. On
    # suit ces redirections pour ajouter ces anciennes URLs comme alias
    # du meme post_id, dans le meme lot que celui charge plus bas.
    try:
        urls_connues = {l['url_normalized'] for l in lignes}
        df_gsc_urls = client_bq.query(f"""
        SELECT DISTINCT page AS url
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        """).to_dataframe()

        nb_redirects_resolus = 0
        for _, row_gsc in df_gsc_urls.iterrows():
            url_gsc = row_gsc['url']
            url_gsc_norm = normaliser_url(url_gsc)
            if not url_gsc_norm or url_gsc_norm in urls_connues:
                continue
            try:
                r_head = requests.head(url_gsc, allow_redirects=True, timeout=10)
                url_finale_norm = normaliser_url(r_head.url)
                if url_finale_norm == url_gsc_norm:
                    continue
                match = next((l for l in lignes if l['url_normalized'] == url_finale_norm), None)
                if match:
                    lignes.append({
                        "post_id": match['post_id'],
                        "url": url_gsc,
                        "url_normalized": url_gsc_norm,
                        "date_maj": datetime.now().isoformat(),
                    })
                    urls_connues.add(url_gsc_norm)
                    nb_redirects_resolus += 1
            except Exception:
                continue
        if nb_redirects_resolus:
            print(f"  🔀 {nb_redirects_resolus} ancienne(s) URL(s) reliee(s) a un post_id via redirection")
    except Exception as e:
        print(f"  ⚠️ Erreur resolution redirections : {e}")

    try:
        from google.cloud import bigquery as bq_module'''

if "resolution des anciennes URLs" in contenu:
    print("⏭️  PATCH (resolution redirections) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (resolution redirections) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (resolution redirections) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
