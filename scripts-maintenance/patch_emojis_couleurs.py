FICHIER = "wordpress-plugins/comparateur-energie/comparateur-energie.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

import re

# ============================================================
# PATCH 1 — Retrait des emojis decoratifs (garde fleches et coche d'etape)
# ============================================================
emojis_decoratifs = "🔥⚡🏠🏢♻🛢🌙☀💡📊📋📄🔄⭐✅"
nb_avant = sum(contenu.count(e) for e in emojis_decoratifs)

pattern_emoji = re.compile("[" + emojis_decoratifs + "]" + r"\s?")
contenu = pattern_emoji.sub("", contenu)

nb_apres = sum(contenu.count(e) for e in emojis_decoratifs)
print(f"✅ PATCH 1 (emojis) : {nb_avant - nb_apres} occurrences retirees ({nb_apres} restantes)")

# ============================================================
# PATCH 2 — Classes distinctes sur les cartes-resume elec/gaz
# ============================================================
ancien2a = "var sm=mk('div','summ-box');sm.style.flex='1';"
nouveau2a = "var sm=mk('div','summ-box summ-elec');sm.style.flex='1';"
if ancien2a in contenu:
    contenu = contenu.replace(ancien2a, nouveau2a, 1)
    print("✅ PATCH 2a (classe summ-elec) : ajoutee")
else:
    print("⏭️  PATCH 2a : ancre non trouvee (deja applique ?)")

ancien2b = "var smg=mk('div','summ-box');smg.style.flex='1';"
nouveau2b = "var smg=mk('div','summ-box summ-gaz');smg.style.flex='1';"
if ancien2b in contenu:
    contenu = contenu.replace(ancien2b, nouveau2b, 1)
    print("✅ PATCH 2b (classe summ-gaz) : ajoutee")
else:
    print("⏭️  PATCH 2b : ancre non trouvee (deja applique ?)")

# ============================================================
# PATCH 3 — CSS : couleurs de fond distinctes (boutons + cartes)
# ============================================================
ancien3 = '#<?php echo $uid;?> .tbtn.on{border:1.5px solid #3b82f6;background:#eff6ff;color:#1d4ed8;font-weight:500}'

nouveau3 = ancien3 + '''
#<?php echo $uid;?> .tog .tbtn:nth-child(1){background:#eff6ff}
#<?php echo $uid;?> .tog .tbtn:nth-child(2){background:#fff7ed}
#<?php echo $uid;?> .tog .tbtn:nth-child(3){background:#faf5ff}
#<?php echo $uid;?> .tog .tbtn:nth-child(1).on{background:#dbeafe;border-color:#3b82f6;color:#1d4ed8}
#<?php echo $uid;?> .tog .tbtn:nth-child(2).on{background:#fed7aa;border-color:#f97316;color:#9a3412}
#<?php echo $uid;?> .tog .tbtn:nth-child(3).on{background:#e9d5ff;border-color:#a855f7;color:#6b21a8}
#<?php echo $uid;?> .summ-elec{border-left:4px solid #3b82f6;background:#eff6ff}
#<?php echo $uid;?> .summ-gaz{border-left:4px solid #f97316;background:#fff7ed}'''

if ".tog .tbtn:nth-child(1)" in contenu:
    print("⏭️  PATCH 3 (CSS couleurs) : deja present, ignore")
elif ancien3 not in contenu:
    print("❌ PATCH 3 (CSS couleurs) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien3, nouveau3, 1)
    print("✅ PATCH 3 (CSS couleurs) : boutons + cartes-resume")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
