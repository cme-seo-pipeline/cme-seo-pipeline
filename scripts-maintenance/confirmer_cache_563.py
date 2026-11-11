"""
CME — Confirme l'hypothese de cache sur l'endpoint REST pour id=563.

Le diagnostic precedent (diagnostiquer_563_dom_live.py) a montre que le
DOM live (15 enfants directs de .entry-content, classes rank-math-block/
wp-block-spacer/carte-fournisseur) ne correspond PAS du tout a la
structure obtenue via `requests.get(.../wp-json/wp/v2/posts/563)` sans
parametre anti-cache (53 "enfants effectifs", bloc <script>/<style>/
<form> legacy jamais vu en live). Hypothese : la requete REST sans
cache-buster servait une reponse mise en cache (perimee), pendant que la
page live (chargee avec ?t=$RANDOM) contourne ce cache.

Ce script refait la meme requete REST, cette fois AVEC un parametre
anti-cache, pour confirmer si le contenu renvoye change.

LECTURE SEULE.
"""
import random

import requests

SITE = "https://www.comprendre-mon-energie.fr"


def main():
    print("=" * 80)
    print("Requete SANS cache-buster (meme forme que le script precedent) :")
    print("=" * 80)
    r1 = requests.get(f"{SITE}/wp-json/wp/v2/posts/563", params={"_fields": "id,content,modified"}, timeout=30)
    html1 = (r1.json().get("content") or {}).get("rendered", "") if r1.status_code == 200 else ""
    print(f"  HTTP {r1.status_code} | longueur contenu = {len(html1)} | modified = {r1.json().get('modified') if r1.status_code == 200 else 'n/a'}")
    print(f"  Contient 'rank-math-block' ? {'rank-math-block' in html1}")
    print(f"  Contient un bloc <script> imbrique ? {'<script' in html1}")

    print()
    print("=" * 80)
    print("Requete AVEC cache-buster (?t=$RANDOM en query) :")
    print("=" * 80)
    t = random.randint(100000, 999999)
    r2 = requests.get(
        f"{SITE}/wp-json/wp/v2/posts/563",
        params={"_fields": "id,content,modified", "t": t},
        timeout=30,
    )
    html2 = (r2.json().get("content") or {}).get("rendered", "") if r2.status_code == 200 else ""
    print(f"  HTTP {r2.status_code} | longueur contenu = {len(html2)} | modified = {r2.json().get('modified') if r2.status_code == 200 else 'n/a'}")
    print(f"  Contient 'rank-math-block' ? {'rank-math-block' in html2}")
    print(f"  Contient un bloc <script> imbrique ? {'<script' in html2}")

    print()
    print("=" * 80)
    print("Conclusion")
    print("=" * 80)
    if html1 == html2:
        print("  Memes deux reponses -- PAS un probleme de cache sur l'endpoint REST lui-meme.")
        print("  (il faudra chercher une autre explication a l'ecart avec le DOM live)")
    else:
        print("  ⚠️ Les deux reponses DIFFERENT -- confirme un cache perime sur l'endpoint")
        print("  REST sans cache-buster. Le contenu reel et actuel est celui avec 't='.")


if __name__ == "__main__":
    main()
