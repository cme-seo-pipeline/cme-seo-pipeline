"""GTM — Creation et publication de version (chantier G.1).

NOTE HISTORIQUE : 2 echecs avant succes.
1. /create_version (slash) -> 404. GTM API v2 utilise la syntaxe
   "custom method" avec deux-points : :create_version, pas un sous-chemin REST.
2. Avec la bonne syntaxe : 403 "insufficient authentication scopes" sur
   CreateContainerVersion. Scope manquant : tagmanager.edit.containerversions,
   distinct de tagmanager.publish (qui ne couvre que la PUBLICATION d'une
   version deja creee, pas sa CREATION).
"""
import subprocess, json
from google.oauth2 import service_account
import google.auth.transport.requests
import requests

cle = subprocess.check_output(
    ["gcloud", "secrets", "versions", "access", "latest", "--secret=SA_GTM_PRIVATE_KEY"], text=True
)
creds = service_account.Credentials.from_service_account_info(
    json.loads(cle),
    scopes=['https://www.googleapis.com/auth/tagmanager.edit.containers',
            'https://www.googleapis.com/auth/tagmanager.edit.containerversions',
            'https://www.googleapis.com/auth/tagmanager.publish']
)
creds.refresh(google.auth.transport.requests.Request())

ACC, CONT, WS = "6358809613", "254350296", "8"
HEADERS = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
BASE = f"https://www.googleapis.com/tagmanager/v2/accounts/{ACC}/containers/{CONT}"

payload = {"name": "G.1 - Tracking unifie 4 outils (generate_lead via dataLayer)"}
r = requests.post(f"{BASE}/workspaces/{WS}:create_version", headers=HEADERS, json=payload)
print("STATUS creation:", r.status_code)
data = r.json()
version_id = data.get('containerVersion', {}).get('containerVersionId')
print("Version ID:", version_id)

if version_id:
    r2 = requests.post(f"{BASE}/versions/{version_id}:publish", headers=HEADERS)
    print("STATUS publication:", r2.status_code)
