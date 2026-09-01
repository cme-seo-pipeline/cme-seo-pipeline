FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = """        r = df_m.iloc[0]
        imp_avant = int(r['impressions_avant'] or 0)
        clics_avant = int(r['clics_avant'] or 0)
        pos_avant = float(r['position_avant']) if r['position_avant'] is not None else None
        imp_apres = int(r['impressions_apres'] or 0)
        clics_apres = int(r['clics_apres'] or 0)
        pos_apres = float(r['position_apres']) if r['position_apres'] is not None else None"""

nouveau = """        r = df_m.iloc[0]
        imp_avant = int(r['impressions_avant']) if pd.notna(r['impressions_avant']) else 0
        clics_avant = int(r['clics_avant']) if pd.notna(r['clics_avant']) else 0
        pos_avant = float(r['position_avant']) if pd.notna(r['position_avant']) else None
        imp_apres = int(r['impressions_apres']) if pd.notna(r['impressions_apres']) else 0
        clics_apres = int(r['clics_apres']) if pd.notna(r['clics_apres']) else 0
        pos_apres = float(r['position_apres']) if pd.notna(r['position_apres']) else None"""

if "pd.notna(r['impressions_avant'])" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
