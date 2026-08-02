FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Configuration Instagram
# ============================================================
ancre1 = '''CLIENT_API_URL = os.environ.get("CLIENT_API_URL", "https://cme-client-api-217943559750.europe-west1.run.app")
BROADCAST_API_KEY = os.environ.get("BROADCAST_API_KEY", "")'''

nouveau1 = ancre1 + '''
INSTAGRAM_CONFIG = {
    "business_account_id": os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", ""),
    "access_token": os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", ""),
}'''

if "INSTAGRAM_CONFIG" in contenu:
    print("⏭️  PATCH 1 (config Instagram) : deja present, ignore")
elif ancre1 not in contenu:
    print("❌ PATCH 1 (config Instagram) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre1, nouveau1, 1)
    print("✅ PATCH 1 (config Instagram) : ajoutee")

# ============================================================
# PATCH 2 — Fonction publier_instagram, juste apres publier_facebook
# ============================================================
ancre2 = '''def logger_publication_facebook_bq(client_bq, post_id, silo, titre, url_article,
                                     facebook_post_id, message, succes, erreur=None):'''

nouvelle_fonction_publier = '''def publier_instagram(image_url, message, instagram_config):
    """Publie une image sur le compte Instagram Business, avec la legende
    fournie. Processus en 2 etapes propre a l'API Instagram : creation d'un
    conteneur media, puis publication de ce conteneur (contrairement a
    Facebook qui publie en un seul appel)."""
    import time
    ig_user_id = instagram_config.get('business_account_id')
    access_token = instagram_config.get('access_token')
    if not ig_user_id or not access_token:
        return False, "Configuration Instagram manquante"
    try:
        r1 = requests.post(
            f"https://graph.facebook.com/v21.0/{ig_user_id}/media",
            data={
                "image_url": image_url,
                "caption": message,
                "access_token": access_token
            },
            timeout=30
        )
        if r1.status_code != 200:
            return False, f"HTTP {r1.status_code} (creation) — {r1.text[:200]}"
        creation_id = r1.json().get('id', '')
        time.sleep(3)
        r2 = requests.post(
            f"https://graph.facebook.com/v21.0/{ig_user_id}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": access_token
            },
            timeout=30
        )
        if r2.status_code == 200:
            return True, r2.json().get('id', '')
        return False, f"HTTP {r2.status_code} (publication) — {r2.text[:200]}"
    except Exception as e:
        return False, str(e)


'''

if "def publier_instagram" in contenu:
    print("⏭️  PATCH 2 (fonction publier_instagram) : deja present, ignore")
elif ancre2 not in contenu:
    print("❌ PATCH 2 (fonction publier_instagram) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre2, nouvelle_fonction_publier + ancre2, 1)
    print("✅ PATCH 2 (fonction publier_instagram) : ajoutee")

# ============================================================
# PATCH 3 — Logger BQ Instagram, juste apres logger Facebook
# ============================================================
ancre3 = '''def notifier_nouveaux_articles(df_publications, config):'''

nouveau_logger = '''def logger_publication_instagram_bq(client_bq, post_id, silo, titre, url_article,
                                      instagram_post_id, message, succes, erreur=None):
    """Enregistre chaque tentative de publication Instagram dans BigQuery,
    meme logique de tracabilite que pour Facebook."""
    try:
        rows = [{
            "date_publication": datetime.now().isoformat(),
            "post_id": post_id,
            "silo": silo,
            "titre": titre,
            "url_article": url_article,
            "instagram_post_id": instagram_post_id or "",
            "message_utilise": message or "",
            "succes": succes,
            "erreur": erreur or "",
        }]
        client_bq.insert_rows_json(
            f"{PROJECT_ID}.{DATASET_ID}.historique_publications_instagram", rows
        )
    except Exception as e:
        print(f"  ⚠️ Erreur log Instagram BQ : {e}")


'''

if "def logger_publication_instagram_bq" in contenu:
    print("⏭️  PATCH 3 (logger Instagram) : deja present, ignore")
elif ancre3 not in contenu:
    print("❌ PATCH 3 (logger Instagram) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre3, nouveau_logger + ancre3, 1)
    print("✅ PATCH 3 (logger Instagram) : ajoute")

# ============================================================
# PATCH 4 — Fonction publier_tous_instagram, juste avant SILO_EMOJIS
# ============================================================
ancre4 = '''SILO_EMOJIS = {
    "1. Gaz": "🔥",'''

nouvelle_fonction_tous = '''def publier_tous_instagram(df_publications, client_bq, config, instagram_config):
    """Publie chaque article du run sur Instagram, avec l'image mise en
    avant de l'article (recuperee depuis WordPress) et la meme legende que
    Facebook, complete par un renvoi vers la bio (Instagram n'autorise pas
    les liens cliquables dans les legendes de posts)."""
    print("📸 PUBLICATION INSTAGRAM...")
    if not instagram_config.get('access_token') or not instagram_config.get('business_account_id'):
        print("  ⏭️ Instagram non configure, etape ignoree")
        return
    for idx, row in df_publications.iterrows():
        post_id = row['Post_ID']
        silo_name = row['Silo']
        titre_article = row['Titre']
        contenu_html = row.get('Contenu_HTML', '') if hasattr(row, 'get') else row['Contenu_HTML']
        try:
            df_url = client_bq.query(f"""
            SELECT url_wp FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE post_id = {post_id} LIMIT 1
            """).to_dataframe()
            url_article = df_url['url_wp'].iloc[0] if not df_url.empty else None
        except Exception:
            url_article = None
        if not url_article:
            print(f"  ⚠️ {titre_article[:50]}... — URL introuvable, ignore")
            continue
        try:
            r = requests.get(f"{WP_CONFIG['url']}/wp-json/wp/v2/posts/{post_id}?_embed", timeout=15)
            image_url = r.json()['_embedded']['wp:featuredmedia'][0]['source_url']
        except Exception:
            image_url = None
        if not image_url:
            print(f"  ⚠️ {titre_article[:50]}... — image introuvable, ignore")
            logger_publication_instagram_bq(client_bq, post_id, silo_name, titre_article,
                                             url_article, None, "", False, erreur="Image introuvable")
            continue
        message = extraire_introduction_article(contenu_html)
        if not message:
            message = generer_legende_facebook(titre_article, silo_name, config)
        emoji_silo = SILO_EMOJIS.get(silo_name, "")
        if emoji_silo and message:
            message = f"{emoji_silo} {message}"
        message = f"{message}\\n\\n🔗 Lien dans la bio"
        succes, resultat = publier_instagram(image_url, message, instagram_config)
        if succes:
            print(f"  ✅ {titre_article[:50]}... — post {resultat}")
            logger_publication_instagram_bq(client_bq, post_id, silo_name, titre_article,
                                             url_article, resultat, message, True)
        else:
            print(f"  ❌ {titre_article[:50]}... — {resultat}")
            logger_publication_instagram_bq(client_bq, post_id, silo_name, titre_article,
                                             url_article, None, message, False, erreur=resultat)


'''

if "def publier_tous_instagram" in contenu:
    print("⏭️  PATCH 4 (fonction publier_tous_instagram) : deja present, ignore")
elif ancre4 not in contenu:
    print("❌ PATCH 4 (fonction publier_tous_instagram) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre4, nouvelle_fonction_tous + ancre4, 1)
    print("✅ PATCH 4 (fonction publier_tous_instagram) : ajoutee")

# ============================================================
# PATCH 5 — Appel dans run_pipeline, juste apres Facebook
# ============================================================
ancre5 = '''    publier_tous_facebook(df_publications, client_bq, CONFIG, FACEBOOK_CONFIG)
    notifier_nouveaux_articles(df_publications, CONFIG)'''

nouveau5 = '''    publier_tous_facebook(df_publications, client_bq, CONFIG, FACEBOOK_CONFIG)
    publier_tous_instagram(df_publications, client_bq, CONFIG, INSTAGRAM_CONFIG)
    notifier_nouveaux_articles(df_publications, CONFIG)'''

if "publier_tous_instagram(df_publications, client_bq, CONFIG, INSTAGRAM_CONFIG)" in contenu and contenu.count("publier_tous_instagram(df_publications, client_bq, CONFIG, INSTAGRAM_CONFIG)") >= 1 and ancre5 not in contenu:
    print("⏭️  PATCH 5 (appel quotidien) : deja present, ignore")
elif ancre5 not in contenu:
    print("❌ PATCH 5 (appel quotidien) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre5, nouveau5, 1)
    print("✅ PATCH 5 (appel quotidien) : Instagram integre au run automatique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
