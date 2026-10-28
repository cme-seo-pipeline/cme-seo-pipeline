"""
CME — Diagnostic ponctuel (lecture seule) de la duplication H1/H2 signalee
par l'operateur le 28/10/2026, suite a la cartographie titres/meta.

Piste forte deja identifiee par lecture de code (pipeline.py) : le prompt
de redaction (rediger_article) donne explicitement au contenu de l'article
"- Titre H1 : {titre_seo}" et REGLE 6 "Commence DIRECTEMENT par
<h1>...</h1>" -- donc le corps HTML de l'article contient lui-meme un
<h1>. Or le payload WordPress envoie SEPAREMENT "title": titre_seo comme
titre du post -- que le theme WordPress rend generalement lui-meme en
<h1> dans le template d'article. Resultat possible : DEUX <h1> sur la
meme page (un du theme, un du contenu), toujours avec le meme texte.

Ce script lit le contenu brut reel (context=edit, contourne le cache) de
quelques articles publies via l'API REST WordPress et compte les
occurrences de h1/h2 DANS LE CONTENU STOCKE, pour confirmer avant de
toucher au prompt.

Lecture seule -- aucune ecriture.

USAGE :
  python3 diagnostiquer_duplication_h1_h2.py --limite=10

Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.
"""
import os
import re
import sys

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")

AUTH = (WP_USERNAME, WP_APP_PASSWORD)


def parse_args():
    limite = 10
    for arg in sys.argv:
        if arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])
    return limite


def main():
    limite = parse_args()
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/posts",
        params={"per_page": limite, "orderby": "date", "order": "desc", "context": "edit"},
        auth=AUTH, timeout=30,
    )
    r.raise_for_status()
    posts = r.json()

    print(f"🔎 {len(posts)} articles les plus recents\n")

    for post in posts:
        post_id = post["id"]
        titre_post = post["title"]["raw"] if isinstance(post["title"], dict) else post["title"]["rendered"]
        contenu = post["content"]["raw"] if isinstance(post["content"], dict) and "raw" in post["content"] else post["content"]["rendered"]

        h1_matches = re.findall(r"<h1[^>]*>(.*?)</h1>", contenu, re.IGNORECASE | re.DOTALL)
        h2_matches = re.findall(r"<h2[^>]*>(.*?)</h2>", contenu, re.IGNORECASE | re.DOTALL)
        h1_textes = [re.sub(r"<[^>]+>", "", h).strip() for h in h1_matches]
        h2_textes = [re.sub(r"<[^>]+>", "", h).strip() for h in h2_matches]

        print(f"📄 post_id={post_id} — titre WP (champ title) : {titre_post}")
        print(f"   nb <h1> DANS LE CONTENU : {len(h1_textes)}")
        for h in h1_textes:
            identique = " [IDENTIQUE au titre WP]" if h.strip() == titre_post.strip() else ""
            print(f"     - {h}{identique}")
        print(f"   nb <h2> DANS LE CONTENU : {len(h2_textes)}")
        for h in h2_textes:
            identique_titre = " [IDENTIQUE au titre WP]" if h.strip() == titre_post.strip() else ""
            identique_h1 = " [IDENTIQUE a un <h1>]" if h.strip() in h1_textes else ""
            print(f"     - {h}{identique_titre}{identique_h1}")
        # H2 dupliques entre eux dans le MEME article
        doublons_h2 = {h for h in h2_textes if h2_textes.count(h) > 1}
        if doublons_h2:
            print(f"   ⚠️ H2 repetes PLUSIEURS FOIS dans le meme article : {doublons_h2}")
        print()


if __name__ == "__main__":
    main()
