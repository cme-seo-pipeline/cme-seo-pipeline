import subprocess, requests

TOKEN = subprocess.check_output(["gcloud", "auth", "print-identity-token"], text=True).strip()

sql = """SELECT p.ID, MAX(CASE WHEN pm.meta_key='rank_math_title' THEN pm.meta_value END), MAX(CASE WHEN pm.meta_key='rank_math_focus_keyword' THEN pm.meta_value END) FROM wp_posts p LEFT JOIN wp_postmeta pm ON p.ID=pm.post_id AND pm.meta_key IN ('rank_math_title','rank_math_focus_keyword') WHERE p.post_status='publish' AND p.post_type IN ('post','page') GROUP BY p.ID LIMIT 5"""

cmd = f'db query "{sql}" --skip-column-names'

r = requests.get(
    "https://cme-seo-pipeline-217943559750.europe-west1.run.app/wp-shell",
    params={"cmd": cmd},
    headers={"Authorization": f"Bearer {TOKEN}"}
)
print(r.json())
