#!/usr/bin/env python3
# ============================================================
# server.py — Point d'entrée Flask pour Cloud Run
# ============================================================

import os
import threading
from flask import Flask, jsonify, request
from pipeline import run_pipeline

app = Flask(__name__)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "CME SEO AI Pipeline",
        "version": "1.0"
    })

@app.route('/run', methods=['POST'])
def trigger_pipeline():
    """
    Endpoint déclenché par Cloud Scheduler
    Body JSON optionnel : {"force": true}
    """
    data = request.get_json(silent=True) or {}
    force = data.get('force', False)

    # Lancer le pipeline en arrière-plan
    def run_async():
        try:
            run_pipeline(force=force)
        except Exception as e:
            print(f"❌ Erreur pipeline : {e}")

    thread = threading.Thread(target=run_async)
    thread.daemon = True
    thread.start()

    return jsonify({
        "status": "started",
        "force": force,
        "message": "Pipeline lancé en arrière-plan"
    }), 202

@app.route('/run-sync', methods=['POST'])
def trigger_pipeline_sync():
    """
    Endpoint synchrone — attend la fin du pipeline
    Utilisé pour les tests
    """
    data = request.get_json(silent=True) or {}
    force = data.get('force', True)

    try:
        run_pipeline(force=force)
        return jsonify({
            "status": "success",
            "message": "Pipeline terminé avec succès"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

from datetime import datetime

@app.route('/api/log-clic', methods=['POST', 'OPTIONS'])
def log_clic():
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'POST'
        return response, 200
    try:
        data = request.get_json(silent=True) or {}
        from google.cloud import bigquery
        client_bq = bigquery.Client()
        row = {
            "timestamp":   data.get("timestamp", datetime.utcnow().isoformat()),
            "tool":        data.get("tool", "comparateur-energie"),
            "offre_id":    data.get("offre_id", ""),
            "offre_nom":   data.get("offre_nom", ""),
            "energie":     data.get("energie", ""),
            "kwh":         int(data.get("kwh", 0)),
            "prix_annuel": int(data.get("prix_annuel", 0)),
            "economie":    int(data.get("economie", 0)),
            "user_agent":  str(data.get("user_agent", ""))[:120],
        }
        errors = client_bq.insert_rows_json(
            "seo-data-hub-cme.04_pipeline_seo.historique_clics_comparateur", [row]
        )
        if errors:
            return jsonify({"status": "error", "detail": str(errors)}), 500
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"log-clic error: {e}")
        return jsonify({"status": "error", "detail": str(e)}), 500


@app.route('/api/tarifs', methods=['GET'])
def get_tarifs():
    return jsonify({"status": "ok", "derniere_maj": "2026-06-29", "source": "CRE"}), 200

from datetime import datetime
