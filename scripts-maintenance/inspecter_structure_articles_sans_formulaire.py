"""
CME — Diagnostic ponctuel (lecture seule) : pourquoi des articles longs
(2000-4000+ mots) sont quand meme signales "sans formulaire" par
identifier_articles_sans_formulaire.py. Hypothese : ce sont des articles
anterieurs au pipeline IA (contenu redige/structure differemment, pas en
blocs <p>/<h2> plats), dont la structure HTML ne correspond pas a ce que
cme-cta-progressifs.php attend (enfants directs de .entry-content en
P/UL/OL/TABLE/FIGURE/BLOCKQUOTE).

Inspecte les tags de PREMIER NIVEAU du contenu stocke pour une poignee
de post_id donnes, pour confirmer ou infirmer cette hypothese.

Lecture seule.

USAGE :
  python3 inspecter_structure_articles_sans_formulaire.py
"""
import os
import sys
from collections import Counter

import requests
from bs4 import BeautifulSoup

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)

POST_IDS = [908, 2218, 3387, 3490, 11035, 709]


def main():
    for post_id in POST_IDS:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                          auth=AUTH, params={"context": "edit"}, timeout=20)
        if r.status_code != 200:
            print(f"post_id={post_id} : HTTP {r.status_code}\n")
            continue
        post = r.json()
        contenu = post["content"]["raw"] if "raw" in post.get("content", {}) else post["content"]["rendered"]
        soup = BeautifulSoup(contenu, "html.parser")
        enfants = [c for c in soup.contents if getattr(c, "name", None)]
        tags = Counter(c.name.upper() for c in enfants)
        print(f"post_id={post_id} | {post['link']}")
        print(f"  longueur contenu brut : {len(contenu)} caracteres")
        print(f"  nb enfants de 1er niveau : {len(enfants)}")
        print(f"  tags de 1er niveau : {dict(tags)}")
        if enfants:
            print(f"  premier enfant : <{enfants[0].name}> {enfants[0].get_text()[:80]!r}")
        print()


if __name__ == "__main__":
    main()
