FICHIERS_VERSIONS = [
    ("wordpress-plugins/simulateur-aides/simulateur-aides.php", " * Version:     1.0.1\n", " * Version:     1.0.2\n"),
    ("wordpress-plugins/comparateur-energie/comparateur-energie.php", " * Version:     3.4.2\n", " * Version:     3.4.3\n"),
    ("wordpress-plugins/simulateur-solaire/simulateur-solaire.php", " * Version:     3.8.0\n", " * Version:     3.8.1\n"),
]

for chemin, ancien, nouveau in FICHIERS_VERSIONS:
    with open(chemin, "r", encoding="utf-8") as f:
        lignes = f.readlines()

    if ancien not in lignes:
        print(f"❌ {chemin} : ligne de version non trouvee exactement")
        continue

    lignes[lignes.index(ancien)] = nouveau
    with open(chemin, "w", encoding="utf-8") as f:
        f.writelines(lignes)
    print(f"✅ {chemin} : version mise a jour ({ancien.strip()} → {nouveau.strip()})")
