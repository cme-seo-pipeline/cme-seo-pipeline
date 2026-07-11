with open('pipeline.py', 'r') as f:
    content = f.read()

old = '''    # Vérification anti-doublon WordPress avant publication
    # Vérification anti-doublon WordPress avant publication
    existe_wp, post_id_existant = verifier_article_wp_existe(slug, wp_config)
    if existe_wp and post_id_existant:
        url_wp = f"{wp_config['url']}/?p={post_id_existant}"
        print(f"  ↩️ Article existant récupéré (post_id={post_id_existant})")
        logger_publication_bq(
            client_bq, post_id_existant, silo_name, titre_seo,
            brief.get('mot_cle_principal', ''), url_wp, run_id,
            sous_silo_val or ''
        )
        return {"success": True, "post_id": post_id_existant, "url": url_wp, "existant": True}'''

new = '''    # Vérification anti-doublon WordPress avant publication
    existe_wp, post_id_existant = verifier_article_wp_existe(slug, wp_config)
    if existe_wp and post_id_existant:
        titre_existant = ''
        try:
            check = requests.get(
                f"{wp_config['url']}/wp-json/wp/v2/posts/{post_id_existant}",
                auth=(wp_config['username'], wp_config['app_password']),
                timeout=10
            )
            if check.status_code == 200:
                titre_existant = check.json().get('title', {}).get('rendered', '').strip()
        except Exception as e:
            print(f"  ⚠️ Vérif titre existant échouée : {e}")

        if titre_existant and titre_existant == titre_seo.strip():
            url_wp = f"{wp_config['url']}/?p={post_id_existant}"
            print(f"  ↩️ Article existant récupéré (post_id={post_id_existant})")
            logger_publication_bq(
                client_bq, post_id_existant, silo_name, titre_seo,
                brief.get('mot_cle_principal', ''), url_wp, run_id,
                sous_silo_val or ''
            )
            return {"success": True, "post_id": post_id_existant, "url": url_wp, "existant": True}
        else:
            suffixe = datetime.now().strftime('%m%d')
            slug = f"{slug}-{suffixe}"
            print(f"  ⚠️ Collision de slug (titre different: '{titre_existant}' != '{titre_seo}')")
            print(f"  🔀 Nouveau slug généré : {slug}")'''

if old in content:
    content = content.replace(old, new, 1)
    print("✅ MATCH TROUVÉ — patch appliqué")
else:
    print("❌ AUCUN MATCH — le texte recherché n'existe pas tel quel dans pipeline.py")
    # Afficher ce qui existe réellement à cet endroit pour diagnostiquer
    idx = content.find("existe_wp, post_id_existant = verifier_article_wp_existe")
    print("--- Contenu réel autour de cette zone ---")
    print(repr(content[max(0,idx-100):idx+700]))

with open('pipeline.py', 'w') as f:
    f.write(content)
