from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore

app = Flask(__name__)

# Initialisation Firebase Admin — utilise le compte de service
# via Application Default Credentials (déjà configuré sur Cloud Run)
firebase_admin.initialize_app()
db = firestore.client()


def _cors(response):
    response.headers['Access-Control-Allow-Origin'] = 'https://www.comprendre-mon-energie.fr'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PATCH'
    return response


def verifier_token(req):
    """Verifie le token Firebase envoye dans le header Authorization, retourne l'uid ou None."""
    auth_header = req.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.replace('Bearer ', '')
    try:
        decoded = auth.verify_id_token(token)
        return decoded['uid']
    except Exception:
        return None


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

    # POST : creation d'un nouveau lead lie au compte
    data = request.get_json(silent=True) or {}
    lead_ref = db.collection('users').document(uid).collection('leads').document()
    lead_ref.set({
        'tool': data.get('tool', ''),
        'statut': 'nouveau',
        'source_post_id': data.get('source_post_id', ''),
        'montant_estime': data.get('montant_estime', 0),
        'economie_estimee': data.get('economie_estimee', 0),
        'details': data.get('details', {}),
        'derniere_maj': firestore.SERVER_TIMESTAMP
    })
    return _cors(jsonify({"status": "ok", "lead_id": lead_ref.id})), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
