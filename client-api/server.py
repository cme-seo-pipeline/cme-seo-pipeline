from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore

app = Flask(__name__)

# Initialisation Firebase Admin — utilise le compte de service
# via Application Default Credentials (déjà configuré sur Cloud Run)
firebase_admin.initialize_app()
db = firestore.client()

# Origines autorisées : production + developpement.
ALLOWED_ORIGIN_SUFFIXES = [
    "https://www.comprendre-mon-energie.fr",
    "https://espace-client-217943559750.europe-west1.run.app",
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
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, OPTIONS"
    response.headers["Vary"] = "Origin"
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


def verifier_admin(uid):
    """Verifie que l'utilisateur a le role admin. Retourne True/False."""
    if not uid:
        return False
    try:
        doc = db.collection('users').document(uid).get()
        if not doc.exists:
            return False
        return doc.to_dict().get('role') == 'admin'
    except Exception:
        return False


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


@app.route('/admin/leads', methods=['GET', 'OPTIONS'])
def admin_leads():
    """Liste TOUS les leads de TOUS les utilisateurs (collection group query).
    Reserve aux comptes role=admin."""
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200

    uid = verifier_token(request)
    if not uid:
        return _cors(jsonify({"error": "Non authentifie"})), 401
    if not verifier_admin(uid):
        return _cors(jsonify({"error": "Acces reserve aux administrateurs"})), 403

    try:
        # Collection group query : parcourt la sous-collection "leads"
        # de TOUS les documents users/{uid}, peu importe le parent.
        docs = db.collection_group('leads').stream()
        result = []
        for d in docs:
            lead_data = d.to_dict()
            # Le parent du document (users/{uid}) donne l'uid du proprietaire
            owner_uid = d.reference.parent.parent.id
            lead_data['id'] = d.id
            lead_data['owner_uid'] = owner_uid
            result.append(lead_data)
        return _cors(jsonify({"leads": result, "total": len(result)})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500


@app.route('/admin/users', methods=['GET', 'OPTIONS'])
def admin_users():
    """Liste tous les comptes clients (pour associer nom/email aux leads
    dans l'interface admin). Reserve aux comptes role=admin."""
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


@app.route('/admin/leads/<lead_owner_uid>/<lead_id>/status', methods=['PATCH', 'OPTIONS'])
def admin_update_lead_status(lead_owner_uid, lead_id):
    """Met a jour le statut d'un lead specifique. Reserve aux admins."""
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
        lead_ref.update({
            'statut': nouveau_statut,
            'derniere_maj': firestore.SERVER_TIMESTAMP
        })
        return _cors(jsonify({"status": "ok"})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
