FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def rafraichir_clarity_par_page(client_bq):
    """CHANTIER G.2 : synchronise les insights Clarity PAR PAGE (dimension1=URL)
    pour permettre le chainage engagement->page dans le tunnel de conversion
    unifie. Complete rafraichir_clarity_insights() (vue globale du projet)."""
    print("🔗 SYNCHRONISATION CLARITY PAR PAGE...")
    if not CLARITY_API_TOKEN:
        print("  ⚠️ CLARITY_API_TOKEN absent, synchronisation ignoree")
        return 0
    try:
        resp = requests.get(
            "https://www.clarity.ms/export-data/api/v1/project-live-insights",
            headers={"Authorization": f"Bearer {CLARITY_API_TOKEN}"},
            params={"numOfDays": 1, "dimension1": "URL"},
            timeout=30
        )
        if resp.status_code != 200:
            print(f"  ⚠️ Erreur API Clarity {resp.status_code} : {resp.text[:200]}")
            return 0
        metrics = resp.json()
    except Exception as e:
        print(f"  ⚠️ Erreur appel API Clarity : {e}")
        return 0

    if not metrics:
        print("  ℹ️ Aucune metrique retournee")
        return 0

    date_sync = datetime.now().date().isoformat()
    lignes = []
    for m in metrics:
        metric_name = m.get("metricName", "")
        for item in m.get("information", []):
            url = item.get("Url", "")
            if not url:
                continue
            autres = {k: v for k, v in item.items() if k != "Url"}
            lignes.append({
                "date_sync": date_sync,
                "metric_name": metric_name,
                "url": url,
                "donnees": json.dumps(autres, ensure_ascii=False),
                "synced_at": datetime.now().isoformat(),
            })

    if not lignes:
        print("  ℹ️ Aucune ligne avec URL a inserer (dimension non supportee pour cette metrique ?)")
        return 0

    try:
        errors = client_bq.insert_rows_json(
            f"{PROJECT_ID}.04_pipeline_seo.clarity_insights_par_page", lignes
        )
        if errors:
            print(f"  ⚠️ Erreurs insertion BQ : {errors}")
            return 0
        print(f"  ✅ {len(lignes)} lignes Clarity par page synchronisees")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def rafraichir_clarity_par_page" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_fonction, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
