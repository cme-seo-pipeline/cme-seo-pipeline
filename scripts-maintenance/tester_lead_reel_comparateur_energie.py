"""
CME — TEST RÉEL (demande explicite operateur, 16/11/2026, qualifie de
"fondamental") : verifier de bout en bout si une soumission du formulaire
de lead du comparateur-energie fonctionne reellement.

⚠️ CE SCRIPT ENVOIE UNE VRAIE REQUETE A L'ENDPOINT AJAX WORDPRESS LIVE
(cme_cmp_handle_lead), avec une identite de test clairement marquee
(prenom/telephone distinctifs, facilement identifiables et nettoyables
apres coup -- meme precedent que les tests "Lionel"/"QA-TEST"/
"0695410020" deja realises dans ce projet). Cela declenche reellement :
- un email vers l'adresse de contact deja codee en dur dans le plugin
  (variable $dest de cme_cmp_handle_lead -- l'operateur a lui-meme
  demande ce test, donc c'est attendu) ;
- potentiellement une ligne dans le Google Sheet "Leads Comparateur" si
  l'URL Apps Script est configuree ;
- un wp_remote_post vers cme-tracking-api -> leads_convertis (BigQuery).

But : lire directement la reponse JSON de l'endpoint (qui expose deja
email_sent et le resultat GAS) + confirmer ensuite si la ligne apparait
dans leads_convertis -- pour trancher entre abandon UX et panne
technique silencieuse.

Pas lecture seule (exception documentee, demande explicite operateur).
"""
import json
import re
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("❌ requests manquant")

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PAGE_URL = "https://www.comprendre-mon-energie.fr/comparateur-energie-electricite-gaz/"
AJAX_URL = "https://www.comprendre-mon-energie.fr/wp-admin/admin-ajax.php"
PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"

MARQUEUR = f"TESTDIAG{int(time.time())}"


def section(t):
    print(f"\n{'='*100}\n{t}\n{'='*100}")


def main():
    section("1. Récupération d'un nonce réel depuis la page live")
    r = requests.get(PAGE_URL, timeout=20, headers={"User-Agent": "Mozilla/5.0 (test diagnostic CME)"})
    print(f"  Statut page : {r.status_code}")
    m_nonce = re.search(r"CMPNONCE='([^']+)'", r.text)
    m_ajax = re.search(r"CMPAJAX='([^']+)'", r.text)
    if not m_nonce:
        print("  ❌ Nonce introuvable dans la page -- impossible de continuer le test.")
        return
    nonce = m_nonce.group(1)
    ajax_url = m_ajax.group(1) if m_ajax else AJAX_URL
    print(f"  Nonce extrait : {nonce}")
    print(f"  URL ajax      : {ajax_url}")

    section("2. Soumission réelle du formulaire (identité de test clairement marquée)")
    payload = {
        "prenom": "TEST-DIAGNOSTIC",
        "nom": MARQUEUR,
        "email": "test-diagnostic@example.invalid",
        "telephone": "0600000000",
        "energie": "elec",
        "fournisseur": "TEST",
        "offre": "Test diagnostic relais lead",
        "prix_annuel": 999,
        "economie": 1,
        "kwh": 3500,
        "option_tarifaire": "base",
        "lien_offre": "https://example.invalid/test",
        "logement": "maison", "surface": 75, "personnes": 2, "chauffage": "elec",
        "codepostal": "75001", "pdl": "", "pce": "",
        "src_post": "0",
    }
    data = {
        "action": "cme_cmp_lead",
        "nonce": nonce,
        "payload": json.dumps(payload),
    }
    resp = requests.post(ajax_url, data=data, timeout=20)
    print(f"  Statut HTTP de la reponse AJAX : {resp.status_code}")
    try:
        resp_json = resp.json()
        print(f"  Reponse JSON complete : {resp_json}")
        if resp_json.get("success"):
            d = resp_json.get("data", {})
            print(f"  -> email_sent = {d.get('email_sent')}")
            print(f"  -> gas (Google Sheets) = {d.get('gas')}")
        else:
            print(f"  ⚠️ success=False -- le nonce a probablement ete rejete ou une erreur serveur est survenue.")
    except Exception as e:
        print(f"  ❌ Reponse non-JSON ou erreur de parsing : {e}")
        print(f"  Corps brut (500 premiers caracteres) : {resp.text[:500]}")

    section("3. Vérification dans leads_convertis (BigQuery) — laisser quelques secondes au relais asynchrone")
    time.sleep(8)
    client = bigquery.Client(project=PROJECT_ID)
    df = client.query(f"""
        SELECT timestamp, tool, prenom, telephone, source_page, details
        FROM `{PROJECT_ID}.{DATASET_ID}.leads_convertis`
        WHERE tool = 'comparateur-energie'
          AND prenom = 'TEST-DIAGNOSTIC'
        ORDER BY timestamp DESC
        LIMIT 3
    """).to_dataframe()
    if df.empty:
        print("  ❌ AUCUNE ligne trouvée dans leads_convertis pour ce test -- le relais Cloud Run n'a PAS abouti "
              "(ou pas encore -- insert_rows_json est généralement immédiat).")
    else:
        print(f"  ✅ {len(df)} ligne(s) trouvée(s) -- le relais Cloud Run -> BigQuery FONCTIONNE :")
        for _, row in df.iterrows():
            print(f"    {dict(row)}")

    section(f"FIN DU TEST — marqueur unique pour nettoyage ultérieur si besoin : {MARQUEUR}")


if __name__ == "__main__":
    main()
