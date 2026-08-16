FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/api/log-clic', methods=['POST', 'OPTIONS'])"

nouvelle_route = '''@app.route('/test-donnees-officielles', methods=['POST'])
def test_donnees_officielles():
    """
    Teste rediger_article() en isolation, SANS PUBLIER, pour verifier que
    l'injection des donnees officielles (CRE/ANAH) fonctionne. Utilise un
    brief synthetique minimal.
    Body JSON optionnel : {"silo": "1. Gaz", "sous_silo": "Facture Gaz"}
    """
    from pipeline import rediger_article, init_bigquery, CONFIG
    data = request.get_json(silent=True) or {}
    silo = data.get('silo', '1. Gaz')
    sous_silo = data.get('sous_silo', 'Facture Gaz')
    brief_test = {
        "silo": silo,
        "sous_silo": sous_silo,
        "titre_seo": f"Test diagnostic {sous_silo}",
        "mot_cle_principal": "test",
        "mots_cles_secondaires": [],
        "volume_recommande": 300,
        "ton_recommande": "informatif",
        "angle_differentiant": "test technique",
        "structure": [
            {"niveau": "H1", "texte": f"Test {sous_silo}", "conseil": "bref"},
            {"niveau": "H2", "texte": "Exemple chiffre concret", "conseil": "donne un exemple de prix reel"},
        ],
        "champ_semantique": {"indispensables": [], "enrichissement": [], "a_eviter": []},
        "faq_recommandee": [],
    }
    try:
        client_bq = init_bigquery()
        contenu_html, erreur = rediger_article(brief_test, CONFIG, None, client_bq)
        if erreur:
            return jsonify({"status": "error", "erreur": erreur}), 500
        return jsonify({
            "status": "ok",
            "contient_172": "172" in contenu_html,
            "longueur": len(contenu_html),
            "extrait": contenu_html[:3000],
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "erreur": str(e)}), 500


'''

if "test_donnees_officielles" in contenu:
    print("⏭️  PATCH (endpoint test) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (endpoint test) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("✅ PATCH (endpoint test) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
