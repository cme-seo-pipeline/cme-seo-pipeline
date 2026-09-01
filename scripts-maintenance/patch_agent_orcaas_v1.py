FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def agent_orcaas_seo_technique(client_bq):
    """AGENT ORCAAS V1 -- Stack SEO technique/commercial. Corrige les titres
    RankMath et meta descriptions manquants ou dupliques, en privilegiant
    une approche commerciale/transactionnelle (constat du porteur de projet :
    contenu trop informationnel, CTR faible) plutot que purement descriptive.
    Genere un brief pour chaque intervention, ecrit directement en base
    WordPress via WP-CLI. Controle total : pas de validation humaine par
    correction (decision du 01/09/2026)."""
    print("AGENT ORCAAS -- Stack SEO technique/commercial...")

    query = f"""
    WITH doublons_titre AS (
      SELECT rank_math_title FROM `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data`
      WHERE rank_math_title IS NOT NULL
      GROUP BY rank_math_title HAVING COUNT(*) > 1
    ),
    doublons_meta AS (
      SELECT rank_math_description FROM `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data`
      WHERE rank_math_description IS NOT NULL
      GROUP BY rank_math_description HAVING COUNT(*) > 1
    )
    SELECT r.post_id, m.url, r.rank_math_title, r.rank_math_description, r.rank_math_focus_keyword,
      CASE
        WHEN r.rank_math_title IS NULL THEN 'titre_manquant'
        WHEN r.rank_math_title IN (SELECT rank_math_title FROM doublons_titre) THEN 'titre_duplique'
        ELSE NULL
      END AS probleme_titre,
      CASE
        WHEN r.rank_math_description IS NULL THEN 'meta_manquante'
        WHEN r.rank_math_description IN (SELECT rank_math_description FROM doublons_meta) THEN 'meta_dupliquee'
        ELSE NULL
      END AS probleme_meta
    FROM `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data` r
    JOIN `{PROJECT_ID}.02_cleaned.wp_url_mapping` m ON m.post_id = r.post_id
    """
    df = client_bq.query(query).to_dataframe()
    df_problemes = df[(df['probleme_titre'].notna()) | (df['probleme_meta'].notna())]

    if df_problemes.empty:
        print("  Aucun probleme detecte")
        return 0

    print(f"  {len(df_problemes)} page(s) a corriger")

    import io
    import paramiko
    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname="109.234.167.170", port=22, username="jolu5920", pkey=pkey, timeout=15)
    except Exception as e:
        print(f"  Erreur connexion SSH : {e}")
        return 0

    wp_path = "/home/jolu5920/public_html/comprendre-mon-energie.com"
    briefs = []
    corrections_reussies = 0

    for _, row in df_problemes.iterrows():
        post_id = int(row['post_id'])
        url = row['url']
        titre_actuel = row['rank_math_title']
        meta_actuelle = row['rank_math_description']
        mot_cle = row['rank_math_focus_keyword'] or ''
        probleme_titre = row['probleme_titre']
        probleme_meta = row['probleme_meta']
        probleme_texte = ' + '.join([p for p in [probleme_titre, probleme_meta] if p])

        prompt = (
            "Tu es un expert SEO technique ET commercial pour un site francais sur "
            "l'energie (gaz/electricite/renovation/aides).\\n"
            f"Cette page a un probleme de metadonnees : {probleme_texte}\\n"
            f"URL : {url}\\n"
            f"Mot-cle cible : {mot_cle or chr(39)+'non defini, deduis-le de l url'+chr(39)}\\n"
            f"Titre actuel : {titre_actuel or 'AUCUN'}\\n"
            f"Meta actuelle : {meta_actuelle or 'AUCUNE'}\\n\\n"
            "Genere un NOUVEAU titre SEO (entre 50 et 60 caracteres) ET une NOUVELLE "
            "meta description (entre 140 et 160 caracteres).\\n"
            "Constat important : le contenu du site est trop informationnel, ce qui "
            "limite le taux de clic (CTR). Privilegie une approche COMMERCIALE et "
            "TRANSACTIONNELLE (benefice concret, chiffre, incitation a l'action) "
            "plutot que purement descriptive -- sans jamais inventer de donnee fausse "
            "(pas de prix ou pourcentage invente).\\n\\n"
            'Reponds UNIQUEMENT avec un JSON strict, rien d\\'autre : {"titre": "...", "meta": "..."}'
        )

        nouveau_titre = titre_actuel
        nouvelle_meta = meta_actuelle
        erreur = None

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CONFIG['ANTHROPIC_API_KEY'], "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": CONFIG['MODEL'], "max_tokens": 300, "messages": [{"role": "user", "content": prompt}]},
                timeout=30
            )
            resp.raise_for_status()
            texte = resp.json()['content'][0]['text']
            texte_json = texte[texte.find('{'):texte.rfind('}')+1]
            correction = json.loads(texte_json)
            nouveau_titre = correction.get('titre', titre_actuel)
            nouvelle_meta = correction.get('meta', meta_actuelle)
        except Exception as e:
            erreur = f"Generation IA : {str(e)[:200]}"

        if erreur:
            briefs.append({
                "brief_id": f"{post_id}_{int(datetime.now().timestamp())}",
                "date_execution": datetime.now().isoformat(),
                "stack": "seo_technique", "post_id": post_id, "url": url,
                "probleme_detecte": probleme_texte,
                "valeur_avant": titre_actuel or meta_actuelle or "",
                "valeur_apres": "", "statut": "echec", "erreur": erreur,
            })
            continue

        titre_echap = nouveau_titre.replace('"', '\\\\"')
        meta_echap = nouvelle_meta.replace('"', '\\\\"')
        try:
            cmd = (f'wp --path="{wp_path}" post meta update {post_id} rank_math_title "{titre_echap}" && '
                   f'wp --path="{wp_path}" post meta update {post_id} rank_math_description "{meta_echap}"')
            stdin, stdout, stderr = ssh.exec_command(cmd)
            sortie_erreur = stderr.read().decode()
            if sortie_erreur and 'Success' not in sortie_erreur:
                raise Exception(sortie_erreur[:200])
            corrections_reussies += 1
            statut = "corrige"
            erreur = None
        except Exception as e:
            statut = "echec"
            erreur = f"Ecriture WP-CLI : {str(e)[:200]}"

        briefs.append({
            "brief_id": f"{post_id}_{int(datetime.now().timestamp())}",
            "date_execution": datetime.now().isoformat(),
            "stack": "seo_technique", "post_id": post_id, "url": url,
            "probleme_detecte": probleme_texte,
            "valeur_avant": f"Titre: {titre_actuel or 'AUCUN'} | Meta: {meta_actuelle or 'AUCUNE'}",
            "valeur_apres": f"Titre: {nouveau_titre} | Meta: {nouvelle_meta}",
            "statut": statut, "erreur": erreur,
        })

    ssh.close()

    if not briefs:
        print("  Aucun brief genere")
        return 0

    try:
        table_ref = f"{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs"
        errors = client_bq.insert_rows_json(table_ref, briefs)
        if errors:
            print(f"  Erreurs insertion briefs : {errors}")
    except Exception as e:
        print(f"  Erreur ecriture briefs BigQuery : {e}")

    print(f"  {corrections_reussies}/{len(briefs)} corrections reussies")
    return corrections_reussies


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def agent_orcaas_seo_technique" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_fonction, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
