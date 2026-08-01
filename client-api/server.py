import os
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
import requests
import json

app = Flask(__name__)

firebase_admin.initialize_app()
db = firestore.client()

GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzHDlqaGbnzMlmTYTY1IN8UJU19bHbqUomrRPhO8QrfTx4S-yW7Ug82dJch5-QCDdxK6g/exec"

ALLOWED_ORIGIN_SUFFIXES = [
    "https://www.comprendre-mon-energie.fr",
    "https://espace-client-217943559750.europe-west1.run.app",
    "https://espace-client.comprendre-mon-energie.fr",
    ".cloudshell.dev",
    "http://localhost:3000",
]


def _origine_autorisee(origin):
    if not origin:
        return False
    return any(
        origin == s or origin.endswith(s) for s in ALLOWED_ORIGIN_SUFFIXES
    )


def _cors(response):
    origin = request.headers.get("Origin", "")
    if _origine_autorisee(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
    response.headers["Vary"] = "Origin"
    return response


def verifier_token(req):
    auth_header = req.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.replace('Bearer ', '')
    try:
        decoded = auth.verify_id_token(token)
        return decoded['uid']
    except Exception:
        return None


def verifier_admin(uid):
    if not uid:
        return False
    try:
        doc = db.collection('users').document(uid).get()
        if not doc.exists:
            return False
        return doc.to_dict().get('role') == 'admin'
    except Exception:
        return False


def notifier_gas(uid, lead_data):
    try:
        profil_doc = db.collection('users').document(uid).get()
        profil = profil_doc.to_dict() if profil_doc.exists else {}

        payload = {
            'tool': lead_data.get('tool', ''),
            'prenom': profil.get('prenom', ''),
            'nom': profil.get('nom', ''),
            'email': profil.get('email', ''),
            'telephone': profil.get('telephone', ''),
            'montant_estime': lead_data.get('montant_estime', 0),
            'details': lead_data.get('details', {}),
            'owner_uid': uid,
        }
        requests.get(
            GAS_WEBHOOK_URL,
            params={'payload': json.dumps(payload, ensure_ascii=False)},
            timeout=15
        )
    except Exception as e:
        print(f"notifier_gas error: {e}")


@app.route('/', methods=['GET'])
def health():
    return jsonify({"service": "CME Client API", "status": "ok"}), 200


@app.route('/auth/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200
    data = request.get_json(silent=True) or {}
    email = data.get('email', '')
    password = data.get('password', '')
    nom = data.get('nom', '')
    prenom = data.get('prenom', '')
    telephone = data.get('telephone', '')

    if not email or not password:
        return _cors(jsonify({"error": "Email et mot de passe requis"})), 400

    try:
        user = auth.create_user(email=email, password=password)
        db.collection('users').document(user.uid).set({
            'email': email, 'nom': nom, 'prenom': prenom,
            'telephone': telephone, 'role': 'client',
            'date_creation': firestore.SERVER_TIMESTAMP
        })
        return _cors(jsonify({"status": "ok", "uid": user.uid})), 201
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 400


@app.route('/users/me', methods=['GET', 'PATCH', 'DELETE', 'OPTIONS'])
def user_me():
    """GET : recupere le profil du compte connecte.
    PATCH : met a jour les infos personnelles et/ou le(s) fournisseur(s).
    DELETE : supprime definitivement le compte et toutes ses donnees
    (conforme a l'obligation Google Play / Apple sur les apps avec creation
    de compte). Ne necessite pas de re-authentification recente : le SDK
    Admin agit avec les pleins pouvoirs cote serveur."""
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200

    uid = verifier_token(request)
    if not uid:
        return _cors(jsonify({"error": "Non authentifie"})), 401

    user_ref = db.collection('users').document(uid)

    if request.method == 'GET':
        doc = user_ref.get()
        if not doc.exists:
            return _cors(jsonify({"error": "Profil introuvable"})), 404
        return _cors(jsonify(doc.to_dict())), 200

    if request.method == 'DELETE':
        try:
            # Supprimer tous les leads/dossiers de l'utilisateur
            leads_ref = user_ref.collection('leads')
            for doc in leads_ref.stream():
                doc.reference.delete()

            # Supprimer le document profil
            user_ref.delete()

            # Supprimer le compte d'authentification Firebase lui-meme
            auth.delete_user(uid)

            return _cors(jsonify({"status": "ok"})), 200
        except Exception as e:
            return _cors(jsonify({"error": str(e)})), 500

    data = request.get_json(silent=True) or {}
    champs_autorises = ['nom', 'prenom', 'telephone', 'adresse_postale', 'fournisseurs']
    maj = {}
    for champ in champs_autorises:
        if champ in data:
            maj[champ] = data[champ]

    if not maj:
        return _cors(jsonify({"error": "Aucun champ valide a mettre a jour"})), 400

    try:
        user_ref.update(maj)
        return _cors(jsonify({"status": "ok"})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500


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
        return _cors(jsonify({"error": str(e)})), 500


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
        return _cors(jsonify({"error": str(e)})), 500


@app.route('/leads', methods=['GET', 'POST', 'OPTIONS'])
def leads():
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200

    uid = verifier_token(request)
    if not uid:
        return _cors(jsonify({"error": "Non authentifie"})), 401

    if request.method == 'GET':
        docs = db.collection('users').document(uid).collection('leads').stream()
        result = [{**d.to_dict(), 'id': d.id} for d in docs]
        return _cors(jsonify({"leads": result})), 200

    data = request.get_json(silent=True) or {}
    lead_ref = db.collection('users').document(uid).collection('leads').document()
    lead_data = {
        'tool': data.get('tool', ''),
        'statut': 'nouveau',
        'source_post_id': data.get('source_post_id', ''),
        'montant_estime': data.get('montant_estime', 0),
        'economie_estimee': data.get('economie_estimee', 0),
        'details': data.get('details', {}),
        'derniere_maj': firestore.SERVER_TIMESTAMP
    }
    lead_ref.set(lead_data)

    notifier_gas(uid, lead_data)

    return _cors(jsonify({"status": "ok", "lead_id": lead_ref.id})), 201


@app.route('/admin/leads', methods=['GET', 'OPTIONS'])
def admin_leads():
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200

    uid = verifier_token(request)
    if not uid:
        return _cors(jsonify({"error": "Non authentifie"})), 401
    if not verifier_admin(uid):
        return _cors(jsonify({"error": "Acces reserve aux administrateurs"})), 403

    try:
        docs = db.collection_group('leads').stream()
        result = []
        for d in docs:
            lead_data = d.to_dict()
            owner_uid = d.reference.parent.parent.id
            lead_data['id'] = d.id
            lead_data['owner_uid'] = owner_uid
            result.append(lead_data)
        return _cors(jsonify({"leads": result, "total": len(result)})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500


@app.route('/admin/users', methods=['GET', 'OPTIONS'])
def admin_users():
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200

    uid = verifier_token(request)
    if not uid:
        return _cors(jsonify({"error": "Non authentifie"})), 401
    if not verifier_admin(uid):
        return _cors(jsonify({"error": "Acces reserve aux administrateurs"})), 403

    try:
        docs = db.collection('users').stream()
        result = [{**d.to_dict(), 'uid': d.id} for d in docs]
        return _cors(jsonify({"users": result})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500


def envoyer_notification_utilisateur(uid, titre, corps, payload_data=None):
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
        pass


STATUT_LABELS_NOTIF = {
    'nouveau': "a ete remis en attente",
    'en_cours': "est maintenant en cours de traitement",
    'documents_manquants': "necessite des documents supplementaires",
    'traite': "a ete traite",
    'abandonne': "a ete cloture",
}

TOOL_LABELS_NOTIF = {
    'solaire': "Solaire",
    'comparateur-energie': "Comparateur Énergie",
    'aides-renovation': "Aides Rénovation",
    'rendez-vous-expert': "Rendez-vous expert",
}


@app.route('/admin/leads/<lead_owner_uid>/<lead_id>/status', methods=['PATCH', 'OPTIONS'])
def admin_update_lead_status(lead_owner_uid, lead_id):
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200

    uid = verifier_token(request)
    if not uid:
        return _cors(jsonify({"error": "Non authentifie"})), 401
    if not verifier_admin(uid):
        return _cors(jsonify({"error": "Acces reserve aux administrateurs"})), 403

    data = request.get_json(silent=True) or {}
    nouveau_statut = data.get('statut', '')
    statuts_valides = ['nouveau', 'en_cours', 'documents_manquants', 'traite', 'abandonne']
    if nouveau_statut not in statuts_valides:
        return _cors(jsonify({"error": "Statut invalide"})), 400

    try:
        lead_ref = db.collection('users').document(lead_owner_uid).collection('leads').document(lead_id)
        lead_avant = lead_ref.get()
        outil = lead_avant.to_dict().get('tool', '') if lead_avant.exists else ''
        outil_libelle = TOOL_LABELS_NOTIF.get(outil, "")
        lead_ref.update({
            'statut': nouveau_statut,
            'derniere_maj': firestore.SERVER_TIMESTAMP
        })
        libelle = STATUT_LABELS_NOTIF.get(nouveau_statut, "a ete mis a jour")
        prefixe = f"Votre dossier {outil_libelle}" if outil_libelle else "Votre dossier"
        envoyer_notification_utilisateur(
            lead_owner_uid,
            "Mise a jour de votre dossier",
            f"{prefixe} {libelle}.",
            {
                "type": "statut_dossier",
                "lead_id": lead_id,
                "statut": nouveau_statut,
                "tool": outil,
                "tool_libelle": outil_libelle
            }
        )
        return _cors(jsonify({"status": "ok"})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500


@app.route('/notifications', methods=['GET', 'OPTIONS'])
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
