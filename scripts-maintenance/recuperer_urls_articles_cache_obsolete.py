"""
CME — Recupere (lecture seule) les URLs des 4 articles identifies par
diagnostiquer_cta_manquant_et_cache_obsolete.py comme montrant encore la
signature de l'ANCIENNE version du mecanisme CTA apres le deploiement du
04/11 (cache LiteSpeed probablement obsolete pour ces pages precises) :
post_id 4701, 4745, 5005, 5945.

LECTURE SEULE -- aucune ecriture.

USAGE :
  python3 recuperer_urls_articles_cache_obsolete.py
"""
import requests

SITE = "https://www.comprendre-mon-energie.fr"
POST_IDS = [4701, 4745, 5005, 5945]


def main():
    for pid in POST_IDS:
        resp = requests.get(f"{SITE}/wp-json/wp/v2/posts/{pid}", params={"_fields": "id,link,title"}, timeout=30)
        if resp.status_code != 200:
            print(f"  id={pid} | ❌ HTTP {resp.status_code}")
            continue
        p = resp.json()
        titre = (p.get("title") or {}).get("rendered", "")
        print(f"  id={pid} | {titre} | {p.get('link')}")


if __name__ == "__main__":
    main()
