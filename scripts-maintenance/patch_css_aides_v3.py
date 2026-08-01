FICHIER = "wordpress-plugins/simulateur-aides/simulateur-aides.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    lignes = f.readlines()

# ============================================================
# PATCH 1 — .hero-text : suppression du min-width:200px qui
# force le debordement sur tres petit ecran
# ============================================================
ancien1 = "#<?php echo $uid;?> .hero-text{flex:1;min-width:200px}\n"
nouveau1 = "#<?php echo $uid;?> .hero-text{flex:1;min-width:0}\n"

if ancien1 not in lignes:
    print("❌ PATCH 1 (hero-text) : ligne non trouvee")
else:
    lignes[lignes.index(ancien1)] = nouveau1
    print("✅ PATCH 1 (hero-text) : min-width force retire")

# ============================================================
# PATCH 2 — .aid-left / .aid-right / .aid-body : min-width:0
# defensif (empeche tout enfant de forcer un debordement)
# ============================================================
ancien2 = "#<?php echo $uid;?> .aid-body{display:grid;grid-template-columns:1fr;gap:0}\n"
nouveau2 = "#<?php echo $uid;?> .aid-body{display:grid;grid-template-columns:1fr;gap:0;min-width:0}\n"

if ancien2 not in lignes:
    print("❌ PATCH 2a (aid-body) : ligne non trouvee")
else:
    lignes[lignes.index(ancien2)] = nouveau2
    print("✅ PATCH 2a (aid-body) : min-width:0 ajoute")

ancien3 = "#<?php echo $uid;?> .aid-left{padding:1.25rem;display:flex;flex-direction:column;gap:12px}\n"
nouveau3 = "#<?php echo $uid;?> .aid-left{padding:1.25rem;display:flex;flex-direction:column;gap:12px;min-width:0}\n"

if ancien3 not in lignes:
    print("❌ PATCH 2b (aid-left) : ligne non trouvee")
else:
    lignes[lignes.index(ancien3)] = nouveau3
    print("✅ PATCH 2b (aid-left) : min-width:0 ajoute")

ancien4 = "#<?php echo $uid;?> .aid-right{padding:1.25rem 1.25rem 1.25rem 0;display:flex;flex-direction:column;gap:12px}\n"
nouveau4 = "#<?php echo $uid;?> .aid-right{padding:1.25rem 1.25rem 1.25rem 0;display:flex;flex-direction:column;gap:12px;min-width:0}\n"

if ancien4 not in lignes:
    print("❌ PATCH 2c (aid-right) : ligne non trouvee")
else:
    lignes[lignes.index(ancien4)] = nouveau4
    print("✅ PATCH 2c (aid-right) : min-width:0 ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.writelines(lignes)

print("📝 Fichier sauvegarde :", FICHIER)
