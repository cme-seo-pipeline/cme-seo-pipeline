FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Flag de config
# ============================================================
ancien1 = '''    "nb_articles_par_run": 9,  # 3 silos industrialises x 3 articles, 7j/7
    "fenetre_anti_doublon_jours": 90,
}'''

nouveau1 = '''    "nb_articles_par_run": 9,  # 3 silos industrialises x 3 articles, 7j/7
    "fenetre_anti_doublon_jours": 90,
    # Desactive temporairement le temps que la verification du compte
    # developpeur Meta aboutisse (app bloquee cote Meta depuis debut aout).
    # Allege aussi la duree du run, qui compte desormais reellement vu que
    # /run-sync est plafonne a 30 min cote Cloud Scheduler.
    "FACEBOOK_INSTAGRAM_ACTIF": False,
}'''

if '"FACEBOOK_INSTAGRAM_ACTIF"' in contenu:
    print("⏭️  PATCH 1 (flag config) : deja present, ignore")
elif ancien1 not in contenu:
    print("❌ PATCH 1 (flag config) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("✅ PATCH 1 (flag config) : FACEBOOK_INSTAGRAM_ACTIF=False ajoute")

# ============================================================
# PATCH 2 — Appels conditionnes par le flag
# ============================================================
ancien2 = '''    publier_tous_facebook(df_publications, client_bq, CONFIG, FACEBOOK_CONFIG)
    publier_tous_instagram(df_publications, client_bq, CONFIG, INSTAGRAM_CONFIG)
    notifier_nouveaux_articles(df_publications, CONFIG)'''

nouveau2 = '''    if CONFIG.get("FACEBOOK_INSTAGRAM_ACTIF", True):
        publier_tous_facebook(df_publications, client_bq, CONFIG, FACEBOOK_CONFIG)
        publier_tous_instagram(df_publications, client_bq, CONFIG, INSTAGRAM_CONFIG)
    else:
        print("⏭️  Facebook/Instagram desactives temporairement (FACEBOOK_INSTAGRAM_ACTIF=False)")
    notifier_nouveaux_articles(df_publications, CONFIG)'''

if 'FACEBOOK_INSTAGRAM_ACTIF", True' in contenu:
    print("⏭️  PATCH 2 (appels conditionnes) : deja present, ignore")
elif ancien2 not in contenu:
    print("❌ PATCH 2 (appels conditionnes) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (appels conditionnes) : Facebook/Instagram desactives")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
