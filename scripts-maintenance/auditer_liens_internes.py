"""
CME — Audit exhaustif des liens presents DANS le contenu des articles.

Complete l'audit technique existant (`auditer_site_technique` dans
pipeline.py), qui ne verifie que les 437 pages connues elles-memes
(wp_url_mapping) -- pas les liens qu'elles contiennent. Ce script lit le
contenu reel de chaque article publie, en extrait TOUS les liens <a href="...">
(internes ET externes), et verifie que chacun repond correctement.

Volontairement construit en Python simple (requests + regex), execute sur
un runner GitHub Actions (gratuit dans les limites habituelles) plutot que
sur Cloud Run / BigQuery -- decision explicite pour ne pas alourdir la
facture Cloud de l'ecosysteme ORCAAS (deja jugee a l'abandon et couteuse).
Aucune dependance a un outil tiers payant (Screaming Frog avait deja ete
ecarte, cf. decision du 31/08 dans pipeline.py).

Script de LECTURE SEULE -- ne modifie jamais le contenu des articles.

USAGE :
  python3 auditer_liens_internes.py                # audit complet
  python3 auditer_liens_internes.py --limite=20     # teste sur 20 articles seulement

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

# Capture toute balise <a ...href="..."...> quelle que soit la position de
# href parmi les attributs (meme piege que fix_cta_liens_retroactif.py :
# ne jamais supposer que href est le premier attribut).
PATTERN_A = re.compile(
    r'<a\s+([^>]*?href="([^"#][^"]*)"[^>]*)>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

TIMEOUT = 15
DELAI_ENTRE_REQUETES = 0.4  # menagement de l'hebergement mutualise


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

    # url -> liste de {post_id, titre, lien_wp, texte_ancre}
    liens_par_cible = defaultdict(list)

    print("🔎 Extraction des liens dans le contenu...")
    for post in posts:
        post_id = post["id"]
        titre = nettoyer_texte(post.get("title", {}).get("rendered", ""))
        lien_wp = post.get("link", "")
        contenu = post.get("content", {}).get("raw") or post.get("content", {}).get("rendered", "")

        for match in PATTERN_A.finditer(contenu):
            href_brut = match.group(2)
            texte_ancre = nettoyer_texte(match.group(3))[:80]

            # Resout les liens relatifs (/page/) en URL absolue sur le domaine.
            url_absolue = urljoin(WP_URL + "/", href_brut)
            liens_par_cible[url_absolue].append({
                "post_id": post_id, "titre": titre[:70], "lien_wp": lien_wp,
                "texte_ancre": texte_ancre or "(sans texte)",
            })

    print(f"   {len(liens_par_cible)} URLs cibles uniques trouvees (internes + externes)\n")

    print("🌐 Verification de chaque lien (HTTP)...")
    problemes = []
    externes_problemes = []
    ok = 0

    for i, (url_cible, occurrences) in enumerate(liens_par_cible.items(), 1):
        est_interne = WP_DOMAIN in urlparse(url_cible).netloc

        try:
            resp = requests.head(url_cible, timeout=TIMEOUT, allow_redirects=True)
            if resp.status_code >= 400:
                # Certains serveurs/WAF bloquent ou gerent mal HEAD -- on
                # retente en GET avant de conclure a un lien casse, pour
                # eviter les faux positifs.
                resp = requests.get(url_cible, timeout=TIMEOUT, allow_redirects=True, stream=True)
            statut = resp.status_code
            nb_redirections = len(resp.history)
        except Exception as e:
            statut = None
            nb_redirections = 0
            erreur = str(e)[:150]
        else:
            erreur = None

        est_casse = statut is None or statut >= 400
        est_redirection_longue = statut is not None and statut < 400 and nb_redirections > 1

        if est_casse or est_redirection_longue:
            entree = {
                "url": url_cible, "interne": est_interne, "statut": statut,
                "erreur": erreur, "nb_redirections": nb_redirections,
                "occurrences": occurrences,
            }
            if est_interne:
                problemes.append(entree)
            else:
                externes_problemes.append(entree)
        else:
            ok += 1

        if i % 50 == 0:
            print(f"   ... {i}/{len(liens_par_cible)} verifies")

        time.sleep(DELAI_ENTRE_REQUETES)

    print(f"\n{'='*70}")
    print("RAPPORT — AUDIT DES LIENS DANS LE CONTENU DES ARTICLES")
    print(f"{'='*70}")
    print(f"Articles analyses        : {len(posts)}")
    print(f"URLs cibles uniques       : {len(liens_par_cible)}")
    print(f"OK                        : {ok}")
    print(f"Problemes (liens internes): {len(problemes)}")
    print(f"Problemes (liens externes): {len(externes_problemes)}")
    print(f"{'='*70}")

    def afficher_section(titre_section, liste):
        if not liste:
            print(f"\n✅ {titre_section} : aucun probleme")
            return
        print(f"\n⚠️ {titre_section} ({len(liste)}) :")
        for p in sorted(liste, key=lambda x: len(x["occurrences"]), reverse=True):
            statut_txt = p["erreur"] or f"HTTP {p['statut']}"
            if p["statut"] is not None and p["statut"] < 400:
                statut_txt += f" ({p['nb_redirections']} redirections)"
            print(f"\n  🔗 {p['url']}")
            print(f"     Statut : {statut_txt}")
            print(f"     Cite dans {len(p['occurrences'])} article(s) :")
            for occ in p["occurrences"][:5]:
                print(f"       - post_id={occ['post_id']} \"{occ['texte_ancre']}\" — {occ['titre']}")
                print(f"         {occ['lien_wp']}")
            if len(p["occurrences"]) > 5:
                print(f"       ... et {len(p['occurrences']) - 5} autre(s)")

    afficher_section("LIENS INTERNES CASSES / EN PROBLEME", problemes)
    afficher_section("LIENS EXTERNES CASSES / EN PROBLEME", externes_problemes)


if __name__ == "__main__":
    main()
