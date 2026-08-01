FICHIER = "client-api/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = """    try:
        user_ref.update(maj)
        return _cors(jsonify({"status": "ok"})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500"""

nouvelle_route = ancre + '''


@app.route('/users/me/push-token', methods=['POST', 'OPTIONS'])
def user_push_token():
    """Enregistre le jeton de notification push Expo de l'utilisateur
    connecte, pour lui permettre de recevoir des notifications ciblees
    (changement de statut de dossier) et groupees (nouveaux articles).
    Un utilisateur peut avoir plusieurs jetons (plusieurs appareils) :
    ArrayUnion evite les doublons si le meme jeton est renvoye."""
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200
    uid = verifier_token(request)
    if not uid:
        return _cors(jsonify({"error": "Non authentifie"})), 401
    data = request.get_json(silent=True) or {}
    jeton = data.get('token', '')
    if not jeton or not jeton.startswith('ExponentPushToken'):
        return _cors(jsonify({"error": "Jeton push invalide"})), 400
    try:
        user_ref = db.collection('users').document(uid)
        user_ref.update({
            'expo_push_tokens': firestore.ArrayUnion([jeton])
        })
        return _cors(jsonify({"status": "ok"})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500'''

if "user_push_token" in contenu:
    print("⏭️  PATCH (endpoint push-token) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (endpoint push-token) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route)
    print("✅ PATCH (endpoint push-token) : /users/me/push-token ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
