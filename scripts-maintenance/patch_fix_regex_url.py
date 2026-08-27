FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# L'ancienne ligne contient un echappement casse (4 backslashes -> 2 dans le
# fichier final -> le groupe (www\\.) cherche un backslash litteral au lieu
# du point, donc ne matche jamais). On la remplace par la version correcte
# (2 backslashes dans ce script -> 1 seul dans le fichier final).

ancien = "u = re_mod.sub(r'^https?://(www\\\\.)?', '', url.strip().lower())"
nouveau = "u = re_mod.sub(r'^https?://(www\\.)?', '', url.strip().lower())"

if ancien not in contenu:
    print("❌ PATCH (correctif regex normaliser_url) : ancre non trouvee")
    print("   Ligne recherchee :", repr(ancien))
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (correctif regex normaliser_url) : echappement corrige")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)

# Verification directe : simuler la meme logique que le script pour confirmer
import re
test = re.sub(r'^https?://(www\.)?', '', 'https://www.comprendre-mon-energie.fr/test/')
test = re.sub(r'/$', '', test)
print("🔎 Test de la regex corrigee sur une URL réelle :", test)
