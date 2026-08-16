FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = """        if resultat['success']:
            print(f"  ✅ ACTUALITE PUBLIEE : {resultat['url']}")
            nb_mots = len(re.sub(r'<[^>]+>', '', contenu_html).split())"""

nouveau = """        if resultat['success']:
            print(f"  ✅ ACTUALITE PUBLIEE : {resultat['url']}")
            try:
                client_bq.query(f\"\"\"
                UPDATE `{PROJECT_ID}.{DATASET_ID}.historique_publications`
                SET type_publication = 'actualite'
                WHERE post_id = {resultat['post_id']}
                \"\"\").result()
            except Exception as e:
                print(f"  ⚠️ Erreur marquage type_publication : {e}")
            nb_mots = len(re.sub(r'<[^>]+>', '', contenu_html).split())"""

if "SET type_publication = 'actualite'" in contenu:
    print("⏭️  PATCH (marquage type_publication) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (marquage type_publication) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (marquage type_publication) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
