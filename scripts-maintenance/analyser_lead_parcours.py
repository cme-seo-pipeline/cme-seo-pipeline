"""
CME — Analyse du parcours d'un lead specifique (lecture seule).

Suite au constat du 24/10 : le lead du 22/10 14:39:56 UTC
(tool=contact-expert-inline, telephone=0607112671, email=lionel.nore@gmail.com,
source_post_id=5502) a ete classe par erreur comme "test" avec les 3 autres
lignes du meme jour -- correction : seules les lignes utilisant
o.blal@decodetheself.com sont des tests identifies (pattern du nom de
l'operateur). Celle-ci a un email/telephone distincts : potentiellement un
vrai visiteur. Ce script reconstruit ce qu'on peut savoir de son parcours a
partir de nos donnees, sans aucune ecriture :

1. Toutes les lignes leads_convertis (tout outil, tout historique) pour ce
   telephone OU cet email -- voir si la personne est deja connue ailleurs.
2. Detail brut de la ligne du 22/10 14:39:56 (colonne 'details' complete).
3. Identification de l'article (post_id=5502) via l'API REST WordPress
   publique (titre, lien, categorie/silo) -- le runner GitHub a l'acces
   reseau complet au site live.
4. Trafic GA4 sur cette page (si synchronise) autour du 22/10, pour
   contextualiser (combien de sessions ce jour-la sur cet article).

LECTURE SEULE. Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
"""
import sys
import os

import requests

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"

TELEPHONE_CIBLE = "0607112671"
EMAIL_CIBLE = "lionel.nore@gmail.com"
POST_ID_CIBLE = 5502

WP_BASE = "https://www.comprendre-mon-energie.fr/wp-json/wp/v2"


def run(client, titre, sql):
    print("=" * 70)
    print(titre)
    print("=" * 70)
    try:
        df = client.query(sql).to_dataframe()
        if df.empty:
            print("   (0 ligne)")
        else:
            print(df.to_string(index=False))
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")
    print()


def main():
    client = bigquery.Client(project=PROJECT_ID)

    run(client, f"1. Historique complet pour telephone='{TELEPHONE_CIBLE}' OU email='{EMAIL_CIBLE}'", f"""
        SELECT timestamp, tool, prenom, telephone, email, code_postal, source_page, source_post_id, details
        FROM `{TABLE}`
        WHERE telephone = '{TELEPHONE_CIBLE}' OR email = '{EMAIL_CIBLE}'
        ORDER BY timestamp
    """)

    print("=" * 70)
    print("2. Identification de l'article (post_id=5502) via l'API REST WordPress")
    print("=" * 70)
    article_link = None
    article_slug = None
    try:
        resp = requests.get(f"{WP_BASE}/posts/{POST_ID_CIBLE}", timeout=15)
        print(f"   Code HTTP : {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            article_link = data.get("link")
            article_slug = data.get("slug")
            titre_rendu = data.get("title", {}).get("rendered", "?")
            date_pub = data.get("date", "?")
            print(f"   Titre     : {titre_rendu}")
            print(f"   Lien      : {article_link}")
            print(f"   Slug      : {article_slug}")
            print(f"   Publie le : {date_pub}")
            cats = data.get("categories", [])
            print(f"   Categories (IDs) : {cats}")
        else:
            print(f"   Corps : {resp.text[:300]!r}")
    except Exception as e:
        print(f"   ❌ Erreur reseau : {e}")
    print()

    print("=" * 70)
    print("3. Trafic GA4 sur cette page -- si synchronise")
    print("=" * 70)
    try:
        if article_slug:
            df = client.query(f"""
                SELECT date, sessions, page_views, bounce_rate, conversions
                FROM `{PROJECT_ID}.01_raw.ga4_pages`
                WHERE page_path LIKE '%{article_slug}%'
                ORDER BY date DESC
                LIMIT 15
            """).to_dataframe()
            if df.empty:
                print(f"   ⚠️ Aucune ligne GA4 pour un chemin contenant '{article_slug}'.")
            else:
                print(df.to_string(index=False))
        else:
            print("   (slug introuvable a l'etape 2, requete GA4 non tentee)")
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")


if __name__ == "__main__":
    main()
