FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    lignes = f.readlines()

ancre_debut = "def generer_legende_facebook(titre_article, silo_name, config):\n"
ancre_fin = "def generer_cta_html(silo_name, post_id=None):\n"

indices_debut = [i for i, l in enumerate(lignes) if l == ancre_debut]
indices_fin = [i for i, l in enumerate(lignes) if l == ancre_fin]

if len(indices_debut) != 1 or len(indices_fin) != 1:
    print(f"❌ Ancres non uniques : debut={len(indices_debut)}, fin={len(indices_fin)} — aucune modification")
else:
    i_debut = indices_debut[0]
    i_fin = indices_fin[0]

    nouveau_bloc = '''def generer_legende_facebook(titre_article, silo_name, config):
    """Genere une legende de repli pour Facebook, utilisee uniquement si
    l'extraction de l'introduction de l'article echoue."""
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


def extraire_introduction_article(contenu_html, limite=400):
    """Extrait le premier paragraphe de l'article (son introduction reelle)
    pour servir de description au post Facebook. Coupe proprement au
    dernier mot si necessaire (jamais de mot tronque)."""
    try:
        soup = BeautifulSoup(contenu_html, 'html.parser')
        premier_p = soup.find('p')
        if not premier_p:
            return None
        texte = premier_p.get_text(strip=True)
        if not texte:
            return None
        return tronquer_proprement(texte, limite)
    except Exception:
        return None


def publier_facebook(titre_article, url_article, message, facebook_config):
    """Publie un lien vers l'article sur la Page Facebook avec le message
    fourni (introduction de l'article, ou legende de repli). Facebook
    genere automatiquement l'apercu (image, titre) a partir des balises
    Open Graph de la page WordPress -- pas besoin de reuploader l'image."""
    page_id = facebook_config.get('page_id')
    access_token = facebook_config.get('access_token')
    if not page_id or not access_token:
        return False, "Configuration Facebook manquante"
    try:
        r = requests.post(
            f"https://graph.facebook.com/v21.0/{page_id}/feed",
            data={
                "message": message,
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
    """Publie chaque article du run sur la Page Facebook, avec en
    description l'introduction reelle de l'article (repli sur une legende
    generee par IA si l'extraction echoue)."""
    print("📘 PUBLICATION FACEBOOK...")
    if not facebook_config.get('access_token') or not facebook_config.get('page_id'):
        print("  ⏭️ Facebook non configure, etape ignoree")
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

        message = extraire_introduction_article(contenu_html)
        if not message:
            message = generer_legende_facebook(titre_article, silo_name, config)

        succes, resultat = publier_facebook(titre_article, url_article, message, facebook_config)
        if succes:
            print(f"  ✅ {titre_article[:50]}... — post {resultat}")
        else:
            print(f"  ❌ {titre_article[:50]}... — {resultat}")


'''

    lignes_nouveau_bloc = nouveau_bloc.splitlines(keepends=True)
    lignes = lignes[:i_debut] + lignes_nouveau_bloc + lignes[i_fin:]
    print("✅ Fonctions Facebook remplacees (introduction reelle de l'article)")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.writelines(lignes)

print("📝 Fichier sauvegarde :", FICHIER)
