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
            # Ajoutes le 24/11/2026 -- mini-formulaire inline "contact-expert-inline"
            # etendu a 6 champs (voir cme-cta-progressifs.php, variante 'contact'
            # uniquement). Absents du payload (variante 'appel', ou tout autre
            # tool existant) -> chaine vide, colonnes BigQuery nullable, aucune
            # erreur. Necessite les colonnes type_logement/statut_occupation sur
            # leads_convertis (scripts-maintenance/ajouter_colonnes_logement_leads.py,
            # a executer avant ce deploiement -- meme precaution d'ordre que les
            # autres colonnes ajoutees a ce schema).
            "type_logement":     str(data.get("type_logement", ""))[:20],
            "statut_occupation": str(data.get("statut_occupation", ""))[:20],
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
                # temps_ms ajoute le 01/11/2026 (colonne BigQuery + JS cote
                # mu-plugins deja en place depuis cette date) mais JAMAIS
                # mappe ici -- bug trouve le 04/11/2026
                # (diagnostiquer_temps_ms_vide.py : 5048/5048 lignes
                # lecture_position avec temps_ms NULL depuis le debut de la
                # collecte). Nullable : certains evenements plus anciens
                # ou d'une version de JS non encore redeployee n'en
                # envoient pas.
                "temps_ms":         (int(e["temps_ms"]) if e.get("temps_ms") is not None else None),
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


INDICATEURS_PROJECT = "seo-data-hub-cme.04_pipeline_seo.indicateurs_reglementaires"


@app.route('/api/tarif-edf', methods=['GET'])
def tarif_edf():
    """
    Tarif reglementaire EDF (TRVE, tarif 6 kVA -- tarif residentiel le
    plus courant) pour l'offre de reference du comparateur-energie.

    Remplace un endpoint precedent (/api/tarifs) qui ne faisait que
    renvoyer un statut fixe sans aucune donnee reelle -- jamais appele
    par le front, decouvert lors du diagnostic du 16/11/2026. Lit
    indicateurs_reglementaires, deja synchronise quotidiennement
    (sync-indicateurs.yml) et deja utilise pour l'audit mensuel des
    articles -- meme source de verite, pas de nouvelle donnee a sourcer.
    """
    try:
        client_bq = bigquery.Client()
        # .result() + iteration directe sur les Row BigQuery plutot que
        # .to_dataframe() -- evite une dependance a pandas/db-dtypes pour
        # lire 2 lignes (bug trouve au deploiement du 16/11 : pandas n'est
        # pas dans requirements.txt, jamais installe dans le conteneur
        # Cloud Run, .to_dataframe() plante systematiquement en prod).
        rows = list(client_bq.query(f"""
            SELECT indicateur, valeur, date_debut_validite
            FROM `{INDICATEURS_PROJECT}`
            WHERE indicateur IN ('TRVE_part_variable_TTC', 'TRVE_part_fixe_TTC')
              AND sous_categorie = '6 kVA'
            QUALIFY ROW_NUMBER() OVER (PARTITION BY indicateur ORDER BY date_verification DESC) = 1
        """).result())
        valeurs = {row["indicateur"]: row for row in rows}
        if "TRVE_part_variable_TTC" not in valeurs or "TRVE_part_fixe_TTC" not in valeurs:
            return _cors(jsonify({"status": "error", "detail": "indicateurs TRVE introuvables"})), 404

        variable = valeurs["TRVE_part_variable_TTC"]
        fixe = valeurs["TRVE_part_fixe_TTC"]
        resp = jsonify({
            "status": "ok",
            "prix_kwh_ttc": round(float(variable["valeur"]), 5),
            "abo_mois_ttc": round(float(fixe["valeur"]) / 12, 2),
            "date_debut_validite": variable["date_debut_validite"].strftime("%d/%m/%Y"),
        })
        return _cors(resp), 200
    except Exception as e:
        print(f"tarif-edf error: {e}")
        return _cors(jsonify({"status": "error", "detail": str(e)})), 500


@app.route('/api/tarif-gaz-repere', methods=['GET'])
def tarif_gaz_repere():
    """
    Prix Repere CRE du gaz (PRVG, moyenne toutes consommations) pour
    l'offre de reference gaz du comparateur-energie. Meme source et
    meme principe que /api/tarif-edf. Aucun abonnement reglemente
    equivalent n'est publie pour le gaz -- seul le prix au kWh est
    renvoye, l'abonnement reste la valeur indicative deja en place
    cote front (pas de source live pour cette partie).
    """
    try:
        client_bq = bigquery.Client()
        # Meme correctif que tarif_edf() ci-dessus : .result() au lieu de
        # .to_dataframe() (pandas indisponible dans le conteneur Cloud Run).
        rows = list(client_bq.query(f"""
            SELECT valeur, date_debut_validite
            FROM `{INDICATEURS_PROJECT}`
            WHERE indicateur = 'PRVG_moyen_TTC'
            ORDER BY date_verification DESC
            LIMIT 1
        """).result())
        if not rows:
            return _cors(jsonify({"status": "error", "detail": "indicateur PRVG_moyen_TTC introuvable"})), 404

        row = rows[0]
        resp = jsonify({
            "status": "ok",
            "prix_kwh_ttc": round(float(row["valeur"]) / 1000, 5),  # €/MWh -> €/kWh
            "date_debut_validite": row["date_debut_validite"].strftime("%d/%m/%Y"),
        })
        return _cors(resp), 200
    except Exception as e:
        print(f"tarif-gaz-repere error: {e}")
        return _cors(jsonify({"status": "error", "detail": str(e)})), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
