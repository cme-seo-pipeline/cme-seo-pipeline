"""
CME — QA complete du tunnel de conversion (lecture seule).

Demande operateur du 24/10/2026, suite au constat du lead "Lionel" non
retrouve dans Sheets (tunnel Sheets pas encore cable au moment de sa
soumission -- voir CLAUDE.md) : verifier TOUS les canaux de conversion du
site, pas seulement le nouveau formulaire inline -- pages live, relais
serveur (WordPress -> Cloud Run -> BigQuery), et relais Google Sheets
(formulaire inline + anciens simulateurs, quand l'URL est connue du repo).

Ne modifie rien cote WordPress/Sheets. Un seul POST de test (deja une
convention du projet, cf. diagnostiquer_relais_tracking.py) vers le relais
central, marque 'tool=diagnostic-relais-test'. Les appels GAS sont des GET
de sonde, pas des ecritures de lead reelles cote appelant (mais peuvent
ecrire une ligne de test visible dans l'onglet Sheets correspondant --
assume, meme convention que les lignes 'diagnostic-relais-test' deja
presentes dans leads_convertis depuis le 19/10).

Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement (fourni par
le runner GitHub Actions).
"""
import sys
import time
import uuid
from datetime import datetime, timezone

import requests

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
BASE = "https://www.comprendre-mon-energie.fr"
RELAIS_URL = BASE + "/wp-json/cme/v1/log-lead"
CLOUD_RUN_LOG_LEAD = "https://cme-tracking-api-217943559750.europe-west1.run.app/api/log-lead"
CLOUD_RUN_LOG_CLIC = "https://cme-tracking-api-217943559750.europe-west1.run.app/api/log-clic"

# URL Sheets du nouveau formulaire inline (constante cablee le 22/10 dans
# cme-tracking-conversion.php). Relais supplementaire, pas la source de
# verite (BigQuery l'est).
GAS_URL_FORMULAIRE_INLINE = "https://script.google.com/macros/s/AKfycbxpzUna-KBj6kpASyufpeAz0rF2C-lXFHSAjpUGiHnrqpTujYsLnUZi9aJlQrHciSThxA/exec"

# Seul l'ancien simulateur solaire a son URL GAS en dur dans le repo
# (comparateur-energie et simulateur-aides la stockent en wp_options,
# non lisible depuis ce sandbox/runner -- limite documentee ci-dessous).
GAS_URL_SIMULATEUR_SOLAIRE = "https://script.google.com/macros/s/AKfycbyQHpJCRLdQZKHDxRNzV3pIHVDQgGuaRKXzlBZfFxpgmVzzPz4YQs8BKww0QMTORB7YGQ/exec"

# Candidats de pages a verifier (slugs vus dans l'historique leads_convertis
# pour les 3 anciens simulateurs, + la page de contact actuelle).
PAGES_A_VERIFIER = {
    "Page de contact (/contactez-un-expert/)": BASE + "/contactez-un-expert/",
    "Simulateur aides renovation": BASE + "/simulateur-aides-renovation-energetique/",
    "Comparateur energie gaz/elec": BASE + "/comparateur-energie-electricite-gaz/",
    "Devis panneau solaire": BASE + "/devis-panneau-solaire/",
}


def section(titre):
    print("\n" + "=" * 70)
    print(titre)
    print("=" * 70)


def main():
    client = bigquery.Client(project=PROJECT_ID)

    section("1. Liveness des pages de conversion (HTTP GET)")
    for nom, url in PAGES_A_VERIFIER.items():
        try:
            resp = requests.get(url, timeout=15, allow_redirects=True)
            print(f"   {nom:40s} -> {resp.status_code:3d}  ({url})")
        except Exception as e:
            print(f"   {nom:40s} -> ❌ erreur reseau : {e}  ({url})")

    section("2. Relais central WordPress -> Cloud Run -> BigQuery (formulaire inline / formulaire contact / appel)")
    marqueur = f"qa-{uuid.uuid4().hex[:12]}"
    payload = {
        "tool": "diagnostic-relais-test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_page": BASE + "/contactez-un-expert/",
        "details": {"marqueur": marqueur, "origine": "qa_tunnel_conversion_complet"},
    }
    try:
        resp = requests.post(RELAIS_URL, json=payload, timeout=15)
        print(f"   POST {RELAIS_URL} -> {resp.status_code} {resp.text[:200]!r}")
    except Exception as e:
        print(f"   ❌ Erreur reseau : {e}")

    time.sleep(10)
    try:
        df = client.query(f"""
            SELECT timestamp, details
            FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
            WHERE tool = 'diagnostic-relais-test'
              AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE)
            ORDER BY timestamp DESC
        """).to_dataframe()
        trouve = df['details'].astype(str).str.contains(marqueur).any() if not df.empty else False
        print(f"   Marqueur '{marqueur}' retrouve dans BigQuery : {'✅ OUI' if trouve else '❌ NON'}")
    except Exception as e:
        print(f"   ⚠️ Erreur BigQuery : {e}")

    section("3. POST direct sur Cloud Run /api/log-clic (meme service, utilise par les anciens simulateurs cote client)")
    try:
        resp = requests.post(CLOUD_RUN_LOG_CLIC, json={"tool": "diagnostic-relais-test", "marqueur": marqueur}, timeout=15)
        print(f"   Code HTTP : {resp.status_code} -- Corps : {resp.text[:200]!r}")
    except Exception as e:
        print(f"   ❌ Erreur reseau : {e}")

    section("4. Relais Google Sheets -- formulaire inline (cme-formulaire-article-leads.gs)")
    try:
        probe_payload = {
            "tool": "qa-diagnostic-sheets",
            "prenom": f"QA-TEST-{marqueur}",
            "telephone": "",
            "details": '{"position":0,"silo":"qa"}',
            "source_page": "qa_tunnel_conversion_complet.py",
        }
        import json as _json
        from urllib.parse import quote
        url_probe = GAS_URL_FORMULAIRE_INLINE + "?payload=" + quote(_json.dumps(probe_payload))
        resp = requests.get(url_probe, timeout=20)
        print(f"   GET Apps Script (formulaire inline) -> {resp.status_code}")
        print(f"   Corps : {resp.text[:300]!r}")
        print("   NB : une reponse {\"status\":\"ok\"} ici confirme que l'Apps Script est deploye, "
              "accessible et execute sans erreur -- pas une preuve visuelle de la ligne dans le Sheet "
              "(a confirmer par toi dans l'onglet \"Leads Formulaire Article\", ligne prefixee QA-TEST-).")
    except Exception as e:
        print(f"   ❌ Erreur reseau (script.google.com injoignable depuis ce runner ?) : {e}")

    section("5. Relais Google Sheets -- ancien simulateur solaire (URL en dur dans le repo)")
    try:
        import json as _json
        from urllib.parse import quote
        probe_payload = {"tool": "qa-diagnostic-sheets", "marqueur": marqueur}
        url_probe = GAS_URL_SIMULATEUR_SOLAIRE + "?payload=" + quote(_json.dumps(probe_payload))
        resp = requests.get(url_probe, timeout=20)
        print(f"   GET Apps Script (simulateur solaire) -> {resp.status_code}")
        print(f"   Corps : {resp.text[:300]!r}")
    except Exception as e:
        print(f"   ❌ Erreur reseau : {e}")

    section("6. Limite connue : comparateur-energie et simulateur-aides stockent leur URL GAS en wp_options")
    print("   (configure via l'admin WordPress, pas dans le repo) -- non testable depuis ce sandbox/runner.")
    print("   Seule verification possible ici : la page est-elle live (section 1) et des lignes recentes")
    print("   existent-elles dans leads_convertis pour tool='comparateur-energie'/'aides-renovation' (section 7).")

    section("7. Derniere activite par outil, toutes sources confondues (rappel)")
    try:
        df = client.query(f"""
            SELECT tool, COUNT(*) AS nb_total, MAX(timestamp) AS derniere_activite
            FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
            GROUP BY tool
            ORDER BY derniere_activite DESC
        """).to_dataframe()
        print(df.to_string(index=False))
    except Exception as e:
        print(f"   ⚠️ Erreur BigQuery : {e}")

    section("8. IAM Cloud Run -- rappel de l'incident du 19/10 (acces anonyme toujours actif ?)")
    try:
        resp = requests.post(CLOUD_RUN_LOG_LEAD, json={"tool": "diagnostic-relais-test", "marqueur": marqueur + "-direct"}, timeout=15)
        print(f"   POST direct Cloud Run (sans WordPress) -> {resp.status_code} {resp.text[:150]!r}")
        if resp.status_code in (401, 403):
            print("   ⚠️ ALERTE : meme symptome que l'incident IAM du 19/10 (politique IAM reinitialisee a vide ?)")
    except Exception as e:
        print(f"   ❌ Erreur reseau : {e}")


if __name__ == "__main__":
    main()
