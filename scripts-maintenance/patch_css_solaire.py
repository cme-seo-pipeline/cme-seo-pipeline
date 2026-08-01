FICHIER = "wordpress-plugins/simulateur-solaire/simulateur-solaire.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    lignes = f.readlines()

# ============================================================
# PATCH 1 — overflow-x:hidden sur le conteneur racine
# ============================================================
ancien1 = "  width:100%;max-width:1400px;margin:0 auto;background:#f1f5f9;\n"
nouveau1 = "  width:100%;max-width:1400px;margin:0 auto;background:#f1f5f9;overflow-x:hidden;\n"

if ancien1 not in lignes:
    print("❌ PATCH 1 (overflow-x) : ligne non trouvee")
else:
    lignes[lignes.index(ancien1)] = nouveau1
    print("✅ PATCH 1 (overflow-x) : ajoute sur le conteneur racine")

# ============================================================
# PATCH 2 — .tog flex-wrap + .tbtn hauteur minimale (defensif)
# ============================================================
ancien2 = "#<?php echo $uid;?> .tog{display:flex;gap:8px}\n#<?php echo $uid;?> .tbtn{flex:1;height:52px;border:1.5px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:14px;cursor:pointer;font-family:inherit;transition:all .15s;font-weight:500}\n"
nouveau2 = "#<?php echo $uid;?> .tog{display:flex;gap:8px;flex-wrap:wrap}\n#<?php echo $uid;?> .tbtn{flex:1;min-width:90px;min-height:52px;border:1.5px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:14px;cursor:pointer;font-family:inherit;transition:all .15s;font-weight:500;display:flex;align-items:center;justify-content:center;text-align:center;padding:6px}\n"

contenu = "".join(lignes)
if ancien2 not in contenu:
    print("❌ PATCH 2 (tog/tbtn) : bloc non trouve")
else:
    contenu = contenu.replace(ancien2, nouveau2)
    lignes = contenu.splitlines(keepends=True)
    print("✅ PATCH 2 (tog/tbtn) : renfort defensif applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.writelines(lignes)

print("📝 Fichier sauvegarde :", FICHIER)
