from flask import Flask, request, jsonify
from google.cloud import bigquery
from datetime import datetime
import json

app = Flask(__name__)

CORS_ORIGIN = 'https://www.comprendre-mon-energie.fr'


def _cors(response):
    response.headers['Access-Control-Allow-Origin'] = CORS_ORIGIN
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'POST'
    return response


@app.route('/', methods=['GET'])
def health():
    return jsonify({"service": "CME Tracking API", "status": "ok"}), 200


@app.route('/api/log-clic', methods=['POST', 'OPTIONS'])
def log_clic():
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200
    try:
        data = request.get_json(silent=True) or {}
        client_bq = bigquery.Client()
        row = {
            "timestamp":   data.get("timestamp", datetime.utcnow().isoformat()),
            "tool":        str(data.get("tool", "comparateur-energie"))[:50],
            "offre_id":    str(data.get("offre_id", ""))[:50],
            "offre_nom":   str(data.get("offre_nom", ""))[:100],
            "energie":     str(data.get("energie", ""))[:20],
            "kwh":         int(data.get("kwh", 0)),
            "prix_annuel": int(data.get("prix_annuel", 0)),
            "economie":    int(data.get("economie", 0)),
            "user_agent":  str(data.get("user_agent", ""))[:120],
        }
        errors = client_bq.insert_rows_json(
            "seo-data-hub-cme.04_pipeline_seo.historique_clics_comparateur", [row]
        )
        resp = jsonify({"status": "error", "detail": str(errors)} if errors else {"status": "ok"})
        return _cors(resp), (500 if errors else 200)
    except Exception as e:
        print(f"log-clic error: {e}")
        return _cors(jsonify({"status": "error", "detail": str(e)})), 500


@app.route('/api/log-lead', methods=['POST', 'OPTIONS'])
def log_lead():
    """
    Enregistre un lead CONVERTI (avec coordonnees) pour l'un des 3
    simulateurs (solaire / comparateur-energie / aides-renovation)
    dans une table unifiee, distincte des clics anonymes.
    Appele server-side depuis les handlers PHP WordPress (pas de JS
    direct), donc pas de risque CORS ni d'exposition de credentials.
    """
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200
    try:
        data = request.get_json(silent=True) or {}
        client_bq = bigquery.Client()

        # Champs communs aux 3 outils
        row = {
            "timestamp":         data.get("timestamp", datetime.utcnow().isoformat()),
            "tool":              str(data.get("tool", ""))[:50],
            "prenom":            str(data.get("prenom", ""))[:100],
            "nom":                str(data.get("nom", ""))[:100],
            "email":             str(data.get("email", ""))[:150],
            "telephone":         str(data.get("telephone", ""))[:30],
            "adresse":           str(data.get("adresse", ""))[:250],
            "code_postal":       str(data.get("code_postal", ""))[:10],
            "montant_estime":    int(data.get("montant_estime", 0) or 0),
            "economie_estimee":  int(data.get("economie_estimee", 0) or 0),
            # Tout ce qui est specifique a l'outil (profil, offre, ROI...)
            # est serialise en JSON pour ne pas multiplier les colonnes.
            "details":           json.dumps(data.get("details", {}), ensure_ascii=False)[:2000],
            "user_agent":        str(data.get("user_agent", ""))[:120],
            "source_page":       str(data.get("source_page", ""))[:250],
            "source_post_id":    str(data.get("source_post_id", ""))[:20],
        }
        errors = client_bq.insert_rows_json(
            "seo-data-hub-cme.04_pipeline_seo.leads_convertis", [row]
        )
        resp = jsonify({"status": "error", "detail": str(errors)} if errors else {"status": "ok"})
        return _cors(resp), (500 if errors else 200)
    except Exception as e:
        print(f"log-lead error: {e}")
        return _cors(jsonify({"status": "error", "detail": str(e)})), 500


@app.route('/api/log-interaction', methods=['POST', 'OPTIONS'])
def log_interaction():
    """
    Journalise des evenements d'interaction fine (clics sur des zones de
    contenu dans les articles, progression/abandon du mini-formulaire)
    pour la cartographie demandee par l'operateur le 26/10/2026 -- table
    dediee interactions_contenu, distincte de leads_convertis (ce ne sont
    pas des leads, pas de coordonnees de contact ici).

    Recoit un LOT d'evenements en une seule requete (tableau JSON), pas un
    evenement a la fois -- le JS cote navigateur bufferise et envoie en
    sendBeacon au moment ou la page se cache/se quitte (voir
    cme-tracking-conversion.php et cme-cta-progressifs.php), pour limiter
    le nombre de requetes a un volume raisonnable par visite.

    Meme contrat que /api/log-lead : appele server-side depuis le relais
    PHP WordPress (/wp-json/cme/v1/log-interaction), jamais directement
    depuis le JS du navigateur -- aucun risque CORS.
    """
    if request.method == 'OPTIONS':
        return _cors(jsonify({})), 200
    try:
        data = request.get_json(silent=True)
        evenements = data if isinstance(data, list) else [data] if data else []
        if not evenements:
            return _cors(jsonify({"status": "ok", "inserted": 0})), 200

        client_bq = bigquery.Client()
        lignes = []
        for e in evenements:
            if not isinstance(e, dict):
                continue
            lignes.append({
                "timestamp":        e.get("timestamp", datetime.utcnow().isoformat()),
                "type_evenement":   str(e.get("type_evenement", ""))[:30],
                "cible":            str(e.get("cible", ""))[:30],
                "section":          str(e.get("section", ""))[:150],
                "texte":            str(e.get("texte", ""))[:150],
                "position_contenu": int(e.get("position_contenu", 0) or 0),
                "etape":            str(e.get("etape", ""))[:20],
                "scroll_pct":       float(e.get("scroll_pct", 0) or 0),
                "silo":             str(e.get("silo", ""))[:50],
                "session_id":       str(e.get("session_id", ""))[:60],
                "source_page":      str(e.get("source_page", ""))[:250],
                "source_post_id":   str(e.get("source_post_id", ""))[:20],
                "user_agent":       str(e.get("user_agent", ""))[:120],
            })

        if not lignes:
            return _cors(jsonify({"status": "ok", "inserted": 0})), 200

        errors = client_bq.insert_rows_json(
            "seo-data-hub-cme.04_pipeline_seo.interactions_contenu", lignes
        )
        resp = jsonify({"status": "error", "detail": str(errors)} if errors else {"status": "ok", "inserted": len(lignes)})
        return _cors(resp), (500 if errors else 200)
    except Exception as e:
        print(f"log-interaction error: {e}")
        return _cors(jsonify({"status": "error", "detail": str(e)})), 500


@app.route('/api/tarifs', methods=['GET'])
def get_tarifs():
    resp = jsonify({"status": "ok", "derniere_maj": "2026-06-29", "source": "CRE"})
    return _cors(resp), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
