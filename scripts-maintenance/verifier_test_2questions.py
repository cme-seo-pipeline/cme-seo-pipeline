"""
CME — Verification ciblee du test de deploiement du formulaire a 2
questions (24/10/2026, soir). L'operateur rapporte un test reussi "de bout
en bout" juste apres le deploiement cPanel, mais une premiere requete
(verifier_leads_formulaire_inline.py, fenetre de 48h) montre 0 ligne
contact-expert-inline recente -- a eclaircir avant de cloturer la journee.

1. Toutes les lignes leads_convertis des 2 dernieres heures, tout outil
   confondu (plus large que 48h cible juste le present, pour voir si
   AUTRE CHOSE est arrive recemment, meme sous un autre tool).
2. Dernier essai de relais vu cote WordPress (/wp-json/cme/v1/log-lead-debug)
   -- donne un timestamp meme si rien n'atteint BigQuery.
3. Nouveau test de bout en bout complet (meme pattern que
   diagnostiquer_relais_tracking.py), pour confirmer que le relais est bien
   fonctionnel A CET INSTANT.

LECTURE SEULE (sauf l'unique POST de test standard de l'etape 3, deja une
convention etablie du projet). Necessite GOOGLE_APPLICATION_CREDENTIALS.
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
DEBUG_URL = "https://www.comprendre-mon-energie.fr/wp-json/cme/v1/log-lead-debug"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("=" * 70)
    print("1. leads_convertis -- TOUTES les lignes des 2 dernieres heures, tout outil")
    print("=" * 70)
    try:
        df = client.query(f"""
            SELECT timestamp, tool, prenom, telephone, source_page, source_post_id
            FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
            ORDER BY timestamp DESC
        """).to_dataframe()
        if df.empty:
            print("   ⚠️ 0 ligne, tout outil confondu, sur les 2 dernieres heures.")
        else:
            print(df.to_string(index=False))
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")

    print("\n" + "=" * 70)
    print(f"2. Dernier essai de relais vu cote WordPress ({DEBUG_URL})")
    print("=" * 70)
    try:
        resp = requests.get(DEBUG_URL, timeout=15)
        print(f"   Code HTTP : {resp.status_code}")
        print(f"   Corps : {resp.text[:500]}")
    except Exception as e:
        print(f"   ⚠️ Erreur reseau : {e}")

    print("\n" + "=" * 70)
    print("3. Nouveau test de bout en bout, maintenant")
    print("=" * 70)
    marqueur = f"verif2q-{uuid.uuid4().hex[:12]}"
    payload = {
        "tool": "diagnostic-relais-test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {"marqueur": marqueur, "origine": "verifier_test_2questions"},
    }
    try:
        resp = requests.post(RELAIS_URL, json=payload, timeout=15)
        print(f"   POST {RELAIS_URL} -> {resp.status_code} {resp.text[:200]!r}")
    except Exception as e:
        print(f"   ❌ Erreur reseau : {e}")

    time.sleep(10)
    try:
        df2 = client.query(f"""
            SELECT timestamp, details
            FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
            WHERE tool = 'diagnostic-relais-test'
              AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE)
            ORDER BY timestamp DESC
        """).to_dataframe()
        trouve = df2['details'].astype(str).str.contains(marqueur).any() if not df2.empty else False
        print(f"   Marqueur '{marqueur}' retrouve dans BigQuery : {'✅ OUI -- relais toujours sain' if trouve else '❌ NON -- relais en panne MAINTENANT'}")
    except Exception as e:
        print(f"   ⚠️ Erreur BigQuery : {e}")


if __name__ == "__main__":
    main()
