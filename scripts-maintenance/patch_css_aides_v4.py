FICHIER = "wordpress-plugins/simulateur-aides/simulateur-aides.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    lignes = f.readlines()

ancre = "#<?php echo $uid;?> input[type=number]{border:1.5px solid #e5e7eb;border-radius:10px;padding:0 8px 0 14px;height:52px;font-size:16px;background:#f9fafb;color:#111827;width:100%;outline:none;font-family:inherit;-moz-appearance:textfield;transition:border .15s}\n"
ajout = "#<?php echo $uid;?> input[type=text]{border:1.5px solid #e5e7eb;border-radius:10px;padding:0 14px;height:52px;font-size:16px;background:#f9fafb;color:#111827;width:100%;outline:none;font-family:inherit;-webkit-appearance:none;transition:border .15s;box-sizing:border-box}\n#<?php echo $uid;?> input[type=text]:focus{border-color:var(--g3);background:#fff;box-shadow:0 0 0 3px rgba(245,158,11,.1)}\n"

if "input[type=text]{border:1.5px solid #e5e7eb;border-radius:10px;padding:0 14px" in "".join(lignes):
    print("⏭️  PATCH (input text) : deja present, ignore")
elif ancre not in lignes:
    print("❌ PATCH (input text) : ancre non trouvee")
else:
    i = lignes.index(ancre)
    lignes = lignes[:i+1] + [ajout] + lignes[i+1:]
    print("✅ PATCH (input text) : style ajoute pour le champ RFR (et tout input[type=text] non classe)")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.writelines(lignes)

print("📝 Fichier sauvegarde :", FICHIER)
