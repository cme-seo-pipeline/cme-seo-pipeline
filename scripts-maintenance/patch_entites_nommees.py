FICHIER = "cme-mobile/app/(tabs)/index.tsx"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''  texte = texte
    .replace(/&#8217;/g, "'")
    .replace(/&#8216;/g, "'")
    .replace(/&#8220;/g, '"')
    .replace(/&#8221;/g, '"')
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\\[&hellip;\\]/g, "…")
    .replace(/&hellip;/g, "…");'''

nouveau = '''  texte = texte
    .replace(/&#8217;|&rsquo;/g, "'")
    .replace(/&#8216;|&lsquo;/g, "'")
    .replace(/&#8220;|&ldquo;/g, '"')
    .replace(/&#8221;|&rdquo;/g, '"')
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\\[&hellip;\\]/g, "…")
    .replace(/&hellip;/g, "…");'''

if "&rsquo;" in contenu:
    print("⏭️  PATCH (entites nommees) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (entites nommees) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (entites nommees) : &rsquo;/&lsquo;/&rdquo;/&ldquo; geres desormais")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
