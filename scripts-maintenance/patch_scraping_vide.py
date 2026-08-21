FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = """    df_market = pd.DataFrame(all_market_data)
    df_market = df_market.groupby(['Silo', 'Sous-Silo']).head(5)
    return df_market"""

nouveau = """    df_market = pd.DataFrame(all_market_data)
    if df_market.empty:
        print("⚠️ Aucun resultat de scraping retenu (filtrage liste noire trop restrictif ou requetes sans resultats) — DataFrame vide retournee, le run continue sans donnees concurrentes pour ce lot")
        return pd.DataFrame(columns=['Requête_Niche', 'Silo', 'Sous-Silo', 'Position', 'Concurrent', 'URL'])
    df_market = df_market.groupby(['Silo', 'Sous-Silo']).head(5)
    return df_market"""

if "Aucun resultat de scraping retenu" in contenu:
    print("⏭️  PATCH (protection scraping vide) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (protection scraping vide) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (protection scraping vide) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
