FICHIER = "app.json"

with open(FICHIER, "r", encoding="utf-8") as f:
    lignes = f.readlines()

# ============================================================
# PATCH 1 — googleServicesFile dans le bloc android
# ============================================================
ancien1 = '''    "android": {
      "package": "fr.comprendremonenergie.espaceclient",
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#ffffff"
      }
    },
'''
nouveau1 = '''    "android": {
      "package": "fr.comprendremonenergie.espaceclient",
      "googleServicesFile": "./google-services.json",
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#ffffff"
      }
    },
'''

contenu = "".join(lignes)

if "googleServicesFile" in contenu:
    print("⏭️  PATCH 1 (googleServicesFile) : deja present, ignore")
elif ancien1 not in contenu:
    print("❌ PATCH 1 (googleServicesFile) : bloc non trouve")
else:
    contenu = contenu.replace(ancien1, nouveau1)
    print("✅ PATCH 1 (googleServicesFile) : ajoute")

# ============================================================
# PATCH 2 — expo-notifications dans les plugins
# ============================================================
ancien2 = '''    "plugins": [
      "expo-router"
    ],
'''
nouveau2 = '''    "plugins": [
      "expo-router",
      "expo-notifications"
    ],
'''

if '"expo-notifications"' in contenu:
    print("⏭️  PATCH 2 (plugin notifications) : deja present, ignore")
elif ancien2 not in contenu:
    print("❌ PATCH 2 (plugin notifications) : bloc non trouve")
else:
    contenu = contenu.replace(ancien2, nouveau2)
    print("✅ PATCH 2 (plugin notifications) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
