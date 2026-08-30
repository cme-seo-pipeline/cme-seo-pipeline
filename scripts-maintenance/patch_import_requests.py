FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = "import threading\nfrom datetime import datetime"
nouveau = "import threading\nimport requests\nfrom datetime import datetime"

if "import requests" in contenu:
    print("⏭️  PATCH (import requests) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (import requests) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (import requests) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
