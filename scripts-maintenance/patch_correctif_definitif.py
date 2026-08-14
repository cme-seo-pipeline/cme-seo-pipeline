FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH A — Annuler le mauvais groupby (mot_cle_principal peu fiable)
# ============================================================
ancien_a = """def generer_tous_briefs(df_final, client_bq, config):
    all_briefs_finaux = {}
    print("✍️ GÉNÉRATION DES BRIEFS...")
    # Groupe aussi par mot_cle_principal : indispensable depuis
    # l'industrialisation (plusieurs articles/jour par silo), qui peut
    # legitimement selectionner plusieurs sujets DISTINCTS partageant le
    # meme sous-silo. Sans cette 3e cle, ils fusionnaient en un seul
    # groupe (donc un seul brief genere au lieu de plusieurs).
    for (silo_name, sous_silo_name, mot_cle_val), df_silo in df_final.groupby(
        ['Silo', 'Sous-Silo', 'mot_cle_principal']
    ):"""

nouveau_a = """def generer_tous_briefs(df_final, client_bq, config):
    all_briefs_finaux = {}
    print("✍️ GÉNÉRATION DES BRIEFS...")
    # Groupby standard par (Silo, Sous-Silo). L'unicite entre plusieurs
    # articles industrialises partageant le meme sous-silo est desormais
    # garantie EN AMONT, a la selection (suffixe ' (2)', ' (3)' ajoute
    # dans selectionner_silos_a_traiter) — pas ici via mot_cle_principal,
    # qui est extrait independamment par concurrent scrape et n'est pas
    # stable pour un meme sujet (cause d'une sur-fragmentation constatee).
    for (silo_name, sous_silo_name), df_silo in df_final.groupby(['Silo', 'Sous-Silo']):"""

if "Groupby standard par (Silo, Sous-Silo)" in contenu:
    print("⏭️  PATCH A (annulation groupby) : deja present, ignore")
elif ancien_a not in contenu:
    print("❌ PATCH A (annulation groupby) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien_a, nouveau_a, 1)
    print("✅ PATCH A (annulation groupby) : revenu a (Silo, Sous-Silo)")

# ============================================================
# PATCH B — Annuler la cle a 3 segments
# ============================================================
ancien_b = '''            all_briefs_finaux[f"{silo_name}||{sous_silo_name}||{mot_cle_val}"] = brief'''
nouveau_b = '''            all_briefs_finaux[f"{silo_name}||{sous_silo_name}"] = brief'''

if ancien_b not in contenu:
    print("⏭️  PATCH B (cle 2 segments) : deja applique ou ancre non trouvee")
else:
    contenu = contenu.replace(ancien_b, nouveau_b, 1)
    print("✅ PATCH B (cle 2 segments) : revenu au format d'origine")

# ============================================================
# PATCH C — Suffixe d'unicite a la source (selection)
# ============================================================
ancien_c = """        silo_safe = silo_du_jour.replace("'", "''")
        nb_trouves = 0
        try:
            df_opp = client_bq.query(f\"\"\"
            SELECT
                '{silo_du_jour}' AS silo,
                COALESCE(NULLIF(sous_silo, ''), 'general') AS sous_silo,
                query AS mot_cle,
                score_opportunite,
                ROUND(position, 1) AS position,
                impressions,
                jours_depuis_pub
            FROM `{PROJECT_ID}.03_final.seo_opportunities`
            WHERE silo = '{silo_safe}'
              AND jours_depuis_pub >= 30
              AND sous_silo IS NOT NULL
            ORDER BY score_opportunite DESC
            LIMIT {ARTICLES_PAR_SILO}
            \"\"\").to_dataframe()
            for idx in range(len(df_opp)):
                df_ligne = df_opp.iloc[[idx]].copy()
                df_ligne['priorite'] = 1
                row = df_ligne.iloc[0]
                # 'general' est un placeholder technique — jamais un vrai sous-silo
                # WordPress. On le remplace par le sous-silo strategique le moins
                # recemment publie, en gardant le mot-cle GSC reel pour le contenu.
                if row['sous_silo'] == 'general':
                    try:
                        df_strat_fix = client_bq.query(f\"\"\"
                        SELECT s.sous_silo, MAX(h.date_publication) AS derniere_pub
                        FROM `{PROJECT_ID}.{DATASET_ID}.sous_silos_strategiques` s
                        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.historique_publications` h
                          ON h.silo = '{silo_safe}' AND h.sous_silo_strategique = s.sous_silo
                        WHERE s.silo = '{silo_safe}'
                        GROUP BY s.sous_silo
                        ORDER BY derniere_pub ASC NULLS FIRST
                        LIMIT 1
                        \"\"\").to_dataframe()
                        if not df_strat_fix.empty:
                            vrai_sous_silo = df_strat_fix.iloc[0]['sous_silo']
                            print(f"   🔀 'general' remplace par sous-silo reel : {vrai_sous_silo}")
                            df_ligne.loc[df_ligne.index[0], 'sous_silo'] = vrai_sous_silo
                            row = df_ligne.iloc[0]
                    except Exception as e_gen:
                        print(f"   ⚠️ Impossible de remplacer 'general' : {e_gen}")
                print(f"   ✅ {row['silo']} | {row['sous_silo']} — "
                      f"'{row['mot_cle']}' (pos {row['position']}, "
                      f"score {row['score_opportunite']:.0f})")
                resultats.append(df_ligne[['silo', 'sous_silo', 'priorite', 'mot_cle']])
                nb_trouves += 1"""

nouveau_c = """        silo_safe = silo_du_jour.replace("'", "''")
        nb_trouves = 0
        sous_silos_deja_vus = []
        try:
            df_opp = client_bq.query(f\"\"\"
            SELECT
                '{silo_du_jour}' AS silo,
                COALESCE(NULLIF(sous_silo, ''), 'general') AS sous_silo,
                query AS mot_cle,
                score_opportunite,
                ROUND(position, 1) AS position,
                impressions,
                jours_depuis_pub
            FROM `{PROJECT_ID}.03_final.seo_opportunities`
            WHERE silo = '{silo_safe}'
              AND jours_depuis_pub >= 30
              AND sous_silo IS NOT NULL
            ORDER BY score_opportunite DESC
            LIMIT {ARTICLES_PAR_SILO}
            \"\"\").to_dataframe()
            for idx in range(len(df_opp)):
                df_ligne = df_opp.iloc[[idx]].copy()
                df_ligne['priorite'] = 1
                row = df_ligne.iloc[0]
                # 'general' est un placeholder technique — jamais un vrai sous-silo
                # WordPress. On le remplace par le sous-silo strategique le moins
                # recemment publie, en gardant le mot-cle GSC reel pour le contenu.
                if row['sous_silo'] == 'general':
                    try:
                        df_strat_fix = client_bq.query(f\"\"\"
                        SELECT s.sous_silo, MAX(h.date_publication) AS derniere_pub
                        FROM `{PROJECT_ID}.{DATASET_ID}.sous_silos_strategiques` s
                        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.historique_publications` h
                          ON h.silo = '{silo_safe}' AND h.sous_silo_strategique = s.sous_silo
                        WHERE s.silo = '{silo_safe}'
                        GROUP BY s.sous_silo
                        ORDER BY derniere_pub ASC NULLS FIRST
                        LIMIT 1
                        \"\"\").to_dataframe()
                        if not df_strat_fix.empty:
                            vrai_sous_silo = df_strat_fix.iloc[0]['sous_silo']
                            print(f"   🔀 'general' remplace par sous-silo reel : {vrai_sous_silo}")
                            df_ligne.loc[df_ligne.index[0], 'sous_silo'] = vrai_sous_silo
                            row = df_ligne.iloc[0]
                    except Exception as e_gen:
                        print(f"   ⚠️ Impossible de remplacer 'general' : {e_gen}")
                # Anti-collision : si ce sous-silo a deja ete pris pour un
                # AUTRE sujet de ce meme silo dans ce run, on le rend unique
                # avec un suffixe ' (2)', ' (3)'... Sans ca, generer_tous_briefs
                # (qui groupe par Silo+Sous-Silo) fusionnerait ces sujets
                # pourtant distincts en un seul brief. Le suffixe est retire
                # juste avant la vraie categorisation WordPress/BigQuery,
                # dans rediger_et_publier.
                sous_silo_base = row['sous_silo']
                if sous_silo_base in sous_silos_deja_vus:
                    occurrence = sous_silos_deja_vus.count(sous_silo_base) + 1
                    sous_silo_unique = f"{sous_silo_base} ({occurrence})"
                    df_ligne.loc[df_ligne.index[0], 'sous_silo'] = sous_silo_unique
                    row = df_ligne.iloc[0]
                sous_silos_deja_vus.append(sous_silo_base)
                print(f"   ✅ {row['silo']} | {row['sous_silo']} — "
                      f"'{row['mot_cle']}' (pos {row['position']}, "
                      f"score {row['score_opportunite']:.0f})")
                resultats.append(df_ligne[['silo', 'sous_silo', 'priorite', 'mot_cle']])
                nb_trouves += 1"""

if "Anti-collision" in contenu:
    print("⏭️  PATCH C (suffixe unicite) : deja present, ignore")
elif ancien_c not in contenu:
    print("❌ PATCH C (suffixe unicite) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien_c, nouveau_c, 1)
    print("✅ PATCH C (suffixe unicite) : ajoute a la selection")

# ============================================================
# PATCH D — Retirer le suffixe avant la vraie categorisation
# ============================================================
ancien_d = """        try:
            if sous_silo_override:
                sous_silo_val = sous_silo_override
            else:
                sous_silo_val = silos_df[silos_df['silo'] == silo_name]['sous_silo'].iloc[0]
                if pd.isna(sous_silo_val): sous_silo_val = ''
        except:
            sous_silo_val = sous_silo_override or ''
        resultat = publier_article("""

nouveau_d = """        try:
            if sous_silo_override:
                sous_silo_val = sous_silo_override
            else:
                sous_silo_val = silos_df[silos_df['silo'] == silo_name]['sous_silo'].iloc[0]
                if pd.isna(sous_silo_val): sous_silo_val = ''
        except:
            sous_silo_val = sous_silo_override or ''
        # Retire le suffixe technique ' (2)', ' (3)'... ajoute a la selection
        # pour distinguer plusieurs sujets industrialises partageant le meme
        # sous-silo. La vraie categorisation WordPress/BigQuery doit garder
        # le nom de sous-silo original.
        sous_silo_val = re.sub(r' \\(\\d+\\)$', '', sous_silo_val)
        resultat = publier_article("""

if "Retire le suffixe technique" in contenu:
    print("⏭️  PATCH D (retrait suffixe) : deja present, ignore")
elif ancien_d not in contenu:
    print("❌ PATCH D (retrait suffixe) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien_d, nouveau_d, 1)
    print("✅ PATCH D (retrait suffixe) : ajoute avant publication")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
