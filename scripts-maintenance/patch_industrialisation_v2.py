FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien2 = '''def selectionner_silos_a_traiter(client_bq, config):
    """
    NOUVELLE LOGIQUE 7j/7 : les 5 silos sont traites a CHAQUE run,
    1 article par silo (au lieu d'1 seul silo par jour).
    Utilise seo_opportunities (GSC+GA4) en priorite, fallback anciennete.
    """
    tous_silos = [
        "5. Électricité", "1. Gaz", "4. Solaire",
        "3. Aide Énergétique", "2. Rénovation Énergétique"
    ]
    print(f"📅 Run 7j/7 → {len(tous_silos)} silos a traiter : {', '.join(tous_silos)}")
    resultats = []

    for silo_du_jour in tous_silos:
        silo_safe = silo_du_jour.replace("'", "''")
        trouve = False

        try:
            df_opp = client_bq.query(f"""
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
            LIMIT 1
            """).to_dataframe()

            if not df_opp.empty:
                df_opp['priorite'] = 1
                row = df_opp.iloc[0]

                # 'general' est un placeholder technique — jamais un vrai sous-silo
                # WordPress. On le remplace par le sous-silo strategique le moins
                # recemment publie, en gardant le mot-cle GSC reel pour le contenu.
                if row['sous_silo'] == 'general':
                    try:
                        df_strat_fix = client_bq.query(f"""
                        SELECT s.sous_silo, MAX(h.date_publication) AS derniere_pub
                        FROM `{PROJECT_ID}.{DATASET_ID}.sous_silos_strategiques` s
                        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.historique_publications` h
                          ON h.silo = '{silo_safe}' AND h.sous_silo_strategique = s.sous_silo
                        WHERE s.silo = '{silo_safe}'
                        GROUP BY s.sous_silo
                        ORDER BY derniere_pub ASC NULLS FIRST
                        LIMIT 1
                        """).to_dataframe()
                        if not df_strat_fix.empty:
                            vrai_sous_silo = df_strat_fix.iloc[0]['sous_silo']
                            print(f"   🔀 'general' remplace par sous-silo reel : {vrai_sous_silo}")
                            df_opp.loc[df_opp.index[0], 'sous_silo'] = vrai_sous_silo
                            row = df_opp.iloc[0]
                    except Exception as e_gen:
                        print(f"   ⚠️ Impossible de remplacer 'general' : {e_gen}")

                print(f"   ✅ {row['silo']} | {row['sous_silo']} — "
                      f"'{row['mot_cle']}' (pos {row['position']}, "
                      f"score {row['score_opportunite']:.0f})")
                resultats.append(df_opp[['silo', 'sous_silo', 'priorite', 'mot_cle']])
                trouve = True
            else:
                print(f"   ⚠️ {silo_du_jour} : seo_opportunities vide — fallback anciennete")
        except Exception as e_opp:
            print(f"   ⚠️ {silo_du_jour} : seo_opportunities indisponible ({e_opp}) — fallback")

        if trouve:
            continue

        # ── FALLBACK par silo : ancienneté ──────────────────────
        try:
            df_strategie = client_bq.query(f"""
            SELECT silo, sous_silo, priorite
            FROM `{PROJECT_ID}.{DATASET_ID}.sous_silos_strategiques`
            WHERE silo = '{silo_safe}'
            ORDER BY priorite ASC
            """).to_dataframe()

            if df_strategie.empty:
                print(f"   ❌ Aucun sous-silo trouve pour {silo_du_jour}")
                continue

            df_hist = client_bq.query(f"""
            SELECT sous_silo_strategique,
                   MAX(date_publication) AS derniere_pub,
                   COUNT(*) AS nb_articles
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE silo = '{silo_safe}'
              AND sous_silo_strategique IS NOT NULL
            GROUP BY sous_silo_strategique
            """).to_dataframe()

            df_merge = df_strategie.merge(
                df_hist, left_on='sous_silo',
                right_on='sous_silo_strategique', how='left'
            )
            df_merge['derniere_pub'] = df_merge['derniere_pub'].fillna(
                pd.Timestamp('2000-01-01', tz='UTC')
            )
            df_merge['nb_articles'] = df_merge['nb_articles'].fillna(0)
            df_merge = df_merge.sort_values(
                by=['nb_articles', 'derniere_pub'],
                ascending=[True, True]
            )
            df_final = df_merge.head(1)[['silo', 'sous_silo', 'priorite']].copy()
            df_final['mot_cle'] = ''
            print(f"   ✅ {silo_du_jour} | {df_final.iloc[0]['sous_silo']} (fallback anciennete)")
            resultats.append(df_final)
        except Exception as e_fb:
            print(f"   ❌ {silo_du_jour} : fallback echoue aussi ({e_fb})")

    if not resultats:
        print("❌ Aucun silo n'a pu etre traite")
        return None

    df_tous = pd.concat(resultats, ignore_index=True)
    print(f"\\n✅ TOTAL : {len(df_tous)} sujets selectionnes sur {len(tous_silos)} silos")
    return df_tous'''

nouveau2 = '''def selectionner_silos_a_traiter(client_bq, config):
    """
    LOGIQUE INDUSTRIALISEE (post-analyse performance BigQuery/GSC/GA4) :
    seuls les 3 silos les plus performants sont traites (Electricite, Gaz,
    Aide Energetique — Solaire et Renovation Energetique abandonnes faute
    de resultats), avec 3 articles chacun par run au lieu d'1 seul.
    Utilise seo_opportunities (GSC+GA4) en priorite, fallback anciennete
    pour completer les slots restants si besoin.
    """
    tous_silos = ["5. Électricité", "1. Gaz", "3. Aide Énergétique"]
    ARTICLES_PAR_SILO = 3
    print(f"📅 Run industrialise → {len(tous_silos)} silos x {ARTICLES_PAR_SILO} articles : {', '.join(tous_silos)}")
    resultats = []

    for silo_du_jour in tous_silos:
        silo_safe = silo_du_jour.replace("'", "''")
        nb_trouves = 0

        try:
            df_opp = client_bq.query(f"""
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
            """).to_dataframe()

            for idx in range(len(df_opp)):
                df_ligne = df_opp.iloc[[idx]].copy()
                df_ligne['priorite'] = 1
                row = df_ligne.iloc[0]

                # 'general' est un placeholder technique — jamais un vrai sous-silo
                # WordPress. On le remplace par le sous-silo strategique le moins
                # recemment publie, en gardant le mot-cle GSC reel pour le contenu.
                if row['sous_silo'] == 'general':
                    try:
                        df_strat_fix = client_bq.query(f"""
                        SELECT s.sous_silo, MAX(h.date_publication) AS derniere_pub
                        FROM `{PROJECT_ID}.{DATASET_ID}.sous_silos_strategiques` s
                        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.historique_publications` h
                          ON h.silo = '{silo_safe}' AND h.sous_silo_strategique = s.sous_silo
                        WHERE s.silo = '{silo_safe}'
                        GROUP BY s.sous_silo
                        ORDER BY derniere_pub ASC NULLS FIRST
                        LIMIT 1
                        """).to_dataframe()
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
                nb_trouves += 1
        except Exception as e_opp:
            print(f"   ⚠️ {silo_du_jour} : seo_opportunities indisponible ({e_opp}) — fallback")

        nb_manquants = ARTICLES_PAR_SILO - nb_trouves
        if nb_manquants <= 0:
            continue

        if nb_trouves == 0:
            print(f"   ⚠️ {silo_du_jour} : seo_opportunities vide — fallback anciennete")
        else:
            print(f"   ℹ️ {silo_du_jour} : {nb_trouves}/{ARTICLES_PAR_SILO} trouves via SEO, {nb_manquants} en fallback anciennete")

        # ── FALLBACK par silo : ancienneté (pour les slots restants) ────
        try:
            df_strategie = client_bq.query(f"""
            SELECT silo, sous_silo, priorite
            FROM `{PROJECT_ID}.{DATASET_ID}.sous_silos_strategiques`
            WHERE silo = '{silo_safe}'
            ORDER BY priorite ASC
            """).to_dataframe()

            if df_strategie.empty:
                print(f"   ❌ Aucun sous-silo trouve pour {silo_du_jour}")
                continue

            df_hist = client_bq.query(f"""
            SELECT sous_silo_strategique,
                   MAX(date_publication) AS derniere_pub,
                   COUNT(*) AS nb_articles
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE silo = '{silo_safe}'
              AND sous_silo_strategique IS NOT NULL
            GROUP BY sous_silo_strategique
            """).to_dataframe()

            df_merge = df_strategie.merge(
                df_hist, left_on='sous_silo',
                right_on='sous_silo_strategique', how='left'
            )
            df_merge['derniere_pub'] = df_merge['derniere_pub'].fillna(
                pd.Timestamp('2000-01-01', tz='UTC')
            )
            df_merge['nb_articles'] = df_merge['nb_articles'].fillna(0)
            df_merge = df_merge.sort_values(
                by=['nb_articles', 'derniere_pub'],
                ascending=[True, True]
            )
            df_final = df_merge.head(nb_manquants)[['silo', 'sous_silo', 'priorite']].copy()
            df_final['mot_cle'] = ''
            for _, r in df_final.iterrows():
                print(f"   ✅ {silo_du_jour} | {r['sous_silo']} (fallback anciennete)")
            resultats.append(df_final)
        except Exception as e_fb:
            print(f"   ❌ {silo_du_jour} : fallback echoue aussi ({e_fb})")

    if not resultats:
        print("❌ Aucun silo n'a pu etre traite")
        return None

    df_tous = pd.concat(resultats, ignore_index=True)
    print(f"\\n✅ TOTAL : {len(df_tous)} sujets selectionnes sur {len(tous_silos)} silos")
    return df_tous'''

if "LOGIQUE INDUSTRIALISEE" in contenu:
    print("⏭️  PATCH 2 (selection industrialisee) : deja present, ignore")
elif ancien2 not in contenu:
    print("❌ PATCH 2 (selection industrialisee) : ancre TOUJOURS non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (selection industrialisee) : 3 silos x 3 articles, ajoute cette fois")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
