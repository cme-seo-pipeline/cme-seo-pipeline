FICHIER = "wordpress-plugins/comparateur-energie/comparateur-energie.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    lignes = f.readlines()

ancien = "#<?php echo $uid;?> .tbtn{flex:1;min-width:80px;height:44px;border:1px solid #e5e7eb;border-radius:10px;background:#f9fafb;color:#374151;font-size:13px;cursor:pointer;font-family:inherit;transition:all .15s;padding:0 8px;line-height:1.2}\n"
nouveau = "#<?php echo $uid;?> .tbtn{flex:1;min-width:80px;min-height:44px;border:1px solid #e5e7eb;border-radius:10px;background:#f9fafb;color:#374151;font-size:13px;cursor:pointer;font-family:inherit;transition:all .15s;padding:8px 6px;line-height:1.2;display:flex;align-items:center;justify-content:center;text-align:center}\n"

if ancien not in lignes:
    print("❌ PATCH (bouton tbtn) : ligne non trouvee")
else:
    lignes[lignes.index(ancien)] = nouveau
    print("✅ PATCH (bouton tbtn) : hauteur fixe remplacee par hauteur minimale + centrage")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.writelines(lignes)

print("📝 Fichier sauvegarde :", FICHIER)
