FICHIER = "client-api/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — envoyer_notification_utilisateur : ajout de l'ecriture
# Firestore (historique consultable dans l'app)
# ============================================================
ancien1 = '''def envoyer_notification_utilisateur(uid, titre, corps, payload_data=None):
    """Envoie une notification push ciblee a un utilisateur precis. Appel
    interne (pas besoin de cle partagee, contrairement au broadcast utilise
    par le pipeline externe)."""
    try:
        doc = db.collection('users').document(uid).get()
        if not doc.exists:
            return
        jetons = doc.to_dict().get('expo_push_tokens', [])
        if not jetons:
            return
        messages = [
            {"to": jeton, "title": titre, "body": corps, "data": payload_data or {}}
            for jeton in jetons
        ]
        requests.post(
            "https://exp.host/--/api/v2/push/send",
            json=messages,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=15
        )
    except Exception:
        pass'''

nouveau1 = '''def envoyer_notification_utilisateur(uid, titre, corps, payload_data=None):
    """Envoie une notification push ciblee a un utilisateur precis, ET
    enregistre un historique consultable dans l'app (meme si le push
    echoue/est absent, l'utilisateur pourra la voir plus tard). Appel
    interne (pas besoin de cle partagee, contrairement au broadcast utilise
    par le pipeline externe)."""
    try:
        doc = db.collection('users').document(uid).get()
        if not doc.exists:
            return
        jetons = doc.to_dict().get('expo_push_tokens', [])
        if jetons:
            messages = [
                {"to": jeton, "title": titre, "body": corps, "data": payload_data or {}}
                for jeton in jetons
            ]
            requests.post(
                "https://exp.host/--/api/v2/push/send",
                json=messages,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=15
            )
        try:
            db.collection('users').document(uid).collection('notifications').document().set({
                'titre': titre,
                'corps': corps,
                'type': (payload_data or {}).get('type', 'info'),
                'data': payload_data or {},
                'lu': False,
                'date': firestore.SERVER_TIMESTAMP
            })
        except Exception:
            pass
    except Exception:
        pass'''

if ancien1 not in contenu:
    print("❌ PATCH 1 (notif ciblee + historique) : ancre non trouvee")
elif "collection('notifications').document().set" in contenu and contenu.count("collection('notifications').document().set") >= 1 and ancien1 not in contenu:
    print("⏭️  PATCH 1 : deja present, ignore")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("✅ PATCH 1 (notif ciblee + historique) : ajoute")

# ============================================================
# PATCH 2 — /notifications/broadcast : ajout de l'ecriture Firestore
# pour chaque destinataire
# ============================================================
ancien2 = '''    try:
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

nouveau2 = '''    try:
        destinataires = []
        for doc in db.collection('users').stream():
            jetons = doc.to_dict().get('expo_push_tokens', [])
            if jetons:
                destinataires.append((doc.id, jetons))
        tous_jetons = []
        for _, jetons in destinataires:
            tous_jetons.extend(jetons)
        tous_jetons = list(set(tous_jetons))
        if not tous_jetons:
            return _cors(jsonify({"status": "ok", "count": 0, "message": "Aucun jeton enregistre"})), 200
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
        for uid, _ in destinataires:
            try:
                db.collection('users').document(uid).collection('notifications').document().set({
                    'titre': titre,
                    'corps': corps,
                    'type': payload_data.get('type', 'info'),
                    'data': payload_data,
                    'lu': False,
                    'date': firestore.SERVER_TIMESTAMP
                })
            except Exception:
                pass
        return _cors(jsonify({"status": "ok", "count": len(tous_jetons)})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500'''

if ancien2 not in contenu:
    print("❌ PATCH 2 (broadcast + historique) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (broadcast + historique) : ajoute")

# ============================================================
# PATCH 3 — Nouveaux endpoints : lecture de l'historique
# ============================================================
ancre3 = "if __name__ == '__main__':"

nouvelles_routes = '''@app.route('/notifications', methods=['GET', 'OPTIONS'])
def user_notifications():
    """Historique des notifications de l'utilisateur connecte (les plus
    recentes en premier), consultable dans l'app via l'icone cloche."""
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200
    uid = verifier_token(request)
    if not uid:
        return _cors(jsonify({"error": "Non authentifie"})), 401
    try:
        docs = (
            db.collection('users').document(uid).collection('notifications')
            .order_by('date', direction=firestore.Query.DESCENDING)
            .limit(50)
            .stream()
        )
        result = [{**d.to_dict(), 'id': d.id} for d in docs]
        return _cors(jsonify({"notifications": result})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500


@app.route('/notifications/<notif_id>/read', methods=['PATCH', 'OPTIONS'])
def marquer_notification_lue(notif_id):
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200
    uid = verifier_token(request)
    if not uid:
        return _cors(jsonify({"error": "Non authentifie"})), 401
    try:
        db.collection('users').document(uid).collection('notifications').document(notif_id).update({'lu': True})
        return _cors(jsonify({"status": "ok"})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500


'''

if "def user_notifications" in contenu:
    print("⏭️  PATCH 3 (endpoints historique) : deja present, ignore")
elif ancre3 not in contenu:
    print("❌ PATCH 3 (endpoints historique) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre3, nouvelles_routes + ancre3, 1)
    print("✅ PATCH 3 (endpoints historique) : /notifications (GET) + /notifications/<id>/read ajoutes")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
