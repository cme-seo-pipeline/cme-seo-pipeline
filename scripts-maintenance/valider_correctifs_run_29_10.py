"""
CME — Validation en conditions reelles (lecture seule) des correctifs
pousses le 28/10 (commit ddbdc3c, 4 ajustements titres/meta + suppression
H1 en double) et le 28/10 soir (commit 1b193ae, fuite "Resume redactionnel").
Le run quotidien du 29/10 09:05 UTC (publication-quotidienne.yml,
run 40846884004) a tourne sur le commit 1b193ae -- donc le premier run
reel a beneficier des DEUX correctifs simultanement.

Pour chaque article publie aujourd'hui (date_publication = CURRENT_DATE,
heure UTC) :
  1. Pas de <h1> dans le contenu stocke (regle 6 corrigee)
  2. Pas de marqueur de fuite "Resume redactionnel" en fin de contenu
     (regle 9 + filet de securite code)
  3. Longueur meta_description (via le champ WP) dans la fourchette visee
  4. mot_cle_principal : pas de doublon exact entre articles du meme run

LECTURE SEULE -- aucune ecriture.
Necessite WP_APP_PASSWORD et GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 valider_correctifs_run_29_10.py
"""
import os
import re
import sys
from collections import Counter

import requests

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)
    df = client.query(f"""
        SELECT post_id, titre, mot_cle, url_wp, silo, sous_silo_strategique, date_publication
        FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
        WHERE DATE(date_publication) = CURRENT_DATE()
        ORDER BY date_publication
    """).to_dataframe()

    print(f"📅 {len(df)} article(s) publie(s) aujourd'hui (date_publication = CURRENT_DATE)\n")
    if df.empty:
        print("⚠️ Aucun article publie aujourd'hui pour l'instant -- rien a valider.")
        return

    print("=" * 90)
    print("1) Doublons de mot_cle_principal au sein du run d'aujourd'hui")
    print("=" * 90)
    compte = Counter(df["mot_cle"].str.lower().str.strip())
    doublons = {k: v for k, v in compte.items() if v > 1}
    if doublons:
        print(f"  ❌ {len(doublons)} mot(s)-cle(s) duplique(s) : {doublons}")
    else:
        print("  ✅ Aucun mot_cle_principal duplique dans le run d'aujourd'hui")

    print("\n" + "=" * 90)
    print("2) Verification par article (H1 en double, fuite resume, longueur meta)")
    print("=" * 90)

    fuite_pattern = re.compile(
        r"r[ée]sum[ée]\s+[ée]ditorial|r[ée]sum[ée]\s+r[ée]dactionnel"
        r"|respect\s+des\s+r[èe]gles\s*:|r[èe]gles\s+respect[ée]es\s*:"
        r"|✅.{0,40}(html|maillage|apostrophe|cta|chiffre)",
        re.IGNORECASE,
    )

    for _, art in df.iterrows():
        post_id = int(art["post_id"])
        print(f"\n  post_id={post_id} | {art['titre']} | {art['url_wp']}")
        try:
            r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                              auth=AUTH, params={"context": "edit"}, timeout=20)
            if r.status_code != 200:
                print(f"    ⚠️ HTTP {r.status_code} -- impossible de recuperer le contenu")
                continue
            post = r.json()
            contenu = post["content"]["raw"] if "raw" in post.get("content", {}) else post["content"]["rendered"]
            meta = post.get("yoast_head_json", {}).get("description") or post.get("excerpt", {}).get("raw", "")

            a_h1 = bool(re.search(r"<h1[\s>]", contenu, re.IGNORECASE))
            print(f"    {'❌' if a_h1 else '✅'} <h1> dans le contenu : {'present (BUG)' if a_h1 else 'absent (attendu)'}")

            m_fuite = fuite_pattern.search(contenu)
            print(f"    {'❌' if m_fuite else '✅'} Fuite 'Resume redactionnel' : {'DETECTEE' if m_fuite else 'absente'}")
            if m_fuite:
                idx = m_fuite.start()
                print(f"       extrait : ...{contenu[max(0, idx-30):idx+100]!r}...")

            if meta:
                longueur = len(meta)
                dans_fourchette = 140 <= longueur <= 160
                print(f"    {'✅' if dans_fourchette else '⚠️'} Longueur meta_description : {longueur} caracteres")
            else:
                print("    ⚠️ meta_description introuvable via l'API (yoast_head_json absent)")

        except Exception as e:
            print(f"    ⚠️ Erreur : {e}")


if __name__ == "__main__":
    main()
