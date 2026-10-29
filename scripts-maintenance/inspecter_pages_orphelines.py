"""
CME — Inspection (lecture seule) des 4 pages orphelines signalees par
l'operateur le 29/10/2026, pour proposer un maillage interne correctif
coherent avec la strategie du site (liens contextuels "Pour aller plus
loin", meme gabarit que celui deja observe dans le contenu existant --
ex. post_id=11035 : "Pour aller plus loin, consultez notre guide sur le
cheque energie.").

Pour chaque page orpheline :
  - recupere son titre, son silo/sous-silo (via historique_publications),
    ses H2 (pour comprendre le sujet exact).
  - liste les articles les plus recents du MEME sous-silo (candidats
    naturels pour y ajouter un lien entrant), avec leur titre et leur URL.

LECTURE SEULE -- aucune ecriture.
USAGE : python3 inspecter_pages_orphelines.py
"""
import os
import re
import sys

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

PAGES_ORPHELINES = [
    "https://www.comprendre-mon-energie.fr/electricite/demenagement/changer-fournisseur-electricite-demenagement/",
    "https://www.comprendre-mon-energie.fr/aide-energetique/aides-renovation-toiture/demarches-conditions-aides-renovation-toiture/",
    "https://www.comprendre-mon-energie.fr/electricite/compteur/consommation-electrique-mesure-optimisation/",
    "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/justificatif-de-domicile/",
]


def recuperer_post_par_url(url):
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts", auth=AUTH,
                      params={"slug": slug, "context": "edit"}, timeout=20)
    if r.status_code == 200 and r.json():
        return r.json()[0]
    return None


def main():
    client = bigquery.Client(project=PROJECT_ID)

    for url in PAGES_ORPHELINES:
        print("=" * 100)
        print(f"PAGE ORPHELINE : {url}")
        print("=" * 100)
        post = recuperer_post_par_url(url)
        if not post:
            print("  ⚠️ Introuvable via l'API REST (slug non trouve).")
            continue
        post_id = post["id"]
        titre = post["title"]["rendered"]
        contenu = post["content"]["raw"] if "raw" in post.get("content", {}) else post["content"]["rendered"]
        h2s = re.findall(r"<h2[^>]*>(.*?)</h2>", contenu, re.IGNORECASE | re.DOTALL)
        print(f"  post_id={post_id} | {titre}")
        print(f"  H2 : {[re.sub('<[^>]+>', '', h).strip() for h in h2s[:6]]}")

        df_meta = client.query(f"""
            SELECT silo, sous_silo_strategique
            FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
            WHERE post_id = {post_id}
        """).to_dataframe()
        if df_meta.empty:
            print("  ⚠️ Pas de ligne dans historique_publications pour ce post_id (article legacy ?)")
            continue
        silo = df_meta.iloc[0]["silo"]
        sous_silo = df_meta.iloc[0]["sous_silo_strategique"]
        print(f"  Silo : {silo} | Sous-silo : {sous_silo}")

        print(f"\n  → Candidats recents du meme sous-silo (pour y ajouter un lien entrant) :")
        silo_sql = silo.replace("'", "\\'")
        sous_silo_sql = sous_silo.replace("'", "\\'")
        df_candidats = client.query(f"""
            SELECT post_id, titre, url_wp, date_publication
            FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
            WHERE silo = '{silo_sql}'
              AND sous_silo_strategique LIKE '{sous_silo_sql}%'
              AND post_id != {post_id}
            ORDER BY date_publication DESC
            LIMIT 8
        """).to_dataframe()
        if df_candidats.empty:
            print("    ⚠️ Aucun autre article dans ce sous-silo precis.")
        else:
            for _, c in df_candidats.iterrows():
                print(f"    post_id={c['post_id']} | {c['titre']} | {c['url_wp']}")
        print()


if __name__ == "__main__":
    main()
