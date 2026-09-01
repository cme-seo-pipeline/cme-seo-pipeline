FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = "label: 'Score d\\'opportunite'"
nouveau = "label: 'Score opportunite'"

if nouveau in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee, verifier manuellement")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : apostrophe retiree, chaine JS corrigee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
