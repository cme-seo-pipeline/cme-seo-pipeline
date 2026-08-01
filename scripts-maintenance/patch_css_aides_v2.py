FICHIER = "wordpress-plugins/simulateur-aides/simulateur-aides.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    lignes = f.readlines()

ancien = "#<?php echo $uid;?> .tog{display:flex;gap:8px}\n#<?php echo $uid;?> .tbtn{flex:1;height:52px;border:1.5px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:14px;cursor:pointer;font-family:inherit;transition:all .15s;font-weight:500}\n"
nouveau = "#<?php echo $uid;?> .tog{display:flex;gap:8px;flex-wrap:wrap}\n#<?php echo $uid;?> .tbtn{flex:1;min-width:90px;min-height:52px;border:1.5px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:14px;cursor:pointer;font-family:inherit;transition:all .15s;font-weight:500;display:flex;align-items:center;justify-content:center;text-align:center;padding:6px}\n"

contenu = "".join(lignes)
if ancien not in contenu:
    print("❌ PATCH (tog/tbtn aides) : bloc non trouve")
else:
    contenu = contenu.replace(ancien, nouveau)
    lignes = contenu.splitlines(keepends=True)
    print("✅ PATCH (tog/tbtn aides) : hauteur fixe corrigee, meme traitement que comparateur/solaire")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.writelines(lignes)

print("📝 Fichier sauvegarde :", FICHIER)
