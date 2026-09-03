FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = "  .vide { color: #64748b; font-size: 14px; text-align: center; padding: 40px 0; }"

nouveau = """  .vide { color: #64748b; font-size: 14px; text-align: center; padding: 40px 0; }

  @media (max-width: 640px) {
    header { padding: 10px 14px; flex-wrap: wrap; row-gap: 8px; }
    header h1 { font-size: 16px; }
    header .badge { font-size: 10px; padding: 3px 8px; }
    nav { margin-left: 0; width: 100%; order: 3; }
    nav button { flex: 1; padding: 10px 8px; font-size: 13px; }
    #chat { padding: 14px; gap: 12px; }
    .msg { max-width: 88%; font-size: 15px; padding: 10px 14px; }
    #input-zone { padding: 12px 14px; gap: 8px; }
    #question { font-size: 16px; padding: 10px 12px; }
    #send { padding: 10px 16px; font-size: 14px; }
    #vue-dashboard.actif { grid-template-columns: 1fr; padding: 14px; gap: 14px; }
    .carte { padding: 14px; }
    #barre-filtre { flex-wrap: wrap; padding: 12px 14px; gap: 10px; }
    #barre-filtre label { flex: 1 1 45%; min-width: 130px; }
    #barre-filtre button { flex: 1 1 100%; }
    #periode-affichee { width: 100%; margin-left: 0; text-align: center; order: 10; }
  }"""

if "@media (max-width: 640px)" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
