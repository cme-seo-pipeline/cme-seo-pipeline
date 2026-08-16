FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = "def recuperer_donnees_officielles(silo, sous_silo, client_bq):"

nouveau = '''def rafraichir_indicateurs_reglementaires(client_bq):
    """Recupere les dernieres valeurs officielles connues (CRE Gaz/Elec,
    ANAH Aides) depuis les sources officielles et les insere dans
    indicateurs_reglementaires. Concu pour tourner periodiquement
    (hebdomadaire via Cloud Scheduler), independamment du run de redaction —
    sans ce rafraichissement, les donnees injectees dans les articles
    deviendraient obsoletes avec le temps."""
    import io
    from datetime import datetime as dt
    headers_cre = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    run_id = dt.now().strftime("%Y%m%d_%H%M")
    lignes = []

    # --- Electricite (TRVE) ---
    try:
        r = requests.get(
            "https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/Option_Base.csv",
            headers=headers_cre, timeout=30
        )
        df_elec = pd.read_csv(io.StringIO(r.content.decode("latin-1")), sep=None, engine="python")
        df_elec['DATE_DEBUT_dt'] = pd.to_datetime(df_elec['DATE_DEBUT'], dayfirst=True)
        derniere_date = df_elec['DATE_DEBUT_dt'].max()
        df_derniere = df_elec[df_elec['DATE_DEBUT_dt'] == derniere_date]
        for _, row in df_derniere.iterrows():
            puissance = f"{row['P_SOUSCRITE']} kVA"
            for indicateur, col, unite in [
                ("TRVE_part_variable_TTC", "PART_VARIABLE_TTC", "€/kWh"),
                ("TRVE_part_fixe_TTC", "PART_FIXE_TTC", "€/an"),
            ]:
                val = str(row[col]).replace(",", ".")
                lignes.append({
                    "domaine": "Électricité", "indicateur": indicateur,
                    "sous_categorie": puissance, "valeur": float(val), "unite": unite,
                    "date_debut_validite": derniere_date.date().isoformat(),
                    "date_verification": dt.now().isoformat(), "run_id": run_id,
                    "source_url": "https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/Option_Base.csv",
                })
        print(f"  ✅ Electricite : {len(df_derniere) * 2} valeurs ({derniere_date.date()})")
    except Exception as e:
        print(f"  ⚠️ Erreur refresh Electricite : {e}")

    # --- Gaz (PRVG) ---
    try:
        r = requests.get(
            "https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/OPEN_DATA_GRDF.xlsx",
            headers=headers_cre, timeout=30
        )
        df_gaz = pd.read_excel(io.BytesIO(r.content), sheet_name="Historique PRVG moyen")
        derniere_ligne = df_gaz.iloc[-1]
        lignes.append({
            "domaine": "Gaz", "indicateur": "PRVG_moyen_TTC", "sous_categorie": None,
            "valeur": float(derniere_ligne['Prix repère moyen TTC (€/MWh)']), "unite": "€/MWh",
            "date_debut_validite": pd.to_datetime(derniere_ligne['Date']).date().isoformat(),
            "date_verification": dt.now().isoformat(), "run_id": run_id,
            "source_url": "https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/OPEN_DATA_GRDF.xlsx",
        })
        print(f"  ✅ Gaz : PRVG {lignes[-1]['valeur']} €/MWh ({lignes[-1]['date_debut_validite']})")
    except Exception as e:
        print(f"  ⚠️ Erreur refresh Gaz : {e}")

    # --- Aides (ANAH — situation-temoin fixe, validee) ---
    try:
        situation = {
            "vous.propriétaire.statut": '"propriétaire occupant"',
            "logement.propriétaire occupant": "oui",
            "ménage.personnes": 3,
            "ménage.revenu": '"modeste"',
            "ménage.commune": '"75056"',
            "parcours d'aide": '"accompagné"',
            "fields": "ampleur.pourcent d'écrêtement",
        }
        r = requests.get("https://mesaides.france-renov.gouv.fr/api/v1/", params=situation, timeout=20)
        data_aide = r.json()["ampleur.pourcent d'écrêtement"]
        lignes.append({
            "domaine": "Aides", "indicateur": "ampleur_pourcent_ecretement",
            "sous_categorie": "propriétaire occupant modeste, 3 pers., parcours accompagné",
            "valeur": float(data_aide["rawValue"]), "unite": "%",
            "date_debut_validite": dt.now().date().isoformat(),
            "date_verification": dt.now().isoformat(), "run_id": run_id,
            "source_url": "https://mesaides.france-renov.gouv.fr/api/v1/",
        })
        print(f"  ✅ Aides : écrêtement {lignes[-1]['valeur']} %")
    except Exception as e:
        print(f"  ⚠️ Erreur refresh Aides : {e}")

    if lignes:
        client_bq.insert_rows_json(
            f"{PROJECT_ID}.{DATASET_ID}.indicateurs_reglementaires", lignes
        )
        print(f"✅ RAFRAICHISSEMENT INDICATEURS : {len(lignes)} lignes inserees")
    return len(lignes)


def recuperer_donnees_officielles(silo, sous_silo, client_bq):'''

if "def rafraichir_indicateurs_reglementaires" in contenu:
    print("⏭️  PATCH (fonction rafraichissement) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (fonction rafraichissement) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (fonction rafraichissement) : ajoutee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
