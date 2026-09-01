FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''    print("🔗 RAFRAICHISSEMENT MAPPING URL → POST_ID...")
    lignes = []
    page = 1
    try:
        while True:
            r = requests.get(
                "https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts",
                params={"per_page": 100, "page": page, "status": "publish", "_fields": "id,link"},
                timeout=30
            )
            if r.status_code != 200:
                break
            data = r.json()
            if not data:
                break
            for post in data:
                url = post.get('link', '')
                lignes.append({
                    "post_id": post.get('id'),
                    "url": url,
                    "url_normalized": normaliser_url(url),
                    "date_maj": datetime.now().isoformat(),
                })
            page += 1
    except Exception as e:
        print(f"  ⚠️ Erreur recuperation posts WordPress : {e}")
        if not lignes:
            return 0'''

nouveau = '''    print("🔗 RAFRAICHISSEMENT MAPPING URL → POST_ID...")
    lignes = []
    # CHANTIER G.3 (correctif decouvert lors de l'audit technique) : les
    # pages WordPress statiques (accueil, outils comparateur/aides/solaire,
    # demande-confirmee...) sont un TYPE DE CONTENU DIFFERENT des articles
    # de blog dans l'API REST WordPress (endpoint /pages, pas /posts).
    # Elles etaient absentes du mapping, cassant silencieusement la
    # resolution des leads generes directement depuis les pages outils.
    for type_contenu in ("posts", "pages"):
        page_num = 1
        try:
            while True:
                r = requests.get(
                    f"https://www.comprendre-mon-energie.fr/wp-json/wp/v2/{type_contenu}",
                    params={"per_page": 100, "page": page_num, "status": "publish", "_fields": "id,link"},
                    timeout=30
                )
                if r.status_code != 200:
                    break
                data = r.json()
                if not data:
                    break
                for post in data:
                    url = post.get('link', '')
                    lignes.append({
                        "post_id": post.get('id'),
                        "url": url,
                        "url_normalized": normaliser_url(url),
                        "date_maj": datetime.now().isoformat(),
                    })
                page_num += 1
        except Exception as e:
            print(f"  ⚠️ Erreur recuperation {type_contenu} WordPress : {e}")
    if not lignes:
        return 0'''

if "type_contenu in (\"posts\", \"pages\")" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
