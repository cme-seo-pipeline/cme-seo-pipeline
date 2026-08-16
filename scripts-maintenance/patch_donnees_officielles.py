FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Nouvelle fonction + signature enrichie
# ============================================================
ancien1 = """def rediger_article(brief, config, articles_silo=None):
    annee_courante = datetime.now().year"""

nouveau1 = """def recuperer_donnees_officielles(silo, sous_silo, client_bq):
    \"\"\"Recupere les dernieres valeurs officielles connues (PRVG, TRVE,
    aides...) pour ce silo/sous-silo via la table de mapping du chantier
    veille reglementaire, pour eviter que l'IA n'invente des chiffres.
    Retourne une chaine prete a injecter dans le prompt, vide si rien
    ne correspond (fonctionne meme si les tables n'existent pas encore).\"\"\"
    try:
        silo_safe = silo.replace("'", "''")
        sous_silo_safe = (sous_silo or "").replace("'", "''")
        df = client_bq.query(f\"\"\"
        SELECT DISTINCT i.indicateur, i.valeur, i.unite, i.date_debut_validite
        FROM `{PROJECT_ID}.{DATASET_ID}.mapping_indicateur_sous_silo` m
        JOIN `{PROJECT_ID}.{DATASET_ID}.indicateurs_reglementaires` i
            ON i.indicateur = m.indicateur
        WHERE m.silo = '{silo_safe}'
          AND m.sous_silo_strategique = '{sous_silo_safe}'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY i.indicateur ORDER BY i.date_verification DESC) = 1
        \"\"\").to_dataframe()
        if df.empty:
            return ""
        return "\\n".join([
            f"- {row['indicateur']} : {row['valeur']} {row['unite']} (en vigueur depuis le {row['date_debut_validite']})"
            for _, row in df.iterrows()
        ])
    except Exception:
        return ""


def rediger_article(brief, config, articles_silo=None, client_bq=None):
    annee_courante = datetime.now().year"""

if "def recuperer_donnees_officielles" in contenu:
    print("⏭️  PATCH 1 (fonction + signature) : deja present, ignore")
elif ancien1 not in contenu:
    print("❌ PATCH 1 (fonction + signature) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("✅ PATCH 1 (fonction + signature) : ajoutee")

# ============================================================
# PATCH 2 — Construction du bloc donnees officielles
# ============================================================
ancien2 = """    maillage_str = ""
    if articles_silo:
        liens = "\\n".join([f"- {a.get('titre')} → {a.get('url')}" for a in articles_silo])
        maillage_str = f"\\nMAILLAGE INTERNE :\\n{liens}\\n"
    prompt = f\"\"\"Tu es un rédacteur SEO expert spécialisé dans l'énergie en France."""

nouveau2 = """    maillage_str = ""
    if articles_silo:
        liens = "\\n".join([f"- {a.get('titre')} → {a.get('url')}" for a in articles_silo])
        maillage_str = f"\\nMAILLAGE INTERNE :\\n{liens}\\n"
    donnees_officielles_str = ""
    if client_bq is not None:
        donnees = recuperer_donnees_officielles(brief.get('silo', ''), brief.get('sous_silo', ''), client_bq)
        if donnees:
            donnees_officielles_str = f"\\nDONNÉES OFFICIELLES ACTUELLES (source : CRE/ANAH, verifiees) :\\n{donnees}\\n"
    prompt = f\"\"\"Tu es un rédacteur SEO expert spécialisé dans l'énergie en France."""

if "donnees_officielles_str = \"\"" in contenu:
    print("⏭️  PATCH 2 (construction bloc) : deja present, ignore")
elif ancien2 not in contenu:
    print("❌ PATCH 2 (construction bloc) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (construction bloc) : ajoutee")

# ============================================================
# PATCH 3 — Injection dans le corps du prompt
# ============================================================
ancien3 = """{faq_str}
{maillage_str}
RÈGLES :"""

nouveau3 = """{faq_str}
{maillage_str}
{donnees_officielles_str}
RÈGLES :"""

if "{donnees_officielles_str}\nRÈGLES :" in contenu:
    print("⏭️  PATCH 3 (injection prompt) : deja present, ignore")
elif ancien3 not in contenu:
    print("❌ PATCH 3 (injection prompt) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien3, nouveau3, 1)
    print("✅ PATCH 3 (injection prompt) : ajoutee")

# ============================================================
# PATCH 4 — Nouvelle regle anti-invention
# ============================================================
ancien4 = """4. Apostrophes : uniquement l'apostrophe droite simple (') — jamais d'entité HTML (&rsquo; interdit)
5. Commence DIRECTEMENT par <h1>...</h1>
6. INTERDIT : ```html, <!DOCTYPE>, <html>, <head>, <body>\"\"\""""

nouveau4 = """4. Apostrophes : uniquement l'apostrophe droite simple (') — jamais d'entité HTML (&rsquo; interdit)
5. Chiffres précis (prix, taux, tarifs) : utilise EXCLUSIVEMENT les valeurs de la section DONNÉES OFFICIELLES ACTUELLES ci-dessus si elle est présente. INTERDIT d'inventer un prix, un taux ou une offre commerciale attribuée à une marque réelle (EDF, Engie, TotalEnergies...). Si aucune donnée officielle n'est fournie pour un point précis, reste général (ex: "les tarifs varient selon les fournisseurs") plutôt que d'inventer un chiffre ou un nom de marque avec un prix associé.
6. Commence DIRECTEMENT par <h1>...</h1>
7. INTERDIT : ```html, <!DOCTYPE>, <html>, <head>, <body>\"\"\""""

if "Chiffres précis (prix, taux, tarifs)" in contenu:
    print("⏭️  PATCH 4 (regle anti-invention) : deja present, ignore")
elif ancien4 not in contenu:
    print("❌ PATCH 4 (regle anti-invention) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien4, nouveau4, 1)
    print("✅ PATCH 4 (regle anti-invention) : ajoutee")

# ============================================================
# PATCH 5 — Mise a jour du site d'appel
# ============================================================
ancien5 = """        contenu_html, erreur = rediger_article(brief, config, articles_silo)"""
nouveau5 = """        contenu_html, erreur = rediger_article(brief, config, articles_silo, client_bq)"""

if ancien5 not in contenu and "rediger_article(brief, config, articles_silo, client_bq)" in contenu:
    print("⏭️  PATCH 5 (site d'appel) : deja present, ignore")
elif ancien5 not in contenu:
    print("❌ PATCH 5 (site d'appel) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien5, nouveau5, 1)
    print("✅ PATCH 5 (site d'appel) : client_bq transmis")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
