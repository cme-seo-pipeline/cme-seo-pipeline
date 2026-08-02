FICHIER = "cme-mobile/app/(tabs)/profil.tsx"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''    lien: "https://web.facebook.com/people/Comprendre-Mon-%C3%89nergie/61592180973793/",'''
nouveau = '''    lien: "https://www.facebook.com/people/Comprendre-Mon-%C3%89nergie/61592180973793/",'''

if nouveau in contenu:
    print("⏭️  PATCH (lien Facebook) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (lien Facebook) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (lien Facebook) : web.facebook.com -> www.facebook.com")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
