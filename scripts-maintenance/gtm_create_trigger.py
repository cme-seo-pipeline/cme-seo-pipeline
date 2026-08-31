"""GTM — Creation du declencheur Custom Event pour generate_lead (chantier G.1)."""
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

payload = {
    "name": "Custom Event - generate_lead",
    "type": "CUSTOM_EVENT",
    "customEventFilter": [{
        "type": "equals",
        "parameter": [
            {"type": "template", "key": "arg0", "value": "{{_event}}"},
            {"type": "template", "key": "arg1", "value": "generate_lead"}
        ]
    }]
}
r = requests.post(f"{BASE}/triggers", headers=HEADERS, json=payload)
print("Status:", r.status_code)
print(json.dumps(r.json(), indent=2, ensure_ascii=False))
