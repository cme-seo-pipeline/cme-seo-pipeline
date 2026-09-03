FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

remplacements = [
    ("const loading = ajouterMessage('ORCAAS reflechit...', 'loading');",
     "const loading = ajouterMessage(TRADUCTIONS[langueActuelle()].reflexion, 'loading');"),
    ("ajouterMessage(data.reponse || data.erreur || 'Erreur inconnue', 'orcaas');",
     "ajouterMessage(data.reponse || data.erreur || TRADUCTIONS[langueActuelle()].erreur_inconnue, 'orcaas');"),
    ("ajouterMessage('Erreur de connexion : ' + e.message, 'orcaas');",
     "ajouterMessage(TRADUCTIONS[langueActuelle()].erreur_connexion + e.message, 'orcaas');"),
    ("document.getElementById('vue-dashboard').innerHTML = '<div class=\"vide\">Erreur de chargement : ' + e.message + '</div>';",
     "document.getElementById('vue-dashboard').innerHTML = '<div class=\"vide\">' + TRADUCTIONS[langueActuelle()].erreur_chargement + e.message + '</div>';"),
    ("document.getElementById('periode-affichee').textContent = 'Periode : ' + (donnees.date_debut || db) + ' au ' + (donnees.date_fin || df);",
     "document.getElementById('periode-affichee').textContent = TRADUCTIONS[langueActuelle()].periode_prefixe + (donnees.date_debut || db) + ' - ' + (donnees.date_fin || df);"),
]

nb_ok = 0
nb_echecs = 0
for ancien, nouveau in remplacements:
    if nouveau in contenu:
        continue
    if ancien not in contenu:
        print(f"ERREUR : ancre non trouvee pour : {ancien[:70]}")
        nb_echecs += 1
        continue
    contenu = contenu.replace(ancien, nouveau, 1)
    nb_ok += 1

print(f"OK : {nb_ok} remplacements dynamiques appliques, {nb_echecs} echecs")

ancien_vide = "Aucune donnee disponible</div>';"
nouveau_vide = "' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';"
nb_vide = contenu.count(ancien_vide)
if nb_vide > 0:
    contenu = contenu.replace(ancien_vide, nouveau_vide)
    print(f"OK : {nb_vide} messages 'aucune donnee' rendus multilingues")
else:
    print("ERREUR : aucun message 'aucune donnee' trouve")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
