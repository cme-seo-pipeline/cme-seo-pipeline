FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Nouvelle fonction utilitaire : filet de securite
# ============================================================
ancien1 = '''def generer_brief_silo(contexte, config, titres_existants=None):'''

nouveau1 = '''def nettoyer_texte_ia(texte, annee_courante=None):
    """Filet de securite applique en plus des instructions de prompt (qui
    seules ne suffisent pas toujours) :
    - Corrige les entites HTML d'apostrophe mal rendues (&rsquo; etc.) en
      apostrophe droite simple.
    - Remplace toute annee obsolete (2020 a annee_courante-1, frequemment
      recopiee du contexte concurrent scrape) par l'annee en cours.
    """
    if not texte:
        return texte
    texte = re.sub(r'&[lr]squo;?', "'", texte)
    texte = re.sub(r'&#821[67];?', "'", texte)
    if annee_courante:
        for annee in range(2020, annee_courante):
            texte = re.sub(rf'\\b{annee}\\b', str(annee_courante), texte)
    return texte


def generer_brief_silo(contexte, config, titres_existants=None):'''

if "def nettoyer_texte_ia" in contenu:
    print("⏭️  PATCH 1 (fonction utilitaire) : deja present, ignore")
elif ancien1 not in contenu:
    print("❌ PATCH 1 (fonction utilitaire) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("✅ PATCH 1 (fonction utilitaire) : nettoyer_texte_ia ajoutee")

# ============================================================
# PATCH 2 — generer_brief_silo : annee_courante + regles prompt
# ============================================================
ancien2 = '''    silo_propre = silo.split('. ')[-1] if '. ' in silo else silo
    slug_silo = to_slug(silo_propre)
    slug_sous_silo = to_slug(sous_silo)'''

nouveau2 = '''    silo_propre = silo.split('. ')[-1] if '. ' in silo else silo
    slug_silo = to_slug(silo_propre)
    slug_sous_silo = to_slug(sous_silo)
    annee_courante = datetime.now().year'''

if "annee_courante = datetime.now().year\n    slug_sous_silo" not in contenu and "silo_propre = silo.split" in contenu:
    if ancien2 not in contenu:
        print("❌ PATCH 2 (annee_courante brief) : ancre non trouvee")
    else:
        contenu = contenu.replace(ancien2, nouveau2, 1)
        print("✅ PATCH 2 (annee_courante brief) : ajoutee")
else:
    print("⏭️  PATCH 2 (annee_courante brief) : deja present, ignore")

ancien2b = '''  "conseil_redacteur": "conseil en 1 phrase"
}}
JSON uniquement."""'''

nouveau2b = '''  "conseil_redacteur": "conseil en 1 phrase"
}}
RÈGLES SUPPLÉMENTAIRES :
- Dates : n'utilise JAMAIS d'année dans titre_seo ou meta_description sauf {annee_courante} ou {annee_courante + 1}. INTERDIT toute année antérieure, même si le contexte concurrent scrapé en mentionne une.
- Apostrophes : utilise uniquement l'apostrophe droite simple (') — jamais d'entité HTML (&rsquo; interdit).
JSON uniquement."""'''

if "RÈGLES SUPPLÉMENTAIRES" in contenu:
    print("⏭️  PATCH 2b (regles prompt brief) : deja present, ignore")
elif ancien2b not in contenu:
    print("❌ PATCH 2b (regles prompt brief) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2b, nouveau2b, 1)
    print("✅ PATCH 2b (regles prompt brief) : ajoutees")

# ============================================================
# PATCH 3 — generer_tous_briefs : nettoyage du titre/meta apres generation
# ============================================================
ancien3 = '''        brief, erreur = generer_brief_silo(contexte, config, titres_existants)
        if erreur:
            print(f"  ❌ {silo_name} : {erreur}")
        else:'''

nouveau3 = '''        brief, erreur = generer_brief_silo(contexte, config, titres_existants)
        if erreur:
            print(f"  ❌ {silo_name} : {erreur}")
        else:
            annee_courante = datetime.now().year
            brief['titre_seo'] = nettoyer_texte_ia(brief.get('titre_seo', ''), annee_courante)
            brief['meta_description'] = nettoyer_texte_ia(brief.get('meta_description', ''), annee_courante)'''

if "brief['titre_seo'] = nettoyer_texte_ia" in contenu:
    print("⏭️  PATCH 3 (nettoyage brief) : deja present, ignore")
elif ancien3 not in contenu:
    print("❌ PATCH 3 (nettoyage brief) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien3, nouveau3, 1)
    print("✅ PATCH 3 (nettoyage brief) : titre_seo/meta_description nettoyes")

# ============================================================
# PATCH 4 — rediger_article : renforcer regle dates + apostrophes
# ============================================================
ancien4 = '''RÈGLES :
1. HTML propre (h1, h2, h3, p, ul, li, strong)
2. NE PAS ajouter de CTA commercial
3. Dates : {annee_courante} ou {annee_suivante} uniquement — INTERDIT {annee_interdite}
4. Commence DIRECTEMENT par <h1>...</h1>
5. INTERDIT : ```html, <!DOCTYPE>, <html>, <head>, <body>"""'''

nouveau4 = '''RÈGLES :
1. HTML propre (h1, h2, h3, p, ul, li, strong)
2. NE PAS ajouter de CTA commercial
3. Dates : {annee_courante} ou {annee_suivante} UNIQUEMENT — INTERDIT TOUTE année antérieure ({annee_interdite}, {annee_interdite - 1}, etc.), même si le contexte concurrent scrapé en mentionne une
4. Apostrophes : uniquement l'apostrophe droite simple (') — jamais d'entité HTML (&rsquo; interdit)
5. Commence DIRECTEMENT par <h1>...</h1>
6. INTERDIT : ```html, <!DOCTYPE>, <html>, <head>, <body>"""'''

if "INTERDIT TOUTE année antérieure" in contenu:
    print("⏭️  PATCH 4 (regles prompt article) : deja present, ignore")
elif ancien4 not in contenu:
    print("❌ PATCH 4 (regles prompt article) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien4, nouveau4, 1)
    print("✅ PATCH 4 (regles prompt article) : renforcees")

# ============================================================
# PATCH 5 — rediger_article : filet de securite sur le contenu final
# ============================================================
ancien5 = '''        match = re.search(r'(<h[1-6]|<p|<article|<section)', contenu, re.IGNORECASE)
        if match:
            contenu = contenu[match.start():]
        return contenu.strip(), None'''

nouveau5 = '''        match = re.search(r'(<h[1-6]|<p|<article|<section)', contenu, re.IGNORECASE)
        if match:
            contenu = contenu[match.start():]
        contenu = nettoyer_texte_ia(contenu, annee_courante)
        return contenu.strip(), None'''

if "contenu = nettoyer_texte_ia(contenu, annee_courante)" in contenu:
    print("⏭️  PATCH 5 (nettoyage article) : deja present, ignore")
elif ancien5 not in contenu:
    print("❌ PATCH 5 (nettoyage article) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien5, nouveau5, 1)
    print("✅ PATCH 5 (nettoyage article) : contenu final nettoye")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
