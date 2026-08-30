FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = "import threading\nfrom datetime import datetime"
nouveau = "import threading\nimport requests\nfrom datetime import datetime"

# Cette fois on verifie specifiquement l'import GLOBAL (en debut de fichier,
# juste apres "import threading"), pas une simple presence de la chaine
# "import requests" ailleurs dans le fichier (les imports locaux existants
# utilisent un alias "as req" et ne suffisent pas pour notre nouvelle route).
if nouveau in contenu:
    print("⏭️  PATCH (import requests global) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (import requests global) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (import requests global) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
