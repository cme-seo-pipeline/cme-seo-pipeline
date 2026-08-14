FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — generer_tous_briefs : groupby + cle enrichis
# ============================================================
ancien1 = """def generer_tous_briefs(df_final, client_bq, config):
    all_briefs_finaux = {}
    print("✍️ GÉNÉRATION DES BRIEFS...")
    for (silo_name, sous_silo_name), df_silo in df_final.groupby(['Silo', 'Sous-Silo']):
        df_silo_clean = df_silo[df_silo['volume_mots'] > 0]
        if df_silo_clean.empty:
            continue
        contexte = preparer_contexte_silo(df_silo_clean, silo_name)
        titres_existants = recuperer_titres_existants(silo_name, client_bq)
        brief, erreur = generer_brief_silo(contexte, config, titres_existants)
        if erreur:
            print(f"  ❌ {silo_name} : {erreur}")
        else:
            all_briefs_finaux[f"{silo_name}||{sous_silo_name}"] = brief
            print(f"  ✅ {silo_name} | {brief.get('sous_silo')} — {brief.get('titre_seo')}")
    return all_briefs_finaux"""

nouveau1 = """def generer_tous_briefs(df_final, client_bq, config):
    all_briefs_finaux = {}
    print("✍️ GÉNÉRATION DES BRIEFS...")
    # Groupe aussi par mot_cle_principal : indispensable depuis
    # l'industrialisation (plusieurs articles/jour par silo), qui peut
    # legitimement selectionner plusieurs sujets DISTINCTS partageant le
    # meme sous-silo. Sans cette 3e cle, ils fusionnaient en un seul
    # groupe (donc un seul brief genere au lieu de plusieurs).
    for (silo_name, sous_silo_name, mot_cle_val), df_silo in df_final.groupby(
        ['Silo', 'Sous-Silo', 'mot_cle_principal']
    ):
        df_silo_clean = df_silo[df_silo['volume_mots'] > 0]
        if df_silo_clean.empty:
            continue
        contexte = preparer_contexte_silo(df_silo_clean, silo_name)
        titres_existants = recuperer_titres_existants(silo_name, client_bq)
        brief, erreur = generer_brief_silo(contexte, config, titres_existants)
        if erreur:
            print(f"  ❌ {silo_name} : {erreur}")
        else:
            # 3e segment (mot-cle) ajoute pour garantir l'unicite de la
            # cle meme quand plusieurs sujets partagent le meme sous-silo.
            all_briefs_finaux[f"{silo_name}||{sous_silo_name}||{mot_cle_val}"] = brief
            print(f"  ✅ {silo_name} | {brief.get('sous_silo')} — {brief.get('titre_seo')}")
    return all_briefs_finaux"""

if "Groupe aussi par mot_cle_principal" in contenu:
    print("⏭️  PATCH 1 (generer_tous_briefs) : deja present, ignore")
elif ancien1 not in contenu:
    print("❌ PATCH 1 (generer_tous_briefs) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("✅ PATCH 1 (generer_tous_briefs) : groupby + cle corriges")

# ============================================================
# PATCH 2 — exporter_bigquery : split sans limite
# ============================================================
ancien2 = """    rows = []
    for _cle, brief in all_briefs_finaux.items():
        parts = _cle.split('||', 1)
        silo_name = parts[0]
        sous_silo_override = parts[1] if len(parts) > 1 else ''"""

nouveau2 = """    rows = []
    for _cle, brief in all_briefs_finaux.items():
        # split('||') sans limite : la cle contient maintenant 3 segments
        # (silo||sous_silo||mot_cle) depuis le correctif anti-collision.
        # parts[2:] (le mot-cle) est ignore ici, seul silo/sous_silo compte.
        parts = _cle.split('||')
        silo_name = parts[0]
        sous_silo_override = parts[1] if len(parts) > 1 else ''"""

if ancien2 not in contenu:
    print("⏭️  PATCH 2 (exporter_bigquery) : deja applique ou ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (exporter_bigquery) : split('||') corrige")

# ============================================================
# PATCH 3 — rediger_et_publier : split sans limite
# ============================================================
ancien3 = """    for _cle, brief in all_briefs_finaux.items():
        parts = _cle.split('||', 1)
        silo_name = parts[0]
        sous_silo_override = parts[1] if len(parts) > 1 else ''
        print(f"\\n{'='*55}")"""

nouveau3 = """    for _cle, brief in all_briefs_finaux.items():
        # split('||') sans limite : voir PATCH 1/2, meme raison.
        parts = _cle.split('||')
        silo_name = parts[0]
        sous_silo_override = parts[1] if len(parts) > 1 else ''
        print(f"\\n{'='*55}")"""

if ancien3 not in contenu:
    print("⏭️  PATCH 3 (rediger_et_publier) : deja applique ou ancre non trouvee")
else:
    contenu = contenu.replace(ancien3, nouveau3, 1)
    print("✅ PATCH 3 (rediger_et_publier) : split('||') corrige")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
