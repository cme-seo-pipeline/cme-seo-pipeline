import json

FICHIER = "cme-mobile/app.json"

with open(FICHIER, "r", encoding="utf-8") as f:
    config = json.load(f)

if "orientation" in config["expo"]:
    del config["expo"]["orientation"]
    print("✅ PATCH (orientation) : restriction 'portrait' retiree")
else:
    print("⏭️  PATCH (orientation) : deja absente, ignore")

with open(FICHIER, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("📝 Fichier sauvegarde :", FICHIER)
