#!/usr/bin/env python3
# ============================================================
# server.py — Point d'entrée Flask pour Cloud Run
# ============================================================
import os
import threading
import requests
from datetime import datetime
from flask import Flask, jsonify, request
from pipeline import run_pipeline

app = Flask(__name__)


CHEMINS_PUBLICS = {'/', '/orcaas', '/orcaas-dashboard-data', '/orcaas-chat'}
ORCAAS_ACTION_SECRET = os.environ.get("ORCAAS_ACTION_SECRET", "")


@app.before_request
def verifier_secret_action():
    """Protege tous les endpoints d'action (sync, audit, deploiement WP,
    agent ORCAAS ecriture) par un secret partage -- necessaire car le
    service est desormais public (plus de proxy Cloud Shell requis pour
    les pages /orcaas). Les pages publiques (chat, dashboard, healthcheck)
    restent librement accessibles."""
    if request.path in CHEMINS_PUBLICS:
        return None
    if request.method == 'OPTIONS':
        return None
    secret_recu = request.headers.get('X-Orcaas-Secret', '')
    if not ORCAAS_ACTION_SECRET or secret_recu != ORCAAS_ACTION_SECRET:
        return jsonify({"erreur": "Non autorise -- en-tete X-Orcaas-Secret requis"}), 401
    return None


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


@app.route('/wp-deploy', methods=['POST'])
def wp_deploy():
    """
    Ecrit un fichier directement sur le serveur o2switch via SFTP (meme
    canal SSH que wp-shell, IP fixe Cloud Run). Attend un JSON :
    {"chemin_distant": "...", "contenu": "..."}
    Temporaire, chantier G.1 (deploiement direct des plugins patches).
    """
    import io
    import paramiko

    data = request.get_json(silent=True) or {}
    chemin_distant = data.get('chemin_distant', '')
    contenu_fichier = data.get('contenu', '')

    if not chemin_distant or not contenu_fichier:
        return jsonify({"status": "erreur", "detail": "chemin_distant et contenu requis"}), 400

    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname="109.234.167.170", port=22, username="jolu5920",
                        pkey=pkey, timeout=15)

        sftp = client.open_sftp()
        with sftp.open(chemin_distant, 'w') as f:
            f.write(contenu_fichier)
        sftp.close()
        client.close()

        return jsonify({"status": "ok", "chemin": chemin_distant,
                         "taille": len(contenu_fichier)}), 200
    except Exception as e:
        return jsonify({"status": "erreur", "detail": str(e)}), 500


@app.route('/wp-shell', methods=['GET'])
def wp_shell():
    """
    Endpoint generique de diagnostic/commande WP-CLI via SSH (Cloud Run,
    IP fixe). Parametre 'cmd' = commande WP-CLI a executer (sans le 'wp'
    initial ni --path, ajoutes automatiquement). Temporaire, pour le
    chantier G.1 (deploiement des plugins).
    """
    import io
    import paramiko

    commande = request.args.get('cmd', 'plugin list --format=csv --fields=name,status')

    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname="109.234.167.170", port=22, username="jolu5920",
                        pkey=pkey, timeout=15)

        wp_path = "/home/jolu5920/public_html/comprendre-mon-energie.com"
        stdin, stdout, stderr = client.exec_command(f'wp --path="{wp_path}" {commande}')
        resultat = stdout.read().decode()
        erreur = stderr.read().decode()
        client.close()

        return jsonify({"status": "ok", "resultat": resultat, "erreur": erreur or None}), 200
    except Exception as e:
        return jsonify({"status": "erreur", "detail": str(e)}), 500


@app.route('/test-ssh-o2switch', methods=['GET'])
def test_ssh_o2switch():
    """
    VALIDATION CHANTIER RESEAU : confirme qu'une connexion SSH reelle vers
    o2switch fonctionne DEPUIS Cloud Run (pas seulement depuis Cloud Shell),
    via le connecteur VPC + Cloud NAT + IP fixe. Endpoint temporaire de
    diagnostic (pas destine a rester en production).
    """
    import io
    import paramiko

    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        if not cle or not passphrase:
            raise Exception("O2SWITCH_SSH_PRIVATE_KEY ou O2SWITCH_SSH_PASSPHRASE absent des variables d'environnement")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname="109.234.167.170", port=22, username="jolu5920",
                        pkey=pkey, timeout=15)

        wp_path = "/home/jolu5920/public_html/comprendre-mon-energie.com"
        stdin, stdout, stderr = client.exec_command(f'wp --path="{wp_path}" core version')
        resultat = stdout.read().decode().strip()
        erreur = stderr.read().decode().strip()
        client.close()

        return jsonify({"status": "ok", "wp_version": resultat, "erreur": erreur or None}), 200
    except Exception as e:
        return jsonify({"status": "erreur", "detail": str(e)}), 500


@app.route('/test-ip-sortante', methods=['GET'])
def test_ip_sortante():
    """
    VERIFICATION CHANTIER RESEAU : confirme l'IP sortante reelle utilisee
    par Cloud Run, pour valider le connecteur VPC + Cloud NAT. Endpoint
    temporaire de diagnostic (pas destine a rester en production).
    """
    try:
        r = requests.get("https://ifconfig.me", timeout=10)
        return jsonify({"ip_sortante": r.text.strip()}), 200
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


@app.route('/synchroniser-clarity-par-page', methods=['POST'])
def synchroniser_clarity_par_page():
    """CHANTIER G.2 : synchronise les insights Clarity PAR PAGE vers BigQuery."""
    from pipeline import rafraichir_clarity_par_page, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = rafraichir_clarity_par_page(client_bq)
            print(f"✅ Sync Clarity par page terminee : {nb} lignes")
        except Exception as e:
            print(f"❌ Erreur sync Clarity par page : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "sync": "declenche en arriere-plan"}), 200


@app.route('/synchroniser-rankmath', methods=['POST'])
def synchroniser_rankmath_endpoint():
    """CHANTIER G.3 : synchronise les donnees SEO RankMath vers BigQuery."""
    from pipeline import synchroniser_rankmath, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = synchroniser_rankmath(client_bq)
            print(f"✅ Sync RankMath terminee : {nb} lignes")
        except Exception as e:
            print(f"❌ Erreur sync RankMath : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "sync": "declenche en arriere-plan"}), 200


@app.route('/agent-orcaas-seo-technique', methods=['POST'])
def agent_orcaas_seo_technique_endpoint():
    """AGENT ORCAAS V1 : corrige titres/meta manquants ou dupliques,
    controle total, genere un brief par intervention."""
    from pipeline import agent_orcaas_seo_technique, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = agent_orcaas_seo_technique(client_bq)
            print(f"✅ Agent ORCAAS termine : {nb} corrections")
        except Exception as e:
            print(f"❌ Erreur agent ORCAAS : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "agent": "declenche en arriere-plan"}), 200


@app.route('/agent-orcaas-evaluer', methods=['POST'])
def agent_orcaas_evaluer_endpoint():
    """AGENT ORCAAS : evalue l'impact reel des corrections passees (GSC avant/apres)."""
    from pipeline import agent_orcaas_evaluer_impact, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = agent_orcaas_evaluer_impact(client_bq)
            print(f"✅ Evaluation ORCAAS terminee : {nb} evaluations")
        except Exception as e:
            print(f"❌ Erreur evaluation ORCAAS : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "evaluation": "declenchee en arriere-plan"}), 200


@app.route('/orcaas-chat', methods=['POST'])
def orcaas_chat_endpoint():
    """AGENT ORCAAS : repond a une question en s'appuyant sur le contexte reel du projet."""
    from pipeline import agent_orcaas_chat, init_bigquery

    data = request.get_json(silent=True) or {}
    question = data.get('message', '').strip()
    if not question:
        return jsonify({"erreur": "message requis"}), 400

    try:
        client_bq = init_bigquery()
        reponse = agent_orcaas_chat(question, client_bq)
        return jsonify({"reponse": reponse}), 200
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


ORCAAS_APP_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ORCAAS</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 0; height: 100vh; display: flex; flex-direction: column; }
  header { background: #1e3a5f; padding: 16px 24px; display: flex; align-items: center; gap: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.3); }
  header h1 { margin: 0; font-size: 20px; }
  header .badge { background: #2563eb; padding: 4px 10px; border-radius: 12px; font-size: 12px; }
  nav { display: flex; gap: 4px; margin-left: 24px; }
  nav button { background: transparent; border: none; color: #94a3b8; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; }
  nav button.actif { background: #2563eb; color: white; }

  #vue-chat { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  #chat { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
  .msg { max-width: 70%; padding: 12px 16px; border-radius: 12px; line-height: 1.5; white-space: pre-wrap; }
  .msg.user { align-self: flex-end; background: #2563eb; color: white; }
  .msg.orcaas { align-self: flex-start; background: #1e293b; border: 1px solid #334155; }
  .msg.loading { align-self: flex-start; background: #1e293b; border: 1px solid #334155; opacity: .6; }
  #input-zone { padding: 16px 24px; display: flex; gap: 12px; border-top: 1px solid #334155; }
  #question { flex: 1; padding: 12px 16px; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: #e2e8f0; font-size: 15px; }
  #question:focus { outline: none; border-color: #2563eb; }
  #send { padding: 12px 24px; border-radius: 8px; border: none; background: #2563eb; color: white; font-weight: 600; cursor: pointer; }
  #send:hover { background: #1d4ed8; }
  #send:disabled { opacity: .5; cursor: not-allowed; }

  #vue-dashboard { flex: 1; overflow-y: auto; padding: 24px; display: none; }
  #vue-dashboard.actif { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 24px; max-width: 1400px; margin: 0 auto; }
  .carte { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; }
  .carte h2 { margin: 0 0 16px 0; font-size: 15px; color: #93c5fd; font-weight: 600; }
  .vide { color: #64748b; font-size: 14px; text-align: center; padding: 40px 0; }
</style>
</head>
<body>
<header>
  <h1>ORCAAS</h1>
  <span class="badge">SEO Specialiste IA</span>
  <nav>
    <button id="onglet-chat" class="actif" onclick="afficherOnglet('chat')">Chat</button>
    <button id="onglet-dashboard" onclick="afficherOnglet('dashboard')">Dashboard</button>
  </nav>
</header>

<div id="vue-chat">
  <div id="chat">
    <div class="msg orcaas">Bonjour, je suis ORCAAS. Posez-moi une question sur l'etat du site, mes dernieres actions, ou les resultats obtenus.</div>
  </div>
  <div id="input-zone">
    <input type="text" id="question" placeholder="Posez votre question..." autocomplete="off" />
    <button id="send">Envoyer</button>
  </div>
</div>

<div id="vue-dashboard">
  <div class="carte">
    <h2>Top pages par impressions (GSC, 30 derniers jours)</h2>
    <canvas id="chartPages"></canvas>
  </div>
  <div class="carte">
    <h2>Corrections ORCAAS par type de probleme</h2>
    <canvas id="chartBriefs"></canvas>
  </div>
  <div class="carte">
    <h2>Evaluations d'impact par verdict</h2>
    <canvas id="chartEvals"></canvas>
  </div>
  <div class="carte">
    <h2>Top 10 opportunites SEO (score)</h2>
    <canvas id="chartOpportunites"></canvas>
  </div>
  <div class="carte">
    <h2>Couverture RankMath (mot-cle cible)</h2>
    <canvas id="chartRankmath"></canvas>
  </div>
  <div class="carte">
    <h2>Sante technique du site (495 pages)</h2>
    <canvas id="chartAudit"></canvas>
  </div>
  <div class="carte">
    <h2>Leads par outil (tous canaux)</h2>
    <canvas id="chartLeads"></canvas>
  </div>
  <div class="carte">
    <h2>Publications par silo</h2>
    <canvas id="chartPublications"></canvas>
  </div>
</div>

<script>
function afficherOnglet(nom) {
  document.getElementById('onglet-chat').classList.toggle('actif', nom === 'chat');
  document.getElementById('onglet-dashboard').classList.toggle('actif', nom === 'dashboard');
  document.getElementById('vue-chat').style.display = nom === 'chat' ? 'flex' : 'none';
  document.getElementById('vue-dashboard').classList.toggle('actif', nom === 'dashboard');
  if (nom === 'dashboard' && !window.dashboardCharge) {
    chargerDashboard();
  }
}

const chat = document.getElementById('chat');
const question = document.getElementById('question');
const send = document.getElementById('send');

function ajouterMessage(texte, classe) {
  const div = document.createElement('div');
  div.className = 'msg ' + classe;
  div.textContent = texte;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

async function envoyer() {
  const q = question.value.trim();
  if (!q) return;
  ajouterMessage(q, 'user');
  question.value = '';
  send.disabled = true;
  const loading = ajouterMessage('ORCAAS reflechit...', 'loading');
  try {
    const res = await fetch('/orcaas-chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: q})
    });
    const data = await res.json();
    loading.remove();
    ajouterMessage(data.reponse || data.erreur || 'Erreur inconnue', 'orcaas');
  } catch (e) {
    loading.remove();
    ajouterMessage('Erreur de connexion : ' + e.message, 'orcaas');
  }
  send.disabled = false;
  question.focus();
}

send.addEventListener('click', envoyer);
question.addEventListener('keypress', function(e) {
  if (e.key === 'Enter') envoyer();
});

async function chargerDashboard() {
  window.dashboardCharge = true;
  try {
    const res = await fetch('/orcaas-dashboard-data');
    const donnees = await res.json();
    dessinerGraphiques(donnees);
  } catch (e) {
    document.getElementById('vue-dashboard').innerHTML = '<div class="vide">Erreur de chargement : ' + e.message + '</div>';
  }
}

function dessinerGraphiques(DONNEES) {
  Chart.defaults.color = '#94a3b8';
  Chart.defaults.borderColor = '#334155';

  if (DONNEES.top_pages && DONNEES.top_pages.length > 0) {
    new Chart(document.getElementById('chartPages'), {
      type: 'bar',
      data: {
        labels: DONNEES.top_pages.map(p => p.url.length > 30 ? p.url.slice(0,30)+'...' : p.url),
        datasets: [
          { label: 'Impressions', data: DONNEES.top_pages.map(p => p.impressions), backgroundColor: '#2563eb' },
          { label: 'Clics', data: DONNEES.top_pages.map(p => p.clics), backgroundColor: '#f59e0b' }
        ]
      },
      options: { indexAxis: 'y', responsive: true, plugins: { legend: { position: 'top' } } }
    });
  } else {
    document.getElementById('chartPages').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.briefs_par_probleme && DONNEES.briefs_par_probleme.length > 0) {
    new Chart(document.getElementById('chartBriefs'), {
      type: 'doughnut',
      data: {
        labels: DONNEES.briefs_par_probleme.map(b => b.probleme),
        datasets: [{ data: DONNEES.briefs_par_probleme.map(b => b.nb), backgroundColor: ['#2563eb','#f59e0b','#16a34a','#dc2626','#7e22ce'] }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
  } else {
    document.getElementById('chartBriefs').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.evaluations_par_verdict && DONNEES.evaluations_par_verdict.length > 0) {
    new Chart(document.getElementById('chartEvals'), {
      type: 'doughnut',
      data: {
        labels: DONNEES.evaluations_par_verdict.map(v => v.verdict),
        datasets: [{ data: DONNEES.evaluations_par_verdict.map(v => v.nb), backgroundColor: ['#64748b','#16a34a','#dc2626','#2563eb'] }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
  } else {
    document.getElementById('chartEvals').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.opportunites && DONNEES.opportunites.length > 0) {
    new Chart(document.getElementById('chartOpportunites'), {
      type: 'bar',
      data: {
        labels: DONNEES.opportunites.map(o => o.url.length > 25 ? o.url.slice(0,25)+'...' : o.url),
        datasets: [{ label: 'Score opportunite', data: DONNEES.opportunites.map(o => o.score), backgroundColor: '#7e22ce' }]
      },
      options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } } }
    });
  } else {
    document.getElementById('chartOpportunites').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.rankmath_couverture) {
    const rm = DONNEES.rankmath_couverture;
    if ((rm.avec_mot_cle + rm.sans_mot_cle) > 0) {
      new Chart(document.getElementById('chartRankmath'), {
        type: 'doughnut',
        data: {
          labels: ['Avec mot-cle cible', 'Sans mot-cle cible'],
          datasets: [{ data: [rm.avec_mot_cle, rm.sans_mot_cle], backgroundColor: ['#16a34a', '#dc2626'] }]
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
      });
    } else {
      document.getElementById('chartRankmath').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
    }
  }

  if (DONNEES.audit_technique && DONNEES.audit_technique.length > 0) {
    new Chart(document.getElementById('chartAudit'), {
      type: 'doughnut',
      data: {
        labels: DONNEES.audit_technique.map(a => a.categorie),
        datasets: [{ data: DONNEES.audit_technique.map(a => a.nb), backgroundColor: ['#16a34a','#f59e0b','#dc2626','#64748b'] }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
  } else {
    document.getElementById('chartAudit').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.leads_par_outil && DONNEES.leads_par_outil.length > 0) {
    new Chart(document.getElementById('chartLeads'), {
      type: 'bar',
      data: {
        labels: DONNEES.leads_par_outil.map(l => l.outil),
        datasets: [{ label: 'Leads', data: DONNEES.leads_par_outil.map(l => l.nb), backgroundColor: '#2563eb' }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });
  } else {
    document.getElementById('chartLeads').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.publications_par_silo && DONNEES.publications_par_silo.length > 0) {
    new Chart(document.getElementById('chartPublications'), {
      type: 'bar',
      data: {
        labels: DONNEES.publications_par_silo.map(p => p.silo),
        datasets: [{ label: 'Articles publies', data: DONNEES.publications_par_silo.map(p => p.nb), backgroundColor: '#f59e0b' }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });
  } else {
    document.getElementById('chartPublications').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }
}
</script>
</body>
</html>"""


@app.route('/orcaas-dashboard-data', methods=['GET'])
def orcaas_dashboard_data_endpoint():
    """Donnees JSON du dashboard (page publique, appelee en arriere-plan par /orcaas)."""
    from pipeline import agent_orcaas_donnees_dashboard, init_bigquery
    try:
        client_bq = init_bigquery()
        donnees = agent_orcaas_donnees_dashboard(client_bq)
        return jsonify(donnees), 200
    except Exception as e:
        return jsonify({"top_pages": [], "briefs_par_probleme": [], "evaluations_par_verdict": [], "erreur": str(e)}), 500


@app.route('/orcaas', methods=['GET'])
def orcaas_chat_page():
    """Application unique ORCAAS : onglets Chat + Dashboard."""
    return ORCAAS_APP_HTML


@app.route('/auditer-site-technique', methods=['POST'])
def auditer_site_technique_endpoint():
    """CHANTIER G.3 : lance l'audit technique complet du site (robot maison)."""
    from pipeline import auditer_site_technique, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = auditer_site_technique(client_bq)
            print(f"✅ Audit technique termine : {nb} pages")
        except Exception as e:
            print(f"❌ Erreur audit technique : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "audit": "declenche en arriere-plan"}), 200


@app.route('/synchroniser-clarity', methods=['POST'])
def synchroniser_clarity():
    """
    CHANTIER SOUVERAINETE SHELL : synchronise les insights Microsoft
    Clarity vers BigQuery (clarity_insights_quotidien).
    """
    from pipeline import rafraichir_clarity_insights, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = rafraichir_clarity_insights(client_bq)
            print(f"✅ Sync Clarity terminee : {nb} metriques")
        except Exception as e:
            print(f"❌ Erreur sync Clarity : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "sync": "declenche en arriere-plan"}), 200


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
