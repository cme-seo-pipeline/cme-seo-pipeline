FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''        f"QUESTION DU PORTEUR DE PROJET :\\n{question}\\n\\n"
        "Reponds de facon claire et concrete, en t'appuyant EXCLUSIVEMENT sur les "
        "donnees ci-dessus. Si tu n'as pas l'information pour repondre precisement, "
        "dis-le clairement plutot que d'inventer."'''

nouveau = '''        f"QUESTION DU PORTEUR DE PROJET (reponds dans la meme langue que cette "
        f"question precise, meme si tout ce qui precede est en francais) :\\n{question}\\n\\n"
        "Reponds de facon claire et concrete, en t'appuyant EXCLUSIVEMENT sur les "
        "donnees ci-dessus. Si tu n'as pas l'information pour repondre precisement, "
        "dis-le clairement plutot que d'inventer."'''

if "meme si tout ce qui precede est en francais" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
