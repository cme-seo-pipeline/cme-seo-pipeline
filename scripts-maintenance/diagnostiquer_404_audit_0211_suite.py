"""
CME — Suite du diagnostic des 7 URLs 404 (diagnostiquer_404_audit_0211.py) :
ces 7 URLs sont introuvables a la fois dans historique_publications (notre
propre log de publication) ET comme post WordPress (meme en recherchant
tous les statuts, authentifie) -- ce qui ne dit pas si elles n'ont JAMAIS
existe, ou si elles ont existe puis ete supprimees DEFINITIVEMENT (purge de
la corbeille WordPress) par un mecanisme hors de ce repo (suppression
manuelle en wp-admin, notamment).

Ce script cherche des traces indirectes :
1. **01_raw.gsc_queries** -- si Google a deja crawle/indexe ces URLs, elles
   y laissent une trace (clics/impressions/dates), meme si le post est
   aujourd'hui supprime. Donne aussi une fenetre temporelle approximative
   et le VRAI volume de trafic perdu (donnee cle pour prioriser les 301).
2. **Sitemap WordPress live** -- si ces URLs sont encore listees dans le
   sitemap XML, c'est la source probable du 404 remonte par l'audit
   externe (un crawler suit le sitemap).
3. **Recherche WP par mot-cle** (plutot que par slug exact) pour chaque
   sujet, afin de proposer une page de remplacement vivante si une page
   tres proche existe deja sous un AUTRE slug (cas frequent documente dans
   ce projet : suffixe de date ajoute lors d'une collision, ou article
   reecrit sous un titre different).

LECTURE SEULE.
"""
import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

import requests

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)
TIMEOUT = 15

URLS_404 = [
    "https://www.comprendre-mon-energie.fr/solaire/systeme-solaire-combine/aides-systeme-solaire-combine-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/batterie-panneaux-solaires/aides-batterie-solaire-2026/",
    "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/augmentation-electricite-causes/",
    "https://www.comprendre-mon-energie.fr/solaire/panneaux-solaires/maprimerenov-panneaux-solaires-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/aides-chauffe-eau-solaire-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/prix-chauffe-eau-solaire-2026-cout-installation/",
    "https://www.comprendre-mon-energie.fr/solaire/panneaux-solaires/prix-panneaux-solaires-2026-tarifs/",
]

# Mots-cles de recherche WP pour trouver une page de remplacement vivante,
# derives manuellement du slug de chaque URL (pas d'automatisation fragile
# ici, seulement 7 URLs).
RECHERCHES = {
    URLS_404[0]: "systeme solaire combine aides",
    URLS_404[1]: "batterie solaire aides",
    URLS_404[2]: "augmentation electricite",
    URLS_404[3]: "panneaux solaires maprimerenov",
    URLS_404[4]: "chauffe-eau solaire aides",
    URLS_404[5]: "chauffe-eau solaire prix",
    URLS_404[6]: "panneaux solaires prix",
}


def main():
    client_bq = init_bigquery()

    print("=" * 100)
    print("1) TRACE DANS GOOGLE SEARCH CONSOLE (01_raw.gsc_queries)")
    print("=" * 100)
    for url in URLS_404:
        df = client_bq.query(f"""
            SELECT MIN(date) AS premiere_date, MAX(date) AS derniere_date,
                   SUM(clics) AS clics_total, SUM(impressions) AS impressions_total,
                   COUNT(DISTINCT query) AS nb_requetes_distinctes
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE page = '{url}'
        """).to_dataframe()
        row = df.iloc[0]
        print(f"\n### {url}")
        if row['premiere_date'] is None:
            print("    GSC : aucune ligne -- jamais vu par Google Search Console")
        else:
            print(f"    GSC : vu du {row['premiere_date']} au {row['derniere_date']} | "
                  f"clics={int(row['clics_total'])} | impressions={int(row['impressions_total'])} | "
                  f"{int(row['nb_requetes_distinctes'])} requete(s) distincte(s)")
            # top requetes
            df_q = client_bq.query(f"""
                SELECT query, SUM(clics) AS clics, SUM(impressions) AS impressions
                FROM `{PROJECT_ID}.01_raw.gsc_queries`
                WHERE page = '{url}'
                GROUP BY query ORDER BY impressions DESC LIMIT 5
            """).to_dataframe()
            for _, r in df_q.iterrows():
                print(f"        - {r['query']!r} : clics={int(r['clics'])}, impressions={int(r['impressions'])}")

    print("\n" + "=" * 100)
    print("2) PRESENCE DANS LE SITEMAP XML LIVE")
    print("=" * 100)
    try:
        r = requests.get(f"{WP_URL}/sitemap_index.xml", timeout=TIMEOUT)
        print(f"sitemap_index.xml -> HTTP {r.status_code}")
        sous_sitemaps = re.findall(r'<loc>([^<]+)</loc>', r.text) if r.status_code == 200 else []
        print(f"{len(sous_sitemaps)} sous-sitemap(s) trouve(s)")
    except Exception as e:
        print(f"Erreur sitemap_index.xml : {e}")
        sous_sitemaps = []

    sitemap_posts = [s for s in sous_sitemaps if 'post-sitemap' in s or 'sitemap.xml' in s.lower()]
    trouve_dans_sitemap = {url: False for url in URLS_404}
    for sm in sitemap_posts[:10]:
        try:
            r = requests.get(sm, timeout=TIMEOUT)
            for url in URLS_404:
                if url in r.text:
                    trouve_dans_sitemap[url] = True
        except Exception:
            continue
    for url, present in trouve_dans_sitemap.items():
        print(f"    {'PRESENT' if present else 'absent'} dans un sitemap post : {url}")

    print("\n" + "=" * 100)
    print("3) RECHERCHE D'UNE PAGE DE REMPLACEMENT VIVANTE (par mot-cle WP)")
    print("=" * 100)
    for url, mots_cles in RECHERCHES.items():
        print(f"\n### {url}")
        print(f"    Recherche WP : {mots_cles!r}")
        try:
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                params={"search": mots_cles, "per_page": 5, "_fields": "id,link,title"},
                timeout=TIMEOUT,
            )
            if r.status_code == 200 and r.json():
                for post in r.json():
                    titre = post.get('title', {}).get('rendered', '')
                    print(f"        candidat : {post.get('link')} -- {titre!r}")
            else:
                print(f"        aucun resultat (HTTP {r.status_code})")
        except Exception as e:
            print(f"        erreur recherche : {e}")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
