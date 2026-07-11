from flask import Flask, request, jsonify
from google.cloud import bigquery
from datetime import datetime

app = Flask(__name__)

@app.route('/', methods=['GET'])
def health():
    return jsonify({"service": "CME Tracking API", "status": "ok"}), 200

@app.route('/api/log-clic', methods=['POST', 'OPTIONS'])
def log_clic():
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers['Access-Control-Allow-Origin'] = 'https://www.comprendre-mon-energie.fr'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'POST'
        return response, 200
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
        response = jsonify({"status": "error", "detail": str(errors)} if errors else {"status": "ok"})
        response.headers['Access-Control-Allow-Origin'] = 'https://www.comprendre-mon-energie.fr'
        return response, (500 if errors else 200)
    except Exception as e:
        print(f"log-clic error: {e}")
        response = jsonify({"status": "error", "detail": str(e)})
        response.headers['Access-Control-Allow-Origin'] = 'https://www.comprendre-mon-energie.fr'
        return response, 500

@app.route('/api/tarifs', methods=['GET'])
def get_tarifs():
    response = jsonify({"status": "ok", "derniere_maj": "2026-06-29", "source": "CRE"})
    response.headers['Access-Control-Allow-Origin'] = 'https://www.comprendre-mon-energie.fr'
    return response, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
