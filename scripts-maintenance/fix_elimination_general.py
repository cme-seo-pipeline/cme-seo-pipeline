with open('pipeline.py', 'r') as f:
    content = f.read()

old = """            if not df_opp.empty:
                df_opp['priorite'] = 1
                row = df_opp.iloc[0]
                print(f"   ✅ {row['silo']} | {row['sous_silo']} — "
                      f"'{row['mot_cle']}' (pos {row['position']}, "
                      f"score {row['score_opportunite']:.0f})")
                resultats.append(df_opp[['silo', 'sous_silo', 'priorite', 'mot_cle']])
                trouve = True"""

new = """            if not df_opp.empty:
                df_opp['priorite'] = 1
                row = df_opp.iloc[0]

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
                            df_opp.loc[df_opp.index[0], 'sous_silo'] = vrai_sous_silo
                            row = df_opp.iloc[0]
                    except Exception as e_gen:
                        print(f"   ⚠️ Impossible de remplacer 'general' : {e_gen}")

                print(f"   ✅ {row['silo']} | {row['sous_silo']} — "
                      f"'{row['mot_cle']}' (pos {row['position']}, "
                      f"score {row['score_opportunite']:.0f})")
                resultats.append(df_opp[['silo', 'sous_silo', 'priorite', 'mot_cle']])
                trouve = True"""

if old in content:
    content = content.replace(old, new, 1)
    print("✅ Fix 'general' appliqué")
else:
    print("❌ Pattern non trouvé")

with open('pipeline.py', 'w') as f:
    f.write(content)
