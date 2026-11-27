"""
CME — Diagnostic "Page has links to redirect" (audit Ahrefs du 21/11/2026).

Contexte : l'audit Ahrefs releve 81 pages (en croissance, +7 depuis le
14/11) contenant un lien interne qui pointe vers une URL qui redirige
(3xx) plutot que directement vers la destination finale -- cout SEO reel
(dilution de link equity, budget de crawl, latence) meme si le lien
"fonctionne" au sens ou le visiteur finit bien par arriver quelque part.

Pourquoi l'audit hebdomadaire existant (`auditer_liens_internes.py`) ne
l'a jamais remonte : il ne considere un lien "a probleme" que si
nb_redirections > 1 (une CHAINE de redirections) -- un lien qui redirige
UNE SEULE fois avant d'atteindre sa destination finale est compte comme
"OK" par ce script. C'est exactement ce que Ahrefs signale ici : un seul
saut suffit a etre sous-optimal, pas besoin d'une chaine.

Ce script, DISTINCT et LECTURE SEULE, reprend la meme extraction de liens
que `auditer_liens_internes.py` (meme regex, meme piege href-pas-forcement-
premier-attribut) mais avec le seuil Ahrefs : tout lien interne dont la
premiere reponse HTTP est deja un 3xx est signale, avec sa destination
finale (apres redirections) pour permettre une correction retroactive du
meme type que `fix_liens_morts_maillage_0211.py` (BeautifulSoup, dry-run
par defaut, jamais ecrit par ce script-ci).

USAGE :
  python3 diagnostiquer_liens_vers_redirections.py                # audit complet
  python3 diagnostiquer_liens_vers_redirections.py --limite=20     # test sur 20 articles

Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.
"""
import os
import re
import sys
import time
from urllib.parse import urljoin, urlparse
from collections import defaultdict

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_DOMAIN = "comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")

AUTH = (WP_USERNAME, WP_APP_PASSWORD)

# Meme piege que fix_cta_liens_retroactif.py / auditer_liens_internes.py :
# ne jamais supposer que href est le premier attribut de <a ...>.
PATTERN_A = re.compile(
    r'<a\s+([^>]*?href="([^"#][^"]*)"[^>]*)>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

TIMEOUT = 15
DELAI_ENTRE_REQUETES = 0.4
MAX_SAUTS_SUIVIS = 5  # garde-fou anti-boucle de redirection


def lister_tous_les_posts():
    posts = []
    page = 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            auth=AUTH,
            params={"per_page": 100, "page": page, "status": "publish", "context": "edit"},
            timeout=30,
        )
        if r.status_code != 200:
            print(f"  ⚠️ Arret pagination a la page {page} : HTTP {r.status_code}")
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
    return posts


def nettoyer_texte(txt):
    return re.sub(r'<[^>]+>', '', txt or "").strip()


def premiere_reponse_sans_suivre(url):
    """HEAD (repli GET si bloque) SANS suivre la redirection -- pour voir
    si la toute premiere reponse est deja un 3xx, meme seuil qu'Ahrefs."""
    try:
        resp = requests.head(url, timeout=TIMEOUT, allow_redirects=False)
        if resp.status_code in (403, 405) or resp.status_code >= 500:
            resp = requests.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True)
        return resp.status_code, resp.headers.get("Location"), None
    except Exception as e:
        return None, None, str(e)[:150]


def resoudre_destination_finale(url):
    """Suit les redirections (max MAX_SAUTS_SUIVIS) pour obtenir la
    destination finale, a des fins de proposition de correction."""
    courante = url
    for _ in range(MAX_SAUTS_SUIVIS):
        statut, location, erreur = premiere_reponse_sans_suivre(courante)
        if erreur or statut is None:
            return courante, statut, erreur
        if 300 <= statut < 400 and location:
            courante = urljoin(courante, location)
            continue
        return courante, statut, None
    return courante, None, "boucle de redirection (>5 sauts)"


def main():
    limite = None
    for arg in sys.argv:
        if arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])

    print("📥 Recuperation de tous les articles publies...")
    posts = lister_tous_les_posts()
    if limite:
        posts = posts[:limite]
        print(f"   (limite de test : {limite} articles)")
    print(f"   {len(posts)} articles a analyser\n")

    # url_source -> liste de {post_id, titre, lien_wp, texte_ancre}
    liens_par_cible = defaultdict(list)

    print("🔎 Extraction des liens internes dans le contenu...")
    for post in posts:
        post_id = post["id"]
        titre = nettoyer_texte(post.get("title", {}).get("rendered", ""))
        lien_wp = post.get("link", "")
        contenu = post.get("content", {}).get("raw") or post.get("content", {}).get("rendered", "")

        for match in PATTERN_A.finditer(contenu):
            href_brut = match.group(2)
            texte_ancre = nettoyer_texte(match.group(3))[:80]
            url_absolue = urljoin(WP_URL + "/", href_brut)

            if WP_DOMAIN not in urlparse(url_absolue).netloc:
                continue  # scope : liens internes uniquement, comme Ahrefs ici

            liens_par_cible[url_absolue].append({
                "post_id": post_id, "titre": titre[:70], "lien_wp": lien_wp,
                "texte_ancre": texte_ancre or "(sans texte)",
            })

    print(f"   {len(liens_par_cible)} URLs internes uniques ciblees\n")

    print("🌐 Verification de la toute PREMIERE reponse de chaque lien (sans suivre)...")
    redirections = []
    ok = 0

    for i, (url_cible, occurrences) in enumerate(liens_par_cible.items(), 1):
        statut, location, erreur = premiere_reponse_sans_suivre(url_cible)

        if statut is not None and 300 <= statut < 400:
            destination, statut_final, erreur_final = resoudre_destination_finale(url_cible)
            redirections.append({
                "url_source": url_cible,
                "statut_initial": statut,
                "destination_finale": destination,
                "statut_final": statut_final,
                "erreur_finale": erreur_final,
                "occurrences": occurrences,
            })
        else:
            ok += 1

        if i % 50 == 0:
            print(f"   ... {i}/{len(liens_par_cible)} verifies")

        time.sleep(DELAI_ENTRE_REQUETES)

    print(f"\n{'='*70}")
    print("RAPPORT — LIENS INTERNES POINTANT VERS UNE REDIRECTION")
    print(f"{'='*70}")
    print(f"Articles analyses              : {len(posts)}")
    print(f"URLs internes uniques ciblees   : {len(liens_par_cible)}")
    print(f"OK (reponse directe, pas de 3xx): {ok}")
    print(f"Liens pointant vers une redirection : {len(redirections)}")
    nb_articles_concernes = len({occ["post_id"] for r in redirections for occ in r["occurrences"]})
    print(f"Articles concernes (au moins 1 lien): {nb_articles_concernes}")
    print(f"{'='*70}")

    if not redirections:
        print("\n✅ Aucun lien interne ne pointe directement vers une redirection.")
        return

    print(f"\n⚠️ LIENS A CORRIGER ({len(redirections)}) :")
    for r in sorted(redirections, key=lambda x: len(x["occurrences"]), reverse=True):
        print(f"\n  🔗 {r['url_source']}")
        print(f"     Statut initial : HTTP {r['statut_initial']}")
        if r["erreur_finale"]:
            print(f"     ⚠️ Destination finale non resolue : {r['erreur_finale']}")
        else:
            print(f"     → Destination finale : {r['destination_finale']} (HTTP {r['statut_final']})")
        print(f"     Cite dans {len(r['occurrences'])} article(s) :")
        for occ in r["occurrences"][:5]:
            print(f"       - post_id={occ['post_id']} \"{occ['texte_ancre']}\" — {occ['titre']}")
            print(f"         {occ['lien_wp']}")
        if len(r["occurrences"]) > 5:
            print(f"       ... et {len(r['occurrences']) - 5} autre(s)")


if __name__ == "__main__":
    main()
