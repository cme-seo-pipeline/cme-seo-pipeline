FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''  "meta_description": "meta description incitant au clic, ENTRE 150 ET 160 CARACTERES pile (jamais plus, jamais moins de 150), phrase complete se terminant par un point, ne JAMAIS couper un mot en cours de generation",'''

nouveau = '''  "meta_description": "Meta description ORIENTEE ACTION pour maximiser le taux de clic. Commence par un verbe d'action a l'imperatif (Decouvrez, Calculez, Comparez, Economisez, Profitez de, Obtenez...) ou une accroche chiffree concrete (montant, pourcentage, delai). Inclut un benefice clair et tangible pour le lecteur, pas une simple description du contenu. ENTRE 150 ET 160 CARACTERES pile (jamais plus, jamais moins de 150), phrase complete se terminant par un point, ne JAMAIS couper un mot en cours de generation. Exemples de structure (a adapter, ne jamais copier tel quel) : 'Decouvrez [benefice concret] en [nombre] etapes simples.' ou 'Economisez jusqu'a [X] sur [sujet] : [benefice].'",'''

if "ORIENTEE ACTION" in contenu:
    print("⏭️  PATCH (meta description action) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (meta description action) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (meta description action) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
