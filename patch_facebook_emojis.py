FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    lignes = f.readlines()

# ============================================================
# PATCH 1 — Ajout du dictionnaire SILO_EMOJIS juste apres CTA_TOOLS
# ============================================================
ancre1 = "def generer_cta_html(silo_name, post_id=None):\n"
bloc_emojis = (
    'SILO_EMOJIS = {\n'
    '    "1. Gaz": "🔥",\n'
    '    "5. Électricité": "⚡",\n'
    '    "4. Solaire": "☀️",\n'
    '    "2. Rénovation Énergétique": "🏠",\n'
    '    "3. Aide Énergétique": "💶",\n'
    '}\n\n\n'
)

if "SILO_EMOJIS = {" in "".join(lignes):
    print("⏭️  PATCH 1 (SILO_EMOJIS) : deja present, ignore")
else:
    indices = [i for i, l in enumerate(lignes) if l == ancre1]
    if len(indices) != 1:
        print(f"❌ PATCH 1 : ancre trouvee {len(indices)} fois (attendu 1), aucune modification")
    else:
        i = indices[0]
        lignes = lignes[:i] + [bloc_emojis] + lignes[i:]
        print("✅ PATCH 1 (SILO_EMOJIS) : ajoute")

# ============================================================
# PATCH 2 — Prefixer le message Facebook avec l'emoji du silo
# ============================================================
contenu_actuel = "".join(lignes)
ancre2 = (
    "        message = extraire_introduction_article(contenu_html)\n"
    "        if not message:\n"
    "            message = generer_legende_facebook(titre_article, silo_name, config)\n"
)
nouveau2 = (
    "        message = extraire_introduction_article(contenu_html)\n"
    "        if not message:\n"
    "            message = generer_legende_facebook(titre_article, silo_name, config)\n"
    "        emoji_silo = SILO_EMOJIS.get(silo_name, \"\")\n"
    "        if emoji_silo and message:\n"
    "            message = f\"{emoji_silo} {message}\"\n"
)

if "emoji_silo = SILO_EMOJIS.get(silo_name" in contenu_actuel:
    print("⏭️  PATCH 2 (prefixe emoji) : deja present, ignore")
elif ancre2 not in contenu_actuel:
    print("❌ PATCH 2 : bloc de recherche non trouve, aucune modification")
else:
    contenu_actuel = contenu_actuel.replace(ancre2, nouveau2)
    lignes = contenu_actuel.splitlines(keepends=True)
    print("✅ PATCH 2 (prefixe emoji) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.writelines(lignes)

print("📝 Fichier sauvegarde :", FICHIER)
