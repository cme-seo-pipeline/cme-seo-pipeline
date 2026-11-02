"""
CME — Correction retroactive des 21 liens internes morts (vers 7 URLs 404,
jamais publiees) trouves le 02/11/2026 dans 18 articles vivants distincts
(voir CLAUDE.md, "Audit 404 externe du 02/11/2026" + correctif).

Remplace chaque <a href="URL_404">texte</a> par <a href="URL_CIBLE">texte</a>
-- garde le texte de l'ancre, change uniquement l'URL, exactement comme
fix_cta_liens_retroactif.py. Detection via BeautifulSoup (pas de regex sur
HTML imbrique), meme principe que nettoyer_anciens_cta_statiques.py.

Dry-run par defaut (affiche ce qui SERAIT change, n'ecrit rien).
--apply pour ecrire reellement (PATCH WordPress, content uniquement --
jamais de cle 'slug', voir audit du 31/10 dans CLAUDE.md).
--limite=N pour cibler les N premiers articles qui ont REELLEMENT un lien
mort a corriger (comme fix_cta_liens_retroactif.py).
"""
import argparse
import os
import sys

from bs4 import BeautifulSoup
import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
TIMEOUT = 20
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")

# URL 404 -> URL cible proposee (meme table que CLAUDE.md, verifiee en ligne le 02/11).
REMPLACEMENTS = {
    f"{WP_URL}/solaire/systeme-solaire-combine/aides-systeme-solaire-combine-2026/":
        f"{WP_URL}/solaire/systeme-solaire-combine/prix-installation-systeme-solaire-combine-2026/",
    f"{WP_URL}/solaire/batterie-panneaux-solaires/aides-batterie-solaire-2026/":
        f"{WP_URL}/solaire/batterie-panneaux-solaires/batterie-solaire-vs-panneau-seul-roi-2026/",
    f"{WP_URL}/electricite/facture-electricite/augmentation-electricite-causes/":
        f"{WP_URL}/electricite/facture-electricite/pic-consommation-electrique-facture-explose/",
    f"{WP_URL}/solaire/panneaux-solaires/maprimerenov-panneaux-solaires-2026/":
        f"{WP_URL}/solaire/panneaux-solaires/panneaux-solaires-400w-prix-rendement-roi-1031-2/",
    f"{WP_URL}/solaire/chauffe-eau-solaire/aides-chauffe-eau-solaire-2026/":
        f"{WP_URL}/solaire/chauffe-eau-solaire/chauffe-eau-solaire-vs-gaz-roi/",
    f"{WP_URL}/solaire/chauffe-eau-solaire/prix-chauffe-eau-solaire-2026-cout-installation/":
        f"{WP_URL}/solaire/chauffe-eau-solaire/chauffe-eau-solaire-vs-electrique-cout-reel/",
    f"{WP_URL}/solaire/panneaux-solaires/prix-panneaux-solaires-2026-tarifs/":
        f"{WP_URL}/solaire/panneaux-solaires/panneaux-solaires-400w-prix-rendement-roi-1031-2/",
}
# Formes sans slash final, au cas ou le lien genere n'en avait pas.
REMPLACEMENTS.update({k.rstrip("/"): v for k, v in list(REMPLACEMENTS.items())})


def lister_tous_les_posts():
    posts, page = [], 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={"per_page": 100, "page": page, "status": "publish", "context": "edit",
                    "_fields": "id,link,content"},
            auth=(WP_USERNAME, WP_APP_PASSWORD),
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        posts.extend(data)
        page += 1
    return posts


def corriger_contenu(contenu_raw):
    soup = BeautifulSoup(contenu_raw, "html.parser")
    nb_corriges = 0
    details = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href in REMPLACEMENTS:
            cible = REMPLACEMENTS[href]
            details.append((href, cible, a.get_text()))
            a["href"] = cible
            nb_corriges += 1
    return str(soup), nb_corriges, details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limite", type=int, default=None)
    args = parser.parse_args()

    print("Recuperation de tous les articles publies (contenu brut, ?context=edit)...")
    posts = lister_tous_les_posts()
    print(f"{len(posts)} article(s) recupere(s).\n")

    traites = 0
    total_liens_corriges = 0
    for post in posts:
        contenu_raw = post.get("content", {}).get("raw", "") or post.get("content", {}).get("rendered", "")
        if not any(url in contenu_raw for url in REMPLACEMENTS):
            continue

        nouveau_contenu, nb_corriges, details = corriger_contenu(contenu_raw)
        if nb_corriges == 0:
            continue

        print(f"\n{'='*100}")
        print(f"ARTICLE : {post.get('link')} (id={post.get('id')})")
        print(f"  {nb_corriges} lien(s) mort(s) a corriger :")
        for href, cible, texte in details:
            print(f"    - \"{texte}\" : {href}")
            print(f"      -> {cible}")

        if args.apply:
            r = requests.post(
                f"{WP_URL}/wp-json/wp/v2/posts/{post['id']}",
                auth=(WP_USERNAME, WP_APP_PASSWORD),
                json={"content": nouveau_contenu},
                timeout=TIMEOUT,
            )
            if r.status_code == 200:
                print("  ✅ Corrige et publie.")
            else:
                print(f"  ❌ Echec PATCH : HTTP {r.status_code} -- {r.text[:300]}")
        else:
            print("  (dry-run -- rien ecrit, relancer avec --apply pour corriger reellement)")

        total_liens_corriges += nb_corriges
        traites += 1
        if args.limite and traites >= args.limite:
            print(f"\n⏹️ Limite de {args.limite} article(s) atteinte, arret.")
            break

    print(f"\n{'='*100}")
    print(f"TOTAL : {traites} article(s) traite(s), {total_liens_corriges} lien(s) mort(s) "
          f"{'corrige(s)' if args.apply else 'detecte(s) (dry-run)'}.")
    print("=" * 100)


if __name__ == "__main__":
    main()
