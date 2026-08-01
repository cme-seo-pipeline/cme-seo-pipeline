FICHIER = "client-api/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = """    try:
        user_ref = db.collection('users').document(uid)
        user_ref.update({
            'expo_push_tokens': firestore.ArrayUnion([jeton])
        })
        return _cors(jsonify({"status": "ok"})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500"""

nouvelle_route = ancre + '''


BROADCAST_API_KEY = os.environ.get('BROADCAST_API_KEY', '')


@app.route('/notifications/broadcast', methods=['POST'])
def notifications_broadcast():
    """Envoie une notification push groupee a tous les utilisateurs ayant
    un jeton enregistre. Protege par une cle partagee (pas d'authentification
    utilisateur classique : appele par le pipeline, pas par un utilisateur
    connecte via l'app)."""
    cle = request.headers.get('X-Broadcast-Key', '')
    if not BROADCAST_API_KEY or cle != BROADCAST_API_KEY:
        return _cors(jsonify({"error": "Non autorise"})), 401
    data = request.get_json(silent=True) or {}
    titre = data.get('title', 'Comprendre Mon Énergie')
    corps = data.get('body', '')
    payload_data = data.get('data', {})
    if not corps:
        return _cors(jsonify({"error": "body requis"})), 400
    try:
        tous_jetons = []
        for doc in db.collection('users').stream():
            jetons = doc.to_dict().get('expo_push_tokens', [])
            tous_jetons.extend(jetons)
        tous_jetons = list(set(tous_jetons))
        if not tous_jetons:
            return _cors(jsonify({"status": "ok", "count": 0, "message": "Aucun jeton enregistre"})), 200
        envoyes = 0
        for i in range(0, len(tous_jetons), 100):
            lot = tous_jetons[i:i + 100]
            messages = [
                {"to": jeton, "title": titre, "body": corps, "data": payload_data}
                for jeton in lot
            ]
            requests.post(
                "https://exp.host/--/api/v2/push/send",
                json=messages,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=15
            )
            envoyes += len(lot)
        return _cors(jsonify({"status": "ok", "count": envoyes})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500'''

if "notifications_broadcast" in contenu:
    print("⏭️  PATCH (endpoint broadcast) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (endpoint broadcast) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route)
    print("✅ PATCH (endpoint broadcast) : /notifications/broadcast ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
