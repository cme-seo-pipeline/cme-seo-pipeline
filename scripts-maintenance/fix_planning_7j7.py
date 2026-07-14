with open('pipeline.py', 'r') as f:
    content = f.read()

# ── 1. JOURS_PUBLICATION : 7j/7 (0=Lun ... 6=Dim) ──────────────────
old_jours = '    "JOURS_PUBLICATION": [0, 1, 2, 3, 4],  # Mardi, Jeudi, Samedi'
new_jours = '    "JOURS_PUBLICATION": [0, 1, 2, 3, 4, 5, 6],  # 7j/7'
if old_jours in content:
    content = content.replace(old_jours, new_jours, 1)
    print("✅ JOURS_PUBLICATION -> 7j/7")
else:
    print("❌ JOURS_PUBLICATION non trouvé")

with open('pipeline.py', 'w') as f:
    f.write(content)
