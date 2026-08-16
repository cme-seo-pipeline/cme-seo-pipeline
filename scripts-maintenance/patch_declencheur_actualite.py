FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''@app.route('/rafraichir-indicateurs', methods=['POST'])
def rafraichir_indicateurs():
    """
    Rafraichit les indicateurs reglementaires (CRE Gaz/Elec, ANAH Aides)
    depuis les sources officielles. Concu pour tourner periodiquement via
    Cloud Scheduler (hebdomadaire), independamment du run de redaction.
    """
    from pipeline import rafraichir_indicateurs_reglementaires, init_bigquery
    try:
        client_bq = init_bigquery()
        nb = rafraichir_indicateurs_reglementaires(client_bq)
        return jsonify({"status": "ok", "lignes_inserees": nb}), 200
    except Exception as e:
        return jsonify({"status": "error", "erreur": str(e)}), 500'''

nouveau = '''@app.route('/rafraichir-indicateurs', methods=['POST'])
def rafraichir_indicateurs():
    """
    Rafraichit les indicateurs reglementaires (CRE Gaz/Elec, ANAH Aides)
    depuis les sources officielles, puis declenche le MODE ACTUALITE en
    arriere-plan (thread, comme les rattrapages Facebook/Instagram) : si un
    changement reel est detecte, publie immediatement un article dedie,
    sans attendre le run quotidien. Concu pour tourner periodiquement via
    Cloud Scheduler (hebdomadaire), independamment du run de redaction.
    """
    from pipeline import (
        rafraichir_indicateurs_reglementaires, publier_actualites_reglementaires,
        init_bigquery, CONFIG, WP_CONFIG
    )
    from datetime import datetime
    try:
        client_bq = init_bigquery()
        nb = rafraichir_indicateurs_reglementaires(client_bq)
        run_id = datetime.now().strftime("%Y%m%d_%H%M")

        def actualite_async():
            try:
                publier_actualites_reglementaires(client_bq, CONFIG, WP_CONFIG, run_id)
            except Exception as e:
                print(f"❌ Erreur Mode Actualite : {e}")

        thread = threading.Thread(target=actualite_async)
        thread.daemon = True
        thread.start()

        return jsonify({
            "status": "ok",
            "lignes_inserees": nb,
            "mode_actualite": "declenche en arriere-plan"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "erreur": str(e)}), 500'''

if "mode_actualite" in contenu:
    print("⏭️  PATCH (declenchement Mode Actualite) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (declenchement Mode Actualite) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (declenchement Mode Actualite) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
