import subprocess, requests, json

def get_identity_token():
    return subprocess.check_output(["gcloud", "auth", "print-identity-token"], text=True).strip()

URL = "https://cme-seo-pipeline-217943559750.europe-west1.run.app/wp-deploy"
TOKEN = get_identity_token()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

fichiers = [
    ("wordpress-plugins/comparateur-energie/comparateur-energie.php",
     "/home/jolu5920/public_html/comprendre-mon-energie.com/wp-content/plugins/comparateur-energie/comparateur-energie.php"),
    ("wordpress-plugins/simulateur-aides/simulateur-aides.php",
     "/home/jolu5920/public_html/comprendre-mon-energie.com/wp-content/plugins/plugin-simulateur-aides-v1.0.7/simulateur-aides.php"),
    ("wordpress-plugins/simulateur-solaire/simulateur-solaire.php",
     "/home/jolu5920/public_html/comprendre-mon-energie.com/wp-content/plugins/plugin-simulateur-solaire-v3.8.3/simulateur-solaire.php"),
]

for local, distant in fichiers:
    with open(local, "r", encoding="utf-8") as f:
        contenu = f.read()
    r = requests.post(URL, headers=HEADERS, json={"chemin_distant": distant, "contenu": contenu}, timeout=30)
    print(local, "->", r.status_code, r.json())
