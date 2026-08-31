"""GTM — Reconfigure la balise GA4 Event pour ecouter le declencheur generate_lead (chantier G.1)."""
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
            'https://www.googleapis.com/auth/tagmanager.publish']
)
creds.refresh(google.auth.transport.requests.Request())

ACC, CONT, WS = "6358809613", "254350296", "8"
HEADERS = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
BASE = f"https://www.googleapis.com/tagmanager/v2/accounts/{ACC}/containers/{CONT}/workspaces/{WS}"

r = requests.get(f"{BASE}/tags/6", headers=HEADERS)
tag = r.json()
print("AVANT - firingTriggerId:", tag.get('firingTriggerId'))
tag['firingTriggerId'] = ["9"]  # 9 = Custom Event - generate_lead (cree par gtm_create_trigger.py)
r2 = requests.put(f"{BASE}/tags/6", headers=HEADERS, json=tag)
print("Status update:", r2.status_code)
print("APRES - firingTriggerId:", r2.json().get('firingTriggerId'))
