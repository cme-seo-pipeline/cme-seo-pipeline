FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    lignes = f.readlines()

# ============================================================
# PATCH 1 — Ajout de FACEBOOK_CONFIG juste apres SEARCH_API_KEY
# ============================================================
ancre1 = 'SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")\n'
bloc_facebook_config = (
    'FACEBOOK_CONFIG = {\n'
    '    "page_id": os.environ.get("FACEBOOK_PAGE_ID", ""),\n'
    '    "access_token": os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", ""),\n'
    '}\n'
)

if "FACEBOOK_CONFIG = {" in "".join(lignes):
    print("⏭️  PATCH 1 (FACEBOOK_CONFIG) : deja presente, ignore")
else:
    indices = [i for i, l in enumerate(lignes) if l == ancre1]
    if len(indices) != 1:
        print(f"❌ PATCH 1 : ancre trouvee {len(indices)} fois (attendu 1), aucune modification")
    else:
        i = indices[0]
        lignes = lignes[:i+1] + [bloc_facebook_config] + lignes[i+1:]
        print("✅ PATCH 1 (FACEBOOK_CONFIG) : ajoutee")

# ============================================================
# PATCH 3 — Appel publier_tous_facebook() juste apres generer_featured_images()
# ============================================================
contenu_actuel = "".join(lignes)
if "publier_tous_facebook(df_publications" in contenu_actuel and "def publier_tous_facebook(" in contenu_actuel:
    # Ne pas ajouter l'appel si deja fait, mais on verifie separement plus bas
    pass

ancre3 = "    generer_featured_images(df_publications, client_bq, CONFIG, OPENAI_CONFIG, WP_CONFIG)\n"
appel_facebook = (
    "    # ── PUBLICATION FACEBOOK ────────────────────────────────\n"
    "    publier_tous_facebook(df_publications, client_bq, CONFIG, FACEBOOK_CONFIG)\n"
)

if "publier_tous_facebook(df_publications, client_bq, CONFIG, FACEBOOK_CONFIG)" in contenu_actuel:
    print("⏭️  PATCH 3 (appel run_pipeline) : deja present, ignore")
else:
    indices = [i for i, l in enumerate(lignes) if l == ancre3]
    if len(indices) != 1:
        print(f"❌ PATCH 3 : ancre trouvee {len(indices)} fois (attendu 1), aucune modification")
    else:
        i = indices[0]
        lignes = lignes[:i+1] + [appel_facebook] + lignes[i+1:]
        print("✅ PATCH 3 (appel run_pipeline) : integre")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.writelines(lignes)

print("\n📝 Fichier sauvegarde :", FICHIER)
