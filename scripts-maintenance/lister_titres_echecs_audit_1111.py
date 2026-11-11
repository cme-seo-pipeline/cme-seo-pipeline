"""
CME — Recupere (lecture seule) les titres/URLs des 17 articles dont la
correction automatique a ete annulee par securite lors du run de l'audit
reglementaire du 11/11/2026 ("passage exact non retrouve").

LECTURE SEULE -- aucune ecriture.

USAGE :
  python3 lister_titres_echecs_audit_1111.py
"""
import requests

SITE = "https://www.comprendre-mon-energie.fr"
IDS = [7268, 11242, 9665, 9349, 9764, 6732, 6411, 8340, 11457, 12499, 7392, 7027, 7031, 7021, 7019, 5235, 9363]


def main():
    for pid in IDS:
        resp = requests.get(f"{SITE}/wp-json/wp/v2/posts/{pid}", params={"_fields": "id,link,title,modified"}, timeout=30)
        if resp.status_code != 200:
            print(f"  id={pid} | ❌ HTTP {resp.status_code}")
            continue
        p = resp.json()
        titre = (p.get("title") or {}).get("rendered", "")
        print(f"  id={pid} | {titre} | modifie: {p.get('modified')} | {p.get('link')}")


if __name__ == "__main__":
    main()
