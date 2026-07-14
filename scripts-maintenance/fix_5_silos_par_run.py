with open('pipeline.py', 'r') as f:
    content = f.read()

old_fn_start = "def selectionner_silos_a_traiter(client_bq, config):"
old_fn_marker_end = "        df_strategie = client_bq.query(f\"\"\"\n        SELECT silo, sous_silo, priorite\n        FROM `{PROJECT_ID}.{DATASET_ID}.sous_silos_strategiques`\n        WHERE silo = '{silo_safe}'\n        ORDER BY priorite ASC\n        \"\"\").to_dataframe()"

idx_start = content.find(old_fn_start)
idx_end = content.find(old_fn_marker_end)

if idx_start == -1 or idx_end == -1:
    print(f"❌ Bornes non trouvées (start={idx_start}, end={idx_end})")
else:
    old_block = content[idx_start:idx_end]
    print(f"Bloc à remplacer : {len(old_block)} caractères")

    new_fn = '''def selectionner_silos_a_traiter(client_bq, config):
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
                print(f"   ✅ {row['silo']} | {row['sous_silo']} — "
                      f"'{row['mot_cle']}' (pos {row['position']}, "
                      f"score {row['score_opportunite']:.0f})")
                resultats.append(df_opp[['silo', 'sous_silo', 'priorite', 'mot_cle']])
                continue
            else:
                print(f"   ⚠️ {silo_du_jour} : seo_opportunities vide — fallback anciennete")
        except Exception as e_opp:
            print(f"   ⚠️ {silo_du_jour} : seo_opportunities indisponible ({e_opp}) — fallback")

        # ── FALLBACK par silo : ancienneté ──────────────────────
        df_strategie = client_bq.query(f"""
        SELECT silo, sous_silo, priorite
        FROM `{PROJECT_ID}.{DATASET_ID}.sous_silos_strategiques`
        WHERE silo = '{silo_safe}'
        ORDER BY priorite ASC
        """).to_dataframe()'''

    content = content[:idx_start] + new_fn + content[idx_end + len(old_fn_marker_end):]
    print("✅ Fonction remplacée")

    with open('pipeline.py', 'w') as f:
        f.write(content)
