FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Ajout de FACEBOOK_CONFIG
# ============================================================
ancienne_config = '''OPENAI_CONFIG = {
    "api_key": os.environ.get("OPENAI_API_KEY", ""),
    "model": "gpt-image-1",
    "size": "1536x1024",
    "quality": "medium",
}
SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")'''

nouvelle_config = '''OPENAI_CONFIG = {
    "api_key": os.environ.get("OPENAI_API_KEY", ""),
    "model": "gpt-image-1",
    "size": "1536x1024",
    "quality": "medium",
}
SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")
FACEBOOK_CONFIG = {
    "page_id": os.environ.get("FACEBOOK_PAGE_ID", ""),
    "access_token": os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", ""),
}'''

if ancienne_config not in contenu:
    print("❌ PATCH 1 (FACEBOOK_CONFIG) : bloc non trouve")
else:
    contenu = contenu.replace(ancienne_config, nouvelle_config)
    print("✅ PATCH 1 (FACEBOOK_CONFIG) : ajoutee")

# ============================================================
# PATCH 2 — Ajout des 3 fonctions Facebook
# (inserees juste avant generer_cta_html)
# ============================================================
ancre_insertion = "def generer_cta_html(silo_name, post_id=None):"

fonctions_facebook = '''def generer_legende_facebook(titre_article, silo_name, config):
    """Genere une legende courte pour Facebook, ton different du SEO
    (plus direct, pense pour l'engagement social, pas le referencement)."""
    prompt = f"""Tu es un community manager specialise energie/renovation en France.
Ecris UNE legende Facebook courte (2-3 phrases MAX, 300 caracteres MAX) pour promouvoir cet article :

Titre : {titre_article}
Theme : {silo_name}

Contraintes :
- Ton direct, accrocheur, pas de jargon SEO
- 0 a 2 hashtags maximum, jamais plus
- Donne envie de cliquer sans etre putaclic
- Pas de guillemets autour du texte, pas de prefixe type "Legende :"

Reponds uniquement avec le texte de la legende, rien d'autre."""
    headers = {
        "x-api-key": config['ANTHROPIC_API_KEY'],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {
        "model": config['MODEL'],
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
                         headers=headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json()['content'][0]['text'].strip()
    except Exception:
        return titre_article


def publier_facebook(titre_article, url_article, silo_name, config, facebook_config):
    """Publie un lien vers l'article sur la Page Facebook. Facebook genere
    automatiquement l'apercu (image, titre) a partir des balises Open Graph
    de la page WordPress -- pas besoin de reuploader l'image separement."""
    page_id = facebook_config.get('page_id')
    access_token = facebook_config.get('access_token')
    if not page_id or not access_token:
        return False, "Configuration Facebook manquante"

    legende = generer_legende_facebook(titre_article, silo_name, config)

    try:
        r = requests.post(
            f"https://graph.facebook.com/v21.0/{page_id}/feed",
            data={
                "message": legende,
                "link": url_article,
                "access_token": access_token
            },
            timeout=30
        )
        if r.status_code == 200:
            return True, r.json().get('id', '')
        return False, f"HTTP {r.status_code} — {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def publier_tous_facebook(df_publications, client_bq, config, facebook_config):
    """Publie chaque article du run sur la Page Facebook."""
    print("📘 PUBLICATION FACEBOOK...")
    if not facebook_config.get('access_token') or not facebook_config.get('page_id'):
        print("  ⏭️ Facebook non configure, etape ignoree")
        return
    for idx, row in df_publications.iterrows():
        post_id = row['Post_ID']
        silo_name = row['Silo']
        titre_article = row['Titre']
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

        succes, resultat = publier_facebook(titre_article, url_article, silo_name, config, facebook_config)
        if succes:
            print(f"  ✅ {titre_article[:50]}... — post {resultat}")
        else:
            print(f"  ❌ {titre_article[:50]}... — {resultat}")


''' + ancre_insertion

if ancre_insertion not in contenu:
    print("❌ PATCH 2 (fonctions Facebook) : point d'insertion non trouve")
elif "def publier_facebook(" in contenu:
    print("⏭️  PATCH 2 (fonctions Facebook) : deja presentes, ignore")
else:
    contenu = contenu.replace(ancre_insertion, fonctions_facebook, 1)
    print("✅ PATCH 2 (fonctions Facebook) : 3 fonctions ajoutees")

# ============================================================
# PATCH 3 — Appel dans run_pipeline(), juste apres les featured images
# ============================================================
ancien_appel = '''    generer_featured_images(df_publications, client_bq, CONFIG, OPENAI_CONFIG, WP_CONFIG)
    print(f"\\n{'='*60}")'''

nouvel_appel = '''    generer_featured_images(df_publications, client_bq, CONFIG, OPENAI_CONFIG, WP_CONFIG)
    # ── PUBLICATION FACEBOOK ────────────────────────────────
    publier_tous_facebook(df_publications, client_bq, CONFIG, FACEBOOK_CONFIG)
    print(f"\\n{'='*60}")'''

if ancien_appel not in contenu:
    print("❌ PATCH 3 (appel run_pipeline) : bloc non trouve")
else:
    contenu = contenu.replace(ancien_appel, nouvel_appel)
    print("✅ PATCH 3 (appel run_pipeline) : integre")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("\n📝 Fichier sauvegarde :", FICHIER)
