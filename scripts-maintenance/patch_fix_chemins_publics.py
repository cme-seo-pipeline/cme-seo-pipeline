FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = "CHEMINS_PUBLICS = {'/', '/orcaas', '/orcaas-dashboard', '/orcaas-chat'}"
nouveau = "CHEMINS_PUBLICS = {'/', '/orcaas', '/orcaas-dashboard-data', '/orcaas-chat'}"

if nouveau in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
