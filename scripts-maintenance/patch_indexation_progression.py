FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''def synchroniser_indexation(client_bq):
    """CHANTIER INDEXATION : verifie pour chaque page connue si Google l'a
    reellement indexee (URL Inspection API de Search Console) -- differe
    des metriques GSC habituelles, qui ne montrent que les pages DEJA
    visibles en recherche."""
    print("SYNCHRONISATION INDEXATION GOOGLE...")'''

nouveau = '''def synchroniser_indexation(client_bq, limite=None):
    """CHANTIER INDEXATION : verifie pour chaque page connue si Google l'a
    reellement indexee (URL Inspection API de Search Console). limite
    (optionnel) : ne traite que les N premieres pages, utile pour tester
    le comportement/la vitesse reelle de l'API avant de lancer sur
    l'ensemble du site."""
    print(f"SYNCHRONISATION INDEXATION GOOGLE (limite={limite})...")'''

if "def synchroniser_indexation(client_bq, limite=None)" in contenu:
    print("SKIP (partie 1) : deja present")
elif ancien not in contenu:
    print("ERREUR (partie 1) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK (partie 1/3)")

ancien2 = '''    lignes = []
    for _, row in df.iterrows():
        post_id = int(row['post_id'])
        url = row['url']
        entree = {
            "post_id": post_id, "url": url,
            "coverage_state": None, "verdict": None, "robots_txt_state": None,
            "indexing_state": None, "page_fetch_state": None,
            "last_crawl_time": None, "crawled_as": None,
            "erreur": None, "checked_at": datetime.now().isoformat(),
        }
        try:
            body = {"inspectionUrl": url, "siteUrl": "https://www.comprendre-mon-energie.fr/"}
            r = requests.post(
                "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
                json=body, timeout=20
            )'''

nouveau2 = '''    if limite:
        df = df.head(int(limite))

    debut_chrono = datetime.now()
    lignes = []
    for i, (_, row) in enumerate(df.iterrows()):
        post_id = int(row['post_id'])
        url = row['url']
        entree = {
            "post_id": post_id, "url": url,
            "coverage_state": None, "verdict": None, "robots_txt_state": None,
            "indexing_state": None, "page_fetch_state": None,
            "last_crawl_time": None, "crawled_as": None,
            "erreur": None, "checked_at": datetime.now().isoformat(),
        }
        try:
            body = {"inspectionUrl": url, "siteUrl": "https://www.comprendre-mon-energie.fr/"}
            r = requests.post(
                "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
                json=body, timeout=10
            )'''

if "debut_chrono = datetime.now()" in contenu:
    print("SKIP (partie 2) : deja present")
elif ancien2 not in contenu:
    print("ERREUR (partie 2) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("OK (partie 2/3)")

ancien3 = '''        lignes.append(entree)

    if not lignes:
        print("  Aucune page a verifier")
        return 0'''

nouveau3 = '''        lignes.append(entree)

        if (i + 1) % 20 == 0:
            ecoule = (datetime.now() - debut_chrono).total_seconds()
            print(f"  Progression : {i + 1}/{len(df)} pages traitees ({ecoule:.0f}s ecoulees)")

    if not lignes:
        print("  Aucune page a verifier")
        return 0'''

if "Progression :" in contenu:
    print("SKIP (partie 3) : deja present")
elif ancien3 not in contenu:
    print("ERREUR (partie 3) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien3, nouveau3, 1)
    print("OK (partie 3/3)")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
