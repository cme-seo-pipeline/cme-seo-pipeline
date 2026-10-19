"""
CME — Diagnostic du relais de tracking (/wp-json/cme/v1/log-lead).

Suite au correctif du 19/10 (routage same-origin via WordPress au lieu
d'un appel JS cross-origin direct vers Cloud Run), un nouveau test reel
(soumission de formulaire) montre toujours 0 ligne dans leads_convertis,
alors que le nouveau JS (relais same-origin) est bien confirme en prod
(verifie via curl+grep). Ce script isole ou ca casse maintenant, en
appelant directement le relais WordPress -- sans passer par un navigateur
ni par le JS -- depuis un runner avec acces reseau complet (contrairement
au sandbox Claude Code) :

1. POST direct sur https://www.comprendre-mon-energie.fr/wp-json/cme/v1/log-lead
   avec un payload de test identifiable (tool=diagnostic-relais-test,
   marqueur unique). Capture le code HTTP + corps de reponse.
   -> Si ce n'est pas un 200 : le probleme est sur la route WordPress
      elle-meme (REST API bloquee par un plugin de securite, 404/403,
      mod_security cPanel, etc.) -- AVANT meme d'atteindre notre code PHP.
2. Attend quelques secondes, puis cherche la ligne correspondante dans
   leads_convertis (par le marqueur unique).
   -> Si le POST a recu un 200 mais que la ligne n'apparait jamais : le
      probleme est dans le relais lui-meme (wp_remote_post qui echoue a
      atteindre Cloud Run depuis l'hebergement, pare-feu sortant cPanel,
      timeout, etc.) -- PAS cote navigateur/JS.
   -> Si la ligne apparait : le relais fonctionne bout en bout, le
      probleme est alors forcement cote navigateur (le JS n'envoie
      toujours pas la requete pour une autre raison a investiguer, par
      ex. un plugin de securite qui bloque le fetch/sendBeacon cote
      client, ou un souci specifique a sendBeacon avec ce navigateur).

LECTURE SEULE cote WordPress (un seul POST de test, pas de donnees
reelles). Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
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
RELAIS_URL = "https://www.comprendre-mon-energie.fr/wp-json/cme/v1/log-lead"


def main():
    marqueur = f"diag-{uuid.uuid4().hex[:12]}"
    payload = {
        "tool": "diagnostic-relais-test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_page": "https://www.comprendre-mon-energie.fr/contactez-un-expert/",
        "details": {"marqueur": marqueur},
    }

    print("=" * 70)
    print(f"1. POST direct sur {RELAIS_URL}")
    print(f"   Marqueur de ce test : {marqueur}")
    print("=" * 70)
    try:
        resp = requests.post(RELAIS_URL, json=payload, timeout=15)
        print(f"   Code HTTP : {resp.status_code}")
        print(f"   Corps de reponse (500 premiers caracteres) : {resp.text[:500]!r}")
        if resp.status_code != 200:
            print("\n⚠️ La route WordPress elle-meme ne repond pas correctement -- "
                  "le probleme est avant d'atteindre le relais PHP (securite, cache, routing).")
    except Exception as e:
        print(f"   ❌ Erreur reseau en appelant la route WordPress : {e}")
        print("\n⚠️ La route est injoignable depuis l'exterieur -- a verifier en priorite.")

    print("\n" + "=" * 70)
    print("2. Attente 10s puis recherche du marqueur dans leads_convertis...")
    print("=" * 70)
    time.sleep(10)
    client = bigquery.Client(project=PROJECT_ID)
    try:
        df = client.query(f"""
            SELECT timestamp, tool, details, source_page
            FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
            WHERE tool = 'diagnostic-relais-test'
              AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE)
            ORDER BY timestamp DESC
            LIMIT 10
        """).to_dataframe()
        trouve = df['details'].astype(str).str.contains(marqueur).any() if not df.empty else False
        if trouve:
            print(f"✅ Ligne trouvee avec le marqueur {marqueur} -- le relais WordPress -> Cloud Run -> "
                  "BigQuery fonctionne bout en bout. Le probleme (si le test navigateur echoue encore) "
                  "est donc cote navigateur/JS, pas cote serveur.")
        else:
            print(f"❌ Aucune ligne avec le marqueur {marqueur} trouvee apres 10s.")
            if not df.empty:
                print("   (Des lignes 'diagnostic-relais-test' existent mais sans ce marqueur precis -- "
                      "verifier manuellement :)")
                print(df.to_string())
            print("\n⚠️ Si le point 1 montrait un 200 OK mais que la ligne n'arrive jamais ici : "
                  "le probleme est dans le relais PHP lui-meme (wp_remote_post qui echoue a "
                  "joindre Cloud Run depuis l'hebergement -- pare-feu sortant, timeout, etc.), "
                  "pas cote navigateur.")
    except Exception as e:
        print(f"⚠️ Erreur BigQuery : {e}")


if __name__ == "__main__":
    main()
