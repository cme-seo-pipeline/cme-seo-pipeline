FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = """            df_merge['nb_articles'] = df_merge['nb_articles'].fillna(0)
            df_merge = df_merge.sort_values(
                by=['nb_articles', 'derniere_pub'],
                ascending=[True, True]
            )"""

nouveau = """            df_merge['nb_articles'] = df_merge['nb_articles'].fillna(0)
            # Exclut les sous-silos deja pris via SEO opportunities pour ce
            # meme silo dans ce run : sans ca, le repli anciennete pouvait
            # re-choisir le meme sous-silo qu'un sujet SEO deja selectionne,
            # recreant la collision que le suffixe d'unicite est cense eviter.
            df_merge = df_merge[~df_merge['sous_silo'].isin(sous_silos_deja_vus)]
            df_merge = df_merge.sort_values(
                by=['nb_articles', 'derniere_pub'],
                ascending=[True, True]
            )"""

if "Exclut les sous-silos deja pris via SEO" in contenu:
    print("⏭️  PATCH (exclusion fallback) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (exclusion fallback) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (exclusion fallback) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
