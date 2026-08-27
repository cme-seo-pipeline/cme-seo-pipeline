FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def normaliser_url(url):
    """Normalise une URL pour comparaison stable : protocole et www retires,
    slash final retire, minuscules. Doit rester identique a la logique
    utilisee cote SQL dans la vue seo_opportunities."""
    import re as re_mod
    if not url:
        return ""
    u = re_mod.sub(r'^https?://(www\\\\.)?', '', url.strip().lower())
    u = re_mod.sub(r'/$', '', u)
    return u


def rafraichir_wp_url_mapping(client_bq):
    """CHANTIER GROWTH ENGINEERING : reconstruit la table de correspondance
    URL -> post_id WordPress, source de verite pour toute jointure future
    (au lieu de comparer des URLs brutes, fragiles face aux restructurations
    de site). Interroge directement l'API WordPress (etat reel actuel),
    pagine sur tous les articles publies, puis remplace entierement la
    table (WRITE_TRUNCATE — cette table reflete l'etat actuel, pas un
    historique)."""
    print("🔗 RAFRAICHISSEMENT MAPPING URL → POST_ID...")
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
            return 0

    if not lignes:
        print("  ⚠️ Aucun post recupere, mapping non mis a jour")
        return 0

    try:
        client_bq.query(f"""
        DELETE FROM `{PROJECT_ID}.02_cleaned.wp_url_mapping` WHERE TRUE
        """).result()
        client_bq.insert_rows_json(f"{PROJECT_ID}.02_cleaned.wp_url_mapping", lignes)
        print(f"  ✅ {len(lignes)} correspondances URL → post_id mises a jour")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def rafraichir_wp_url_mapping" in contenu:
    print("⏭️  PATCH (mapping URL post_id) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (mapping URL post_id) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_fonction, 1)
    print("✅ PATCH (mapping URL post_id) : fonction ajoutee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
