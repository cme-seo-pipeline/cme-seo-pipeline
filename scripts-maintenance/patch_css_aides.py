FICHIER = "wordpress-plugins/simulateur-aides/simulateur-aides.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    lignes = f.readlines()

# ============================================================
# PATCH 1 — overflow-x:hidden sur le conteneur racine
# ============================================================
ancien1 = "#<?php echo $uid;?>{--g1:#78350f;--g2:#b45309;--g3:#f59e0b;--g4:#d97706;--gb:#fffbeb;--gbl:#fde68a;--gbm:#fcd34d;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;width:100%;max-width:1400px;margin:0 auto;background:#f1f5f9}\n"
nouveau1 = "#<?php echo $uid;?>{--g1:#78350f;--g2:#b45309;--g3:#f59e0b;--g4:#d97706;--gb:#fffbeb;--gbl:#fde68a;--gbm:#fcd34d;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;width:100%;max-width:1400px;margin:0 auto;background:#f1f5f9;overflow-x:hidden}\n"

if ancien1 not in lignes:
    print("❌ PATCH 1 (overflow-x) : ligne non trouvee")
else:
    lignes[lignes.index(ancien1)] = nouveau1
    print("✅ PATCH 1 (overflow-x) : ajoute sur le conteneur racine")

# ============================================================
# PATCH 2 — Ajout du bloc mobile manquant (juste avant </style>)
# ============================================================
ancre2 = "</style>\n"
bloc_mobile = '@media(max-width:480px){#<?php echo $uid;?> .g2,#<?php echo $uid;?> .opts,#<?php echo $uid;?> .prev-grid{grid-template-columns:1fr}#<?php echo $uid;?> .aid-left,#<?php echo $uid;?> .aid-right{padding:1rem}}\n'

if "grid-template-columns:1fr}#<?php echo $uid;?> .aid-left" in "".join(lignes):
    print("⏭️  PATCH 2 (bloc mobile) : deja present, ignore")
else:
    indices = [i for i, l in enumerate(lignes) if l == ancre2]
    if len(indices) != 1:
        print(f"❌ PATCH 2 : ancre trouvee {len(indices)} fois (attendu 1), aucune modification")
    else:
        i = indices[0]
        lignes = lignes[:i] + [bloc_mobile] + lignes[i:]
        print("✅ PATCH 2 (bloc mobile) : ajoute avant </style>")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.writelines(lignes)

print("📝 Fichier sauvegarde :", FICHIER)
