#!/usr/bin/env python3
# ============================================================
# server.py — Point d'entrée Flask pour Cloud Run
# ============================================================
import os
import threading
from datetime import datetime
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


@app.route('/rattraper-images', methods=['POST'])
def rattraper_images():
    """
    Regenere les featured images manquantes depuis une date donnee.
    Utile apres une panne (ex : plafond de facturation OpenAI atteint)
    qui a empeche generer_featured_images() de s'executer normalement
    pendant un ou plusieurs runs, sans re-publier les articles concernes.

    Body JSON optionnel : {"depuis": "2026-07-20"}
    Par defaut, rattrape tout ce qui n'a pas d'image_id depuis 7 jours.
    """
    from pipeline import (
        generer_featured_images, init_bigquery,
        CONFIG, OPENAI_CONFIG, WP_CONFIG, PROJECT_ID, DATASET_ID
    )
    import pandas as pd

    data = request.get_json(silent=True) or {}
    depuis = data.get('depuis', '2026-07-14')

    try:
        client_bq = init_bigquery()
        query = f"""
        SELECT post_id, silo, titre, mot_cle, sous_silo_strategique
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE date_publication >= '{depuis}'
          AND (image_id IS NULL OR image_id = '')
        """
        df = client_bq.query(query).to_dataframe()

        if df.empty:
            return jsonify({
                "status": "ok",
                "message": "Aucun article a rattraper",
                "count": 0
            }), 200

        df_publications = pd.DataFrame({
            'Post_ID': df['post_id'],
            'Silo': df['silo'],
            'Titre': df['titre'],
            # Pas stocke en BQ : generer_featured_images() se rabat
            # automatiquement sur le titre pour construire le prompt DALL-E
            'Contenu_HTML': '',
            'Mot_cle': df['mot_cle'],
            'sous_silo': df['sous_silo_strategique'],
        })

        post_ids = df['post_id'].tolist()

        def run_async():
            try:
                generer_featured_images(
                    df_publications, client_bq, CONFIG, OPENAI_CONFIG, WP_CONFIG
                )
                print(f"✅ Rattrapage termine : {len(df_publications)} articles traites")
            except Exception as e:
                print(f"❌ Erreur rattrapage images : {e}")

        thread = threading.Thread(target=run_async)
        thread.daemon = True
        thread.start()

        return jsonify({
            "status": "started",
            "count": len(df_publications),
            "depuis": depuis,
            "post_ids": post_ids
        }), 202

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/rattraper-schemas', methods=['POST'])
def rattraper_schemas():
    """
    Regenere les schemas SVG manquants pour des articles precis, en
    fournissant leurs post_id explicitement (contrairement a
    /rattraper-images, pas de detection automatique possible ici : aucune
    colonne BigQuery ne trace si les schemas ont ete injectes).
    Body JSON requis : {"post_ids": [5093, 5094]}
    """
    from pipeline import (
        nettoyer_et_generer_schemas, init_bigquery,
        CONFIG, WP_CONFIG, PROJECT_ID, DATASET_ID
    )
    import pandas as pd
    data = request.get_json(silent=True) or {}
    post_ids = data.get('post_ids', [])
    if not post_ids:
        return jsonify({"status": "error", "message": "post_ids requis"}), 400
    try:
        client_bq = init_bigquery()
        post_ids_str = ",".join(str(p) for p in post_ids)
        query = f"""
        SELECT post_id, silo, titre
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE post_id IN ({post_ids_str})
        """
        df = client_bq.query(query).to_dataframe()
        if df.empty:
            return jsonify({
                "status": "ok",
                "message": "Aucun article trouve pour ces post_id",
                "count": 0
            }), 200
        df_publications = pd.DataFrame({
            'Post_ID': df['post_id'],
            'Silo': df['silo'],
            'Titre': df['titre'],
        })
        def run_async():
            try:
                nettoyer_et_generer_schemas(df_publications, WP_CONFIG, CONFIG)
                print(f"✅ Rattrapage schemas termine : {len(df_publications)} articles traites")
            except Exception as e:
                print(f"❌ Erreur rattrapage schemas : {e}")
        thread = threading.Thread(target=run_async)
        thread.daemon = True
        thread.start()
        return jsonify({
            "status": "started",
            "count": len(df_publications),
            "post_ids": df['post_id'].tolist()
        }), 202
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/rattraper-facebook', methods=['POST'])
def rattraper_facebook():
    """
    Republie sur Facebook des articles precis (post_id explicites), en
    reutilisant exactement la meme fonction que le pipeline quotidien
    (publier_tous_facebook) : meme extraction d'introduction, meme emoji
    par silo, meme filet de securite IA, meme logging BigQuery.
    Body JSON requis : {"post_ids": [4964, 4966]}
    """
    from pipeline import (
        publier_tous_facebook, init_bigquery,
        CONFIG, FACEBOOK_CONFIG, WP_CONFIG, PROJECT_ID, DATASET_ID
    )
    import pandas as pd
    import requests as req
    data = request.get_json(silent=True) or {}
    post_ids = data.get('post_ids', [])
    if not post_ids:
        return jsonify({"status": "error", "message": "post_ids requis"}), 400
    try:
        client_bq = init_bigquery()
        post_ids_str = ",".join(str(p) for p in post_ids)
        query = f"""
        SELECT post_id, silo, titre
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE post_id IN ({post_ids_str})
        """
        df = client_bq.query(query).to_dataframe()
        if df.empty:
            return jsonify({
                "status": "ok",
                "message": "Aucun article trouve pour ces post_id",
                "count": 0
            }), 200
        contenus = []
        for post_id in df['post_id']:
            try:
                r = req.get(
                    f"{WP_CONFIG['url']}/wp-json/wp/v2/posts/{post_id}",
                    timeout=15
                )
                contenus.append(r.json()['content']['rendered'] if r.status_code == 200 else '')
            except Exception:
                contenus.append('')
        df_publications = pd.DataFrame({
            'Post_ID': df['post_id'],
            'Silo': df['silo'],
            'Titre': df['titre'],
            'Contenu_HTML': contenus,
        })
        def run_async():
            try:
                publier_tous_facebook(df_publications, client_bq, CONFIG, FACEBOOK_CONFIG)
                print(f"✅ Rattrapage Facebook termine : {len(df_publications)} articles traites")
            except Exception as e:
                print(f"❌ Erreur rattrapage Facebook : {e}")
        thread = threading.Thread(target=run_async)
        thread.daemon = True
        thread.start()
        return jsonify({
            "status": "started",
            "count": len(df_publications),
            "post_ids": df['post_id'].tolist()
        }), 202
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/rattraper-instagram', methods=['POST'])
def rattraper_instagram():
    """
    Republie sur Instagram des articles precis (post_id explicites), en
    reutilisant exactement la meme fonction que le pipeline quotidien
    (publier_tous_instagram) : meme recuperation d'image, meme legende,
    meme logging BigQuery.
    Body JSON requis : {"post_ids": [4964, 4966]}
    """
    from pipeline import (
        publier_tous_instagram, init_bigquery,
        CONFIG, INSTAGRAM_CONFIG, WP_CONFIG, PROJECT_ID, DATASET_ID
    )
    import pandas as pd
    import requests as req
    data = request.get_json(silent=True) or {}
    post_ids = data.get('post_ids', [])
    if not post_ids:
        return jsonify({"status": "error", "message": "post_ids requis"}), 400
    try:
        client_bq = init_bigquery()
        post_ids_str = ",".join(str(p) for p in post_ids)
        query = f"""
        SELECT post_id, silo, titre
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE post_id IN ({post_ids_str})
        """
        df = client_bq.query(query).to_dataframe()
        if df.empty:
            return jsonify({
                "status": "ok",
                "message": "Aucun article trouve pour ces post_id",
                "count": 0
            }), 200
        contenus = []
        for post_id in df['post_id']:
            try:
                r = req.get(
                    f"{WP_CONFIG['url']}/wp-json/wp/v2/posts/{post_id}",
                    timeout=15
                )
                contenus.append(r.json()['content']['rendered'] if r.status_code == 200 else '')
            except Exception:
                contenus.append('')
        df_publications = pd.DataFrame({
            'Post_ID': df['post_id'],
            'Silo': df['silo'],
            'Titre': df['titre'],
            'Contenu_HTML': contenus,
        })
        def run_async():
            try:
                publier_tous_instagram(df_publications, client_bq, CONFIG, INSTAGRAM_CONFIG)
                print(f"✅ Rattrapage Instagram termine : {len(df_publications)} articles traites")
            except Exception as e:
                print(f"❌ Erreur rattrapage Instagram : {e}")
        thread = threading.Thread(target=run_async)
        thread.daemon = True
        thread.start()
        return jsonify({
            "status": "started",
            "count": len(df_publications),
            "post_ids": df['post_id'].tolist()
        }), 202
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/rafraichir-indicateurs', methods=['POST'])
def rafraichir_indicateurs():
    """
    Rafraichit les indicateurs reglementaires (CRE Gaz/Elec, ANAH Aides)
    depuis les sources officielles, puis declenche le MODE ACTUALITE en
    arriere-plan (thread, comme les rattrapages Facebook/Instagram) : si un
    changement reel est detecte, publie immediatement un article dedie,
    sans attendre le run quotidien. Concu pour tourner periodiquement via
    Cloud Scheduler (hebdomadaire), independamment du run de redaction.
    """
    from pipeline import (
        rafraichir_indicateurs_reglementaires, publier_actualites_reglementaires,
        init_bigquery, CONFIG, WP_CONFIG
    )
    from datetime import datetime
    try:
        client_bq = init_bigquery()
        nb = rafraichir_indicateurs_reglementaires(client_bq)
        run_id = datetime.now().strftime("%Y%m%d_%H%M")

        def actualite_async():
            try:
                publier_actualites_reglementaires(client_bq, CONFIG, WP_CONFIG, run_id)
            except Exception as e:
                print(f"❌ Erreur Mode Actualite : {e}")

        thread = threading.Thread(target=actualite_async)
        thread.daemon = True
        thread.start()

        return jsonify({
            "status": "ok",
            "lignes_inserees": nb,
            "mode_actualite": "declenche en arriere-plan"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "erreur": str(e)}), 500


@app.route('/auditer-articles', methods=['POST'])
def auditer_articles():
    """
    CHANTIER MISE A JOUR DES ARTICLES PUBLIES : audite tous les candidats
    en pertinence directe et corrige automatiquement, sans validation
    humaine, toute citation reelle devenue obsolete. Tourne en
    arriere-plan (audit de dizaines d'articles = plusieurs minutes).
    Concu pour tourner periodiquement via Cloud Scheduler (mensuel).
    """
    from pipeline import auditer_et_corriger_articles, init_bigquery, CONFIG, WP_CONFIG

    def audit_async():
        try:
            client_bq = init_bigquery()
            resultat = auditer_et_corriger_articles(client_bq, CONFIG, WP_CONFIG)
            print(f"✅ Audit articles termine : {resultat}")
        except Exception as e:
            print(f"❌ Erreur audit articles : {e}")

    thread = threading.Thread(target=audit_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "audit": "declenche en arriere-plan"}), 200


@app.route('/synchroniser-leads-app', methods=['POST'])
def synchroniser_leads_app():
    """
    CHANTIER SOUVERAINETE SHELL : synchronise les leads des utilisateurs
    connectes a l'app (Firestore) vers BigQuery (leads_app_authentifies).
    """
    from pipeline import rafraichir_leads_app_authentifies, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = rafraichir_leads_app_authentifies(client_bq)
            print(f"✅ Sync leads app terminee : {nb} leads")
        except Exception as e:
            print(f"❌ Erreur sync leads app : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "sync": "declenche en arriere-plan"}), 200


@app.route('/rafraichir-mapping-urls', methods=['POST'])
def rafraichir_mapping_urls():
    """
    CHANTIER GROWTH ENGINEERING : reconstruit la correspondance URL -> post_id
    WordPress (table 02_cleaned.wp_url_mapping), utilisee par la vue
    seo_opportunities pour joindre GSC/GA4 sur un identifiant stable plutot
    que sur l'URL brute. Concu pour tourner quotidiennement, avant le run
    principal.
    """
    from pipeline import rafraichir_wp_url_mapping, init_bigquery

    def refresh_async():
        try:
            client_bq = init_bigquery()
            nb = rafraichir_wp_url_mapping(client_bq)
            print(f"✅ Mapping URL->post_id termine : {nb} correspondances")
        except Exception as e:
            print(f"❌ Erreur mapping URL->post_id : {e}")

    thread = threading.Thread(target=refresh_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "mapping": "declenche en arriere-plan"}), 200


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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
