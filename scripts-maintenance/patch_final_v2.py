FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 2+role — construction du bloc + role cible 3 secteurs
# ============================================================
ancien2 = '''    maillage_str = ""
    if articles_silo:
        liens = "\\n".join([f"- {a.get('titre')} → {a.get('url')}" for a in articles_silo])
        maillage_str = f"\\nMAILLAGE INTERNE :\\n{liens}\\n"

    prompt = f"""Tu es un rédacteur SEO expert spécialisé dans l'énergie en France.'''

nouveau2 = '''    maillage_str = ""
    if articles_silo:
        liens = "\\n".join([f"- {a.get('titre')} → {a.get('url')}" for a in articles_silo])
        maillage_str = f"\\nMAILLAGE INTERNE :\\n{liens}\\n"
    donnees_officielles_str = ""
    if client_bq is not None:
        donnees = recuperer_donnees_officielles(brief.get('silo', ''), brief.get('sous_silo', ''), client_bq)
        if donnees:
            donnees_officielles_str = f"\\nDONNÉES OFFICIELLES ACTUELLES (source : CRE/ANAH, verifiees) :\\n{donnees}\\n"

    prompt = f"""Tu es un rédacteur SEO expert et conseiller commercial, spécialisé exclusivement dans 3 secteurs : l'électricité, le gaz et les aides à la rénovation énergétique en France.'''

if "donnees_officielles_str = \"\"" in contenu:
    print("⏭️  PATCH 2+role : deja present, ignore")
elif ancien2 not in contenu:
    print("❌ PATCH 2+role : ancre TOUJOURS non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2+role : bloc donnees + role 3 secteurs ajoutes")

# ============================================================
# PATCH 3 — injection dans le corps du prompt
# ============================================================
ancien3 = '''FAQ :
{faq_str}

{maillage_str}

RÈGLES :'''

nouveau3 = '''FAQ :
{faq_str}

{maillage_str}
{donnees_officielles_str}

RÈGLES :'''

if "{donnees_officielles_str}" in contenu and contenu.count("{donnees_officielles_str}") >= 2:
    print("⏭️  PATCH 3 (injection prompt) : deja present, ignore")
elif ancien3 not in contenu:
    print("❌ PATCH 3 (injection prompt) : ancre TOUJOURS non trouvee")
else:
    contenu = contenu.replace(ancien3, nouveau3, 1)
    print("✅ PATCH 3 (injection prompt) : ajoutee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
