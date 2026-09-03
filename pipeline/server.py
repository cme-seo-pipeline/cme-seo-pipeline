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


CHEMINS_PUBLICS = {'/', '/orcaas', '/orcaas-dashboard-data', '/orcaas-dashboard-detail', '/orcaas-chat'}
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
  .logo-icone { flex-shrink: 0; }
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

  @media (max-width: 640px) {
    header { padding: 10px 14px; flex-wrap: wrap; row-gap: 8px; }
    header h1 { font-size: 16px; }
    header .badge { font-size: 10px; padding: 3px 8px; }
    nav { margin-left: 0; width: 100%; order: 3; }
    nav button { flex: 1; padding: 10px 8px; font-size: 13px; }
    #chat { padding: 14px; gap: 12px; }
    .msg { max-width: 88%; font-size: 15px; padding: 10px 14px; }
    #input-zone { padding: 12px 14px; gap: 8px; }
    #question { font-size: 16px; padding: 10px 12px; }
    #send { padding: 10px 16px; font-size: 14px; }
    #vue-dashboard.actif { grid-template-columns: 1fr; padding: 14px; gap: 14px; }
    .carte { padding: 14px; }
    #barre-filtre { flex-wrap: wrap; padding: 12px 14px; gap: 10px; }
    #barre-filtre label { flex: 1 1 45%; min-width: 130px; }
    #barre-filtre button { flex: 1 1 100%; }
    #periode-affichee { width: 100%; margin-left: 0; text-align: center; order: 10; }
  }
  #barre-filtre { grid-column: 1 / -1; display: flex; align-items: center; gap: 12px; background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 14px 20px; }
  #barre-filtre label { font-size: 13px; color: #94a3b8; display: flex; align-items: center; gap: 6px; }
  #barre-filtre input[type=date] { background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 6px 10px; border-radius: 6px; font-size: 13px; }
  #barre-filtre button { background: #2563eb; border: none; color: white; padding: 8px 18px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; }
  #barre-filtre button:hover { background: #1d4ed8; }
  #periode-affichee { font-size: 13px; color: #64748b; margin-left: auto; }
  .carte canvas { cursor: pointer; }
  .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); z-index: 100; align-items: center; justify-content: center; padding: 20px; }
  .modal-contenu { background: #1e293b; border: 1px solid #334155; border-radius: 12px; max-width: 600px; width: 100%; max-height: 80vh; display: flex; flex-direction: column; }
  .modal-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid #334155; }
  .modal-header h3 { margin: 0; font-size: 15px; color: #e2e8f0; }
  .modal-header button { background: transparent; border: none; color: #94a3b8; font-size: 22px; cursor: pointer; line-height: 1; padding: 0 4px; }
  .modal-header button:hover { color: #e2e8f0; }
  .modal-liste { overflow-y: auto; padding: 8px 12px; }
  .modal-item { padding: 10px 8px; border-bottom: 1px solid #29344a; font-size: 13px; display: flex; flex-direction: column; gap: 3px; }
  .modal-item:last-child { border-bottom: none; }
  .modal-item-url { color: #e2e8f0; word-break: break-all; }
  .modal-item-detail { color: #64748b; font-size: 12px; }
  #bouton-langue { background: transparent; border: 1px solid #334155; color: #94a3b8; padding: 5px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; margin-left: auto; }
  #bouton-langue:hover { background: #1e293b; color: #e2e8f0; }
</style>
</head>
<body>
<header>
  <svg class="logo-icone" viewBox="80 10 420 300" width="40" height="40">
    <path d="M 160 260 C 158 200 190 145 245 125 C 250 80 285 45 335 35 C 365 29 395 35 415 52 C 398 58 380 70 370 88 C 395 80 425 82 448 98 C 432 102 415 112 405 128 C 432 125 460 135 478 158 C 460 158 442 165 430 178 C 455 182 478 198 490 222 C 470 220 450 224 434 234 C 452 244 465 262 468 285 C 448 277 425 276 405 282 C 413 298 412 315 402 328 C 388 315 370 308 350 308 C 355 322 352 336 340 346 C 322 334 305 320 292 302 C 260 308 228 300 205 280 C 185 282 168 276 160 260 Z" fill="#0a1120"/>
    <path d="M 250 130 C 285 98 330 88 368 102 C 398 113 418 138 418 168 C 396 166 375 172 358 184 C 368 196 371 210 366 222 C 348 213 328 210 310 213 C 314 226 311 239 302 248 C 285 234 268 226 250 227 C 236 212 230 193 233 174 C 237 158 242 143 250 130 Z" fill="#f8fafc"/>
    <path d="M 205 280 C 202 265 208 250 222 240 C 232 248 236 260 233 273 C 224 280 214 281 205 280 Z" fill="#f8fafc"/>
    <circle cx="352" cy="148" r="19" fill="#60a5fa"/>
    <circle cx="352" cy="148" r="7.5" fill="#1e3a5f"/>
    <circle cx="349" cy="145" r="2.5" fill="#f8fafc"/>
    <g stroke="#93c5fd" stroke-width="2" opacity="0.9">
      <path d="M 352 129 L 352 110 L 385 110" fill="none"/>
      <circle cx="388" cy="110" r="3.5" fill="#93c5fd"/>
      <path d="M 371 148 L 405 148 L 405 170" fill="none"/>
      <circle cx="405" cy="173" r="3.5" fill="#93c5fd"/>
      <path d="M 335 160 L 305 185 L 305 212" fill="none"/>
      <circle cx="305" cy="215" r="3.5" fill="#93c5fd"/>
    </g>
    <path d="M 160 260 C 140 258 122 260 108 268 C 122 274 138 278 155 277 Z" fill="#0a1120"/>
  </svg>
  <h1>ORCAAS</h1>
  <span class="badge" data-i18n="badge">SEO Specialiste IA</span>
  <nav>
    <button id="onglet-chat" class="actif" onclick="afficherOnglet('chat')" data-i18n="onglet_chat">Chat</button>
    <button id="onglet-dashboard" onclick="afficherOnglet('dashboard')" data-i18n="onglet_dashboard">Dashboard</button>
  </nav>
  <button id="bouton-langue" onclick="changerLangue()">EN</button>
</header>

<div id="vue-chat">
  <div id="chat">
    <div class="msg orcaas" data-i18n="bienvenue">Bonjour, je suis ORCAAS. Posez-moi une question sur l'etat du site, mes dernieres actions, ou les resultats obtenus.</div>
  </div>
  <div id="input-zone">
    <input type="text" id="question" placeholder="Posez votre question..." autocomplete="off" data-i18n-placeholder="placeholder_question" />
    <button id="send" data-i18n="bouton_envoyer">Envoyer</button>
  </div>
</div>

<div id="modal-detail" class="modal-overlay">
  <div class="modal-contenu">
    <div class="modal-header">
      <h3 id="modal-titre"></h3>
      <button onclick="fermerModal()">&times;</button>
    </div>
    <div id="modal-liste" class="modal-liste"></div>
  </div>
</div>

<div id="vue-dashboard">
  <div id="barre-filtre">
    <label><span data-i18n="label_du">Du</span> <input type="date" id="date-debut"></label>
    <label><span data-i18n="label_au">au</span> <input type="date" id="date-fin"></label>
    <button id="appliquer-filtre" onclick="rechargerAvecFiltre()" data-i18n="bouton_appliquer">Appliquer</button>
    <span id="periode-affichee"></span>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_pages">Top pages par impressions (GSC, periode selectionnee)</h2>
    <canvas id="chartPages"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_briefs">Corrections ORCAAS par type de probleme</h2>
    <canvas id="chartBriefs"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_evals">Evaluations d'impact par verdict</h2>
    <canvas id="chartEvals"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_opportunites">Top 10 opportunites SEO (score)</h2>
    <canvas id="chartOpportunites"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_rankmath">Couverture RankMath (mot-cle cible)</h2>
    <canvas id="chartRankmath"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_audit">Sante technique du site (495 pages)</h2>
    <canvas id="chartAudit"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_leads">Leads par outil (tous canaux)</h2>
    <canvas id="chartLeads"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_publications">Publications par silo</h2>
    <canvas id="chartPublications"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_indexation">Indexation Google (statut reel par page)</h2>
    <canvas id="chartIndexation"></canvas>
  </div>
</div>

<script>
const TRADUCTIONS = {
  fr: {
    badge: "SEO Specialiste IA", onglet_chat: "Chat", onglet_dashboard: "Dashboard",
    bienvenue: "Bonjour, je suis ORCAAS. Posez-moi une question sur l'etat du site, mes dernieres actions, ou les resultats obtenus.",
    placeholder_question: "Posez votre question...", bouton_envoyer: "Envoyer",
    reflexion: "ORCAAS reflechit...", erreur_inconnue: "Erreur inconnue",
    erreur_connexion: "Erreur de connexion : ", erreur_chargement: "Erreur de chargement : ",
    aucune_donnee: "Aucune donnee disponible",
    label_du: "Du", label_au: "au", bouton_appliquer: "Appliquer", periode_prefixe: "Periode : ",
    titre_pages: "Top pages par impressions (GSC, periode selectionnee)",
    titre_briefs: "Corrections ORCAAS par type de probleme",
    titre_evals: "Evaluations d'impact par verdict",
    titre_opportunites: "Top 10 opportunites SEO (score)",
    titre_rankmath: "Couverture RankMath (mot-cle cible)",
    titre_audit: "Sante technique du site (495 pages)",
    titre_leads: "Leads par outil (tous canaux)",
    titre_publications: "Publications par silo",
    titre_indexation: "Indexation Google (statut reel par page)",
  },
  en: {
    badge: "AI SEO Specialist", onglet_chat: "Chat", onglet_dashboard: "Dashboard",
    bienvenue: "Hello, I'm ORCAAS. Ask me about the site's status, my latest actions, or the results obtained.",
    placeholder_question: "Ask your question...", bouton_envoyer: "Send",
    reflexion: "ORCAAS is thinking...", erreur_inconnue: "Unknown error",
    erreur_connexion: "Connection error: ", erreur_chargement: "Loading error: ",
    aucune_donnee: "No data available",
    label_du: "From", label_au: "to", bouton_appliquer: "Apply", periode_prefixe: "Period: ",
    titre_pages: "Top pages by impressions (GSC, selected period)",
    titre_briefs: "ORCAAS corrections by problem type",
    titre_evals: "Impact evaluations by verdict",
    titre_opportunites: "Top 10 SEO opportunities (score)",
    titre_rankmath: "RankMath coverage (target keyword)",
    titre_audit: "Site technical health (495 pages)",
    titre_leads: "Leads by tool (all channels)",
    titre_publications: "Publications by silo",
    titre_indexation: "Google indexing (real per-page status)",
  }
};

function langueActuelle() {
  return localStorage.getItem('orcaas_langue') || 'fr';
}

function appliquerLangue(lang) {
  const dict = TRADUCTIONS[lang] || TRADUCTIONS.fr;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const cle = el.getAttribute('data-i18n');
    if (dict[cle]) el.textContent = dict[cle];
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const cle = el.getAttribute('data-i18n-placeholder');
    if (dict[cle]) el.placeholder = dict[cle];
  });
  document.getElementById('bouton-langue').textContent = lang === 'fr' ? 'EN' : 'FR';
  document.documentElement.lang = lang;
}

function changerLangue() {
  const actuelle = langueActuelle();
  const nouvelle = actuelle === 'fr' ? 'en' : 'fr';
  localStorage.setItem('orcaas_langue', nouvelle);
  appliquerLangue(nouvelle);
  if (window.dashboardCharge) { window.dashboardCharge = false; chargerDashboard(); }
}

appliquerLangue(langueActuelle());

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
  const loading = ajouterMessage(TRADUCTIONS[langueActuelle()].reflexion, 'loading');
  try {
    const res = await fetch('/orcaas-chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: q})
    });
    const data = await res.json();
    loading.remove();
    ajouterMessage(data.reponse || data.erreur || TRADUCTIONS[langueActuelle()].erreur_inconnue, 'orcaas');
  } catch (e) {
    loading.remove();
    ajouterMessage(TRADUCTIONS[langueActuelle()].erreur_connexion + e.message, 'orcaas');
  }
  send.disabled = false;
  question.focus();
}

send.addEventListener('click', envoyer);
question.addEventListener('keypress', function(e) {
  if (e.key === 'Enter') envoyer();
});

function datesParDefaut() {
  const auj = new Date();
  const il30j = new Date(auj);
  il30j.setDate(il30j.getDate() - 30);
  return { debut: il30j.toISOString().slice(0,10), fin: auj.toISOString().slice(0,10) };
}

async function chargerDashboard(dateDebut, dateFin) {
  window.dashboardCharge = true;
  const defaut = datesParDefaut();
  const db = dateDebut || defaut.debut;
  const df = dateFin || defaut.fin;
  document.getElementById('date-debut').value = db;
  document.getElementById('date-fin').value = df;
  try {
    const res = await fetch('/orcaas-dashboard-data?date_debut=' + db + '&date_fin=' + df);
    const donnees = await res.json();
    document.getElementById('periode-affichee').textContent = TRADUCTIONS[langueActuelle()].periode_prefixe + (donnees.date_debut || db) + ' - ' + (donnees.date_fin || df);
    dessinerGraphiques(donnees);
  } catch (e) {
    document.getElementById('vue-dashboard').innerHTML = '<div class="vide">' + TRADUCTIONS[langueActuelle()].erreur_chargement + e.message + '</div>';
  }
}

function rechargerAvecFiltre() {
  const db = document.getElementById('date-debut').value;
  const df = document.getElementById('date-fin').value;
  chargerDashboard(db, df);
}

async function afficherDetail(graphique, categorie) {
  document.getElementById('modal-titre').textContent = categorie;
  document.getElementById('modal-liste').innerHTML = '<div class=\"vide\">...</div>';
  document.getElementById('modal-detail').style.display = 'flex';
  try {
    const res = await fetch('/orcaas-dashboard-detail?graphique=' + encodeURIComponent(graphique) + '&categorie=' + encodeURIComponent(categorie));
    const data = await res.json();
    const liste = document.getElementById('modal-liste');
    if (data.erreur) {
      liste.innerHTML = '<div class=\"vide\">' + data.erreur + '</div>';
      return;
    }
    if (!data.items || data.items.length === 0) {
      liste.innerHTML = '<div class=\"vide\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
      return;
    }
    liste.innerHTML = data.items.map(function(it) {
      return '<div class=\"modal-item\"><span class=\"modal-item-url\">' + it.url + '</span><span class=\"modal-item-detail\">' + (it.detail || '') + '</span></div>';
    }).join('');
  } catch (e) {
    document.getElementById('modal-liste').innerHTML = '<div class=\"vide\">' + e.message + '</div>';
  }
}

function fermerModal() {
  document.getElementById('modal-detail').style.display = 'none';
}

function assurerCanvas(id) {
  var el = document.getElementById(id);
  var chartExistant = Chart.getChart(id);
  if (chartExistant) { chartExistant.destroy(); }
  if (!el || el.tagName !== 'CANVAS') {
    var c = document.createElement('canvas');
    c.id = id;
    if (el) { el.replaceWith(c); } 
    el = c;
  }
  return el;
}

function dessinerGraphiques(DONNEES) {
  Chart.defaults.color = '#94a3b8';
  Chart.defaults.borderColor = '#334155';

  if (DONNEES.top_pages && DONNEES.top_pages.length > 0) {
    new Chart(assurerCanvas('chartPages'), {
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
    document.getElementById('chartPages').outerHTML = '<div class=\"vide\" id=\"chartPages\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }

  if (DONNEES.briefs_par_probleme && DONNEES.briefs_par_probleme.length > 0) {
    new Chart(assurerCanvas('chartBriefs'), {
      type: 'doughnut',
      data: {
        labels: DONNEES.briefs_par_probleme.map(b => b.probleme),
        datasets: [{ data: DONNEES.briefs_par_probleme.map(b => b.nb), backgroundColor: ['#2563eb','#f59e0b','#16a34a','#dc2626','#7e22ce'] }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } }, onClick: function(evt, els) { if (els.length > 0) afficherDetail('briefs', this.data.labels[els[0].index]); } }
    });
  } else {
    document.getElementById('chartBriefs').outerHTML = '<div class=\"vide\" id=\"chartBriefs\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }

  if (DONNEES.evaluations_par_verdict && DONNEES.evaluations_par_verdict.length > 0) {
    new Chart(assurerCanvas('chartEvals'), {
      type: 'doughnut',
      data: {
        labels: DONNEES.evaluations_par_verdict.map(v => v.verdict),
        datasets: [{ data: DONNEES.evaluations_par_verdict.map(v => v.nb), backgroundColor: ['#64748b','#16a34a','#dc2626','#2563eb'] }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } }, onClick: function(evt, els) { if (els.length > 0) afficherDetail('evaluations', this.data.labels[els[0].index]); } }
    });
  } else {
    document.getElementById('chartEvals').outerHTML = '<div class=\"vide\" id=\"chartEvals\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }

  if (DONNEES.opportunites && DONNEES.opportunites.length > 0) {
    new Chart(assurerCanvas('chartOpportunites'), {
      type: 'bar',
      data: {
        labels: DONNEES.opportunites.map(o => o.url.length > 25 ? o.url.slice(0,25)+'...' : o.url),
        datasets: [{ label: 'Score opportunite', data: DONNEES.opportunites.map(o => o.score), backgroundColor: '#7e22ce' }]
      },
      options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } } }
    });
  } else {
    document.getElementById('chartOpportunites').outerHTML = '<div class=\"vide\" id=\"chartOpportunites\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }

  if (DONNEES.rankmath_couverture) {
    const rm = DONNEES.rankmath_couverture;
    if ((rm.avec_mot_cle + rm.sans_mot_cle) > 0) {
      new Chart(assurerCanvas('chartRankmath'), {
        type: 'doughnut',
        data: {
          labels: ['Avec mot-cle cible', 'Sans mot-cle cible'],
          datasets: [{ data: [rm.avec_mot_cle, rm.sans_mot_cle], backgroundColor: ['#16a34a', '#dc2626'] }]
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } }, onClick: function(evt, els) { if (els.length > 0) afficherDetail('rankmath', this.data.labels[els[0].index]); } }
      });
    } else {
      document.getElementById('chartRankmath').outerHTML = '<div class=\"vide\" id=\"chartRankmath\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
    }
  }

  if (DONNEES.audit_technique && DONNEES.audit_technique.length > 0) {
    new Chart(assurerCanvas('chartAudit'), {
      type: 'doughnut',
      data: {
        labels: DONNEES.audit_technique.map(a => a.categorie),
        datasets: [{ data: DONNEES.audit_technique.map(a => a.nb), backgroundColor: ['#16a34a','#f59e0b','#dc2626','#64748b'] }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } }, onClick: function(evt, els) { if (els.length > 0) afficherDetail('audit_technique', this.data.labels[els[0].index]); } }
    });
  } else {
    document.getElementById('chartAudit').outerHTML = '<div class=\"vide\" id=\"chartAudit\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }

  if (DONNEES.leads_par_outil && DONNEES.leads_par_outil.length > 0) {
    new Chart(assurerCanvas('chartLeads'), {
      type: 'bar',
      data: {
        labels: DONNEES.leads_par_outil.map(l => l.outil),
        datasets: [{ label: 'Leads', data: DONNEES.leads_par_outil.map(l => l.nb), backgroundColor: '#2563eb' }]
      },
      options: { responsive: true, plugins: { legend: { display: false } }, onClick: function(evt, els) { if (els.length > 0) afficherDetail('leads', this.data.labels[els[0].index]); } }
    });
  } else {
    document.getElementById('chartLeads').outerHTML = '<div class=\"vide\" id=\"chartLeads\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }

  if (DONNEES.publications_par_silo && DONNEES.publications_par_silo.length > 0) {
    new Chart(assurerCanvas('chartPublications'), {
      type: 'bar',
      data: {
        labels: DONNEES.publications_par_silo.map(p => p.silo),
        datasets: [{ label: 'Articles publies', data: DONNEES.publications_par_silo.map(p => p.nb), backgroundColor: '#f59e0b' }]
      },
      options: { responsive: true, plugins: { legend: { display: false } }, onClick: function(evt, els) { if (els.length > 0) afficherDetail('publications', this.data.labels[els[0].index]); } }
    });
  } else {
    document.getElementById('chartPublications').outerHTML = '<div class=\"vide\" id=\"chartPublications\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }

  if (DONNEES.indexation && DONNEES.indexation.length > 0) {
    const couleursIndex = { 'Submitted and indexed': '#16a34a', 'Crawled - currently not indexed': '#f59e0b', 'URL is unknown to Google': '#dc2626' };
    new Chart(assurerCanvas('chartIndexation'), {
      type: 'doughnut',
      data: {
        labels: DONNEES.indexation.map(i => i.etat),
        datasets: [{ data: DONNEES.indexation.map(i => i.nb), backgroundColor: DONNEES.indexation.map(i => couleursIndex[i.etat] || '#2563eb') }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } }, onClick: function(evt, els) { if (els.length > 0) afficherDetail('indexation', this.data.labels[els[0].index]); } }
    });
  } else {
    document.getElementById('chartIndexation').outerHTML = '<div class=\"vide\" id=\"chartIndexation\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }
}
</script>
</body>
</html>"""


@app.route('/orcaas-dashboard-detail', methods=['GET'])
def orcaas_dashboard_detail_endpoint():
    """Detail cliquable du dashboard : liste des elements derriere une
    categorie agregee. Page publique en lecture seule -- transparence
    uniquement, aucune action possible depuis cette liste."""
    from pipeline import agent_orcaas_detail_categorie, init_bigquery

    graphique = request.args.get('graphique', '')
    categorie = request.args.get('categorie', '')
    if not graphique or not categorie:
        return jsonify({"items": [], "erreur": "parametres graphique et categorie requis"}), 400

    try:
        client_bq = init_bigquery()
        resultat = agent_orcaas_detail_categorie(client_bq, graphique, categorie)
        return jsonify(resultat), 200
    except Exception as e:
        return jsonify({"items": [], "erreur": str(e)}), 500


@app.route('/orcaas-dashboard-data', methods=['GET'])
def orcaas_dashboard_data_endpoint():
    """Donnees JSON du dashboard (page publique, appelee en arriere-plan par
    /orcaas). Parametres optionnels : ?date_debut=AAAA-MM-JJ&date_fin=AAAA-MM-JJ
    (par defaut : 30 derniers jours)."""
    from pipeline import agent_orcaas_donnees_dashboard, init_bigquery
    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    try:
        client_bq = init_bigquery()
        donnees = agent_orcaas_donnees_dashboard(client_bq, date_debut, date_fin)
        return jsonify(donnees), 200
    except Exception as e:
        return jsonify({"top_pages": [], "briefs_par_probleme": [], "evaluations_par_verdict": [], "erreur": str(e)}), 500


@app.route('/orcaas', methods=['GET'])
def orcaas_chat_page():
    """Application unique ORCAAS : onglets Chat + Dashboard."""
    return ORCAAS_APP_HTML


@app.route('/agent-orcaas-monitoring', methods=['POST'])
def agent_orcaas_monitoring_endpoint():
    """AGENT ORCAAS -- Stack Monitoring du pipeline : detecte et supprime
    automatiquement les doublons de sujet publies le meme jour."""
    from pipeline import agent_orcaas_monitoring_pipeline, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            resultat = agent_orcaas_monitoring_pipeline(client_bq)
            print(f"✅ Monitoring ORCAAS termine : {resultat}")
        except Exception as e:
            print(f"❌ Erreur monitoring ORCAAS : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "monitoring": "declenche en arriere-plan"}), 200


@app.route('/synchroniser-indexation', methods=['POST'])
def synchroniser_indexation_endpoint():
    """CHANTIER INDEXATION : verifie l'indexation Google reelle de chaque
    page. Parametre optionnel ?limite=N pour tester sur un petit lot."""
    from pipeline import synchroniser_indexation, init_bigquery

    limite = request.args.get('limite')
    limite = int(limite) if limite else None

    def sync_async():
        try:
            client_bq = init_bigquery()
            nb = synchroniser_indexation(client_bq, limite=limite)
            print(f"✅ Sync indexation terminee : {nb} pages")
        except Exception as e:
            print(f"❌ Erreur sync indexation : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "sync": "declenche en arriere-plan"}), 200


@app.route('/agent-orcaas-analyser-chevauchement', methods=['POST'])
def agent_orcaas_analyser_chevauchement_endpoint():
    """AGENT ORCAAS -- Stack Contenu editorial, etape 1 : detecte le
    chevauchement thematique. Lecture seule, retourne le resultat directement."""
    from pipeline import agent_orcaas_analyser_chevauchement, init_bigquery

    try:
        client_bq = init_bigquery()
        resultats = agent_orcaas_analyser_chevauchement(client_bq)
        return jsonify({"status": "ok", "resultats": resultats}), 200
    except Exception as e:
        return jsonify({"status": "erreur", "detail": str(e)}), 500


@app.route('/agent-orcaas-differencier', methods=['POST'])
def agent_orcaas_differencier_endpoint():
    """AGENT ORCAAS -- Stack Contenu editorial, etape 2 : reecrit les pages
    en chevauchement thematique pour leur donner un angle distinct."""
    from pipeline import agent_orcaas_differencier_contenu, init_bigquery

    def sync_async():
        try:
            client_bq = init_bigquery()
            resultat = agent_orcaas_differencier_contenu(client_bq)
            print(f"✅ Differenciation ORCAAS terminee : {resultat}")
        except Exception as e:
            print(f"❌ Erreur differenciation ORCAAS : {e}")

    thread = threading.Thread(target=sync_async)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "ok", "differenciation": "declenchee en arriere-plan"}), 200


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
