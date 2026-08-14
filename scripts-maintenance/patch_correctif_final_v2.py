FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH C1 — Initialiser le tracker de sous-silos vus
# ============================================================
ancien_c1 = """        nb_trouves = 0

        try:"""

nouveau_c1 = """        nb_trouves = 0
        sous_silos_deja_vus = []

        try:"""

if "sous_silos_deja_vus = []" in contenu:
    print("⏭️  PATCH C1 (init tracker) : deja present, ignore")
elif ancien_c1 not in contenu:
    print("❌ PATCH C1 (init tracker) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien_c1, nouveau_c1, 1)
    print("✅ PATCH C1 (init tracker) : ajoute")

# ============================================================
# PATCH C2 — Logique anti-collision (suffixe d'unicite)
# ============================================================
ancien_c2 = """                    except Exception as e_gen:
                        print(f"   ⚠️ Impossible de remplacer 'general' : {e_gen}")

                print(f"   ✅ {row['silo']} | {row['sous_silo']} — \""""

nouveau_c2 = """                    except Exception as e_gen:
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

                print(f"   ✅ {row['silo']} | {row['sous_silo']} — \""""

if "Anti-collision" in contenu:
    print("⏭️  PATCH C2 (suffixe unicite) : deja present, ignore")
elif ancien_c2 not in contenu:
    print("❌ PATCH C2 (suffixe unicite) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien_c2, nouveau_c2, 1)
    print("✅ PATCH C2 (suffixe unicite) : ajoute")

# ============================================================
# PATCH D — Retirer le suffixe avant publication
# ============================================================
ancien_d = """        except:
            sous_silo_val = sous_silo_override or ''

        resultat = publier_article("""

nouveau_d = """        except:
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
    print("✅ PATCH D (retrait suffixe) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
