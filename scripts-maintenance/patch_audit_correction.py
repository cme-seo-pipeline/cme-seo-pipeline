FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelles_fonctions = '''def auditer_article(post_id, titre, indicateur, valeur_actuelle, unite, config):
    """CHANTIER MISE A JOUR DES ARTICLES : verifie si un article cite une
    valeur reglementaire precise comme un fait actuel (pas un exemple
    fictif), et si elle est devenue obsolete, genere directement le
    passage corrige. Un seul appel IA combine verification + correction
    pour limiter la latence."""
    try:
        r_article = requests.get(
            f"https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts/{post_id}",
            timeout=20
        )
        if r_article.status_code != 200:
            return {"post_id": post_id, "statut": "erreur", "detail": "article introuvable"}
        contenu_html = r_article.json()['content']['rendered']
    except Exception as e:
        return {"post_id": post_id, "statut": "erreur", "detail": str(e)}

    prompt = f"""Tu es un auditeur de contenu factuel, rigoureux et prudent.

ARTICLE (titre) : {titre}

CONTENU HTML DE L'ARTICLE :
{contenu_html[:6000]}

DONNEE OFFICIELLE ACTUELLE A VERIFIER :
- Indicateur : {indicateur}
- Valeur actuelle en vigueur : {valeur_actuelle} {unite}

TACHE :
1. Determine si cet article presente une valeur CHIFFREE PRECISE pour "{indicateur}" comme un FAIT REGLEMENTAIRE ACTUEL (pas un exemple fictif, pas une simulation avec "imaginons"/"exemple"/"prenons le cas").
2. Si oui ET que cette valeur differe de la valeur actuelle ci-dessus, propose une correction MINIMALE : reprends EXACTEMENT le meme passage HTML mais avec la valeur mise a jour, sans rien changer d'autre au style, a la structure ou au reste du texte. Arrondis a 2 decimales maximum.

Reponds UNIQUEMENT en JSON strict, sans texte autour :
{{
  "cite_donnee_reelle": true ou false,
  "valeur_obsolete": true ou false,
  "passage_exact_html": "le passage HTML exact copie mot pour mot si cite_donnee_reelle=true, sinon chaine vide",
  "passage_corrige_html": "le meme passage avec la valeur mise a jour si valeur_obsolete=true, sinon chaine vide",
  "justification": "1 phrase expliquant ta decision"
}}"""
    headers = {
        "x-api-key": config['ANTHROPIC_API_KEY'],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {"model": config['MODEL'], "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]}
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=60)
        texte = r.json()['content'][0]['text'].strip()
        texte = re.sub(r'^```json\\s*|```\\s*$', '', texte, flags=re.IGNORECASE)
        verdict = json.loads(texte)
        verdict['post_id'] = post_id
        verdict['contenu_html_actuel'] = contenu_html
        verdict['statut'] = 'ok'
        return verdict
    except Exception as e:
        return {"post_id": post_id, "statut": "erreur", "detail": str(e)}


def appliquer_correction_article(verdict, wp_config, client_bq):
    """Applique la correction d'un article via l'API REST WordPress, avec
    verification de securite que le passage exact existe bien avant de le
    remplacer (annule silencieusement sinon, plutot que de risquer une
    modification incorrecte). Journalise chaque correction pour tracabilite,
    meme en l'absence de validation humaine."""
    post_id = verdict['post_id']
    passage_avant = verdict['passage_exact_html']
    passage_apres = verdict['passage_corrige_html']
    contenu_actuel = verdict['contenu_html_actuel']

    if not passage_avant or passage_avant not in contenu_actuel:
        print(f"  ⚠️ Post {post_id} : passage exact non retrouve, correction annulee par securite")
        return False

    nouveau_contenu = contenu_actuel.replace(passage_avant, passage_apres, 1)

    try:
        r = requests.post(
            f"https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts/{post_id}",
            auth=(wp_config['USER'], wp_config['APP_PASSWORD']),
            json={"content": nouveau_contenu},
            timeout=30
        )
        if r.status_code != 200:
            print(f"  ❌ Post {post_id} : echec MAJ WordPress ({r.status_code})")
            return False
    except Exception as e:
        print(f"  ❌ Post {post_id} : erreur MAJ WordPress ({e})")
        return False

    try:
        client_bq.insert_rows_json(f"{PROJECT_ID}.{DATASET_ID}.corrections_articles_auto", [{
            "post_id": post_id,
            "titre": verdict.get('titre', ''),
            "indicateur": verdict.get('indicateur', ''),
            "passage_avant": passage_avant,
            "passage_apres": passage_apres,
            "date_correction": datetime.now().isoformat(),
            "url_wp": verdict.get('url_wp', ''),
        }])
    except Exception as e:
        print(f"  ⚠️ Post {post_id} : correction appliquee mais log echoue ({e})")

    print(f"  ✅ Post {post_id} corrige automatiquement")
    return True


def auditer_et_corriger_articles(client_bq, config, wp_config):
    """CHANTIER MISE A JOUR DES ARTICLES PUBLIES : audite tous les candidats
    en pertinence directe (mapping_indicateur_sous_silo) et corrige
    automatiquement, sans validation humaine, toute citation reelle
    devenue obsolete. Concu pour tourner periodiquement (mensuel) via
    Cloud Scheduler."""
    print("🔍 AUDIT ARTICLES — recherche de citations obsoletes...")
    try:
        df_candidats = client_bq.query(f"""
        SELECT DISTINCT m.indicateur, h.post_id, h.titre, h.url_wp
        FROM `{PROJECT_ID}.{DATASET_ID}.mapping_indicateur_sous_silo` m
        JOIN `{PROJECT_ID}.{DATASET_ID}.historique_publications` h
            ON h.silo = m.silo AND h.sous_silo_strategique = m.sous_silo_strategique
        WHERE m.pertinence = 'directe'
        """).to_dataframe()
        df_valeurs = client_bq.query(f"""
        SELECT indicateur, valeur, unite,
          ROW_NUMBER() OVER (PARTITION BY indicateur ORDER BY date_verification DESC) as rang
        FROM `{PROJECT_ID}.{DATASET_ID}.indicateurs_reglementaires`
        QUALIFY rang = 1
        """).to_dataframe()
    except Exception as e:
        print(f"  ⚠️ Erreur chargement candidats : {e}")
        return {"audites": 0, "corriges": 0}

    valeurs = {r['indicateur']: (r['valeur'], r['unite']) for _, r in df_valeurs.iterrows()}
    nb_audites = 0
    nb_corriges = 0
    for _, row in df_candidats.iterrows():
        if row['indicateur'] not in valeurs:
            continue
        valeur, unite = valeurs[row['indicateur']]
        verdict = auditer_article(row['post_id'], row['titre'], row['indicateur'], valeur, unite, config)
        nb_audites += 1
        if verdict.get('statut') != 'ok':
            continue
        if verdict.get('cite_donnee_reelle') and verdict.get('valeur_obsolete'):
            verdict['titre'] = row['titre']
            verdict['url_wp'] = row['url_wp']
            verdict['indicateur'] = row['indicateur']
            if appliquer_correction_article(verdict, wp_config, client_bq):
                nb_corriges += 1
    print(f"🔍 AUDIT TERMINE : {nb_audites} article(s) audite(s), {nb_corriges} corrige(s)")
    return {"audites": nb_audites, "corriges": nb_corriges}


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def auditer_article" in contenu:
    print("⏭️  PATCH (audit + correction articles) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (audit + correction articles) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelles_fonctions, 1)
    print("✅ PATCH (audit + correction articles) : 3 fonctions ajoutees")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
