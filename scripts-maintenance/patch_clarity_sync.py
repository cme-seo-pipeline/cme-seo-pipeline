FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ── Partie 1 : variable d'environnement ──────────────────────────────
ancre_env = 'SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")'
nouveau_env = ancre_env + '\nCLARITY_API_TOKEN = os.environ.get("CLARITY_API_TOKEN", "")'

if "CLARITY_API_TOKEN = os.environ.get" in contenu:
    print("⏭️  PATCH (env CLARITY_API_TOKEN) : deja present, ignore")
elif ancre_env not in contenu:
    print("❌ PATCH (env CLARITY_API_TOKEN) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre_env, nouveau_env, 1)
    print("✅ PATCH (env CLARITY_API_TOKEN) : ajoute")

# ── Partie 2 : fonction de synchronisation ───────────────────────────
ancre_fonction = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def rafraichir_clarity_insights(client_bq):
    """CHANTIER SOUVERAINETE SHELL : synchronise les insights Microsoft
    Clarity (Data Export API) vers BigQuery. Limite API : 10 requetes/jour
    par projet, max 3 jours de donnees par appel — on utilise numOfDays=1,
    en phase avec un rafraichissement quotidien unique."""
    print("🔗 SYNCHRONISATION CLARITY INSIGHTS...")
    if not CLARITY_API_TOKEN:
        print("  ⚠️ CLARITY_API_TOKEN absent, synchronisation ignoree")
        return 0
    try:
        resp = requests.get(
            "https://www.clarity.ms/export-data/api/v1/project-live-insights",
            headers={"Authorization": f"Bearer {CLARITY_API_TOKEN}"},
            params={"numOfDays": 1},
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
        lignes.append({
            "date_sync": date_sync,
            "metric_name": m.get("metricName", ""),
            "information": json.dumps(m.get("information", []), ensure_ascii=False),
            "synced_at": datetime.now().isoformat(),
        })

    try:
        errors = client_bq.insert_rows_json(
            f"{PROJECT_ID}.04_pipeline_seo.clarity_insights_quotidien", lignes
        )
        if errors:
            print(f"  ⚠️ Erreurs insertion BQ : {errors}")
            return 0
        print(f"  ✅ {len(lignes)} metriques Clarity synchronisees")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def rafraichir_clarity_insights" in contenu:
    print("⏭️  PATCH (sync Clarity) : deja present, ignore")
elif ancre_fonction not in contenu:
    print("❌ PATCH (sync Clarity) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre_fonction, nouvelle_fonction, 1)
    print("✅ PATCH (sync Clarity) : fonction ajoutee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
