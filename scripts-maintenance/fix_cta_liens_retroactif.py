"""
CME — Correctif retroactif des liens CTA deja publies

Remplace, dans le contenu WORDPRESS DEJA PUBLIE, chaque lien <a href="...">
pointant vers l'un des 3 anciens simulateurs par un lien vers
/contactez-un-expert/, en conservant tel quel tout le reste du bloc CTA
(titre, texte d'accroche, couleurs, mise en page) -- conformement au choix
du porteur de projet : on change le lien et le libelle du bouton, rien
d'autre. L'attribut rel="nofollow sponsored" est retire quand present : ce
n'etait plus une recommandation commerciale affiliee mais une page interne
de contact.

Touche UNIQUEMENT la sous-chaine <a href="...">...</a> correspondante.
Tout le reste du contenu de l'article (HTML, tableaux, images, texte) est
laisse rigoureusement intact, octet pour octet.

USAGE :
  python3 fix_cta_liens_retroactif.py                 # lecture seule (defaut) : rapport + echantillon, AUCUNE ecriture
  python3 fix_cta_liens_retroactif.py --limite=5 --apply   # ecrit reellement, mais sur 5 articles seulement (test)
  python3 fix_cta_liens_retroactif.py --apply          # ecrit reellement, sur TOUS les articles publies

Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.
"""
import os
import re
import sys
import time
import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")

AUTH = (WP_USERNAME, WP_APP_PASSWORD)

SIMULATEURS = (
    "comparateur-energie-electricite-gaz",
    "simulateur-aides-renovation-energetique",
    "devis-panneau-solaire",
)

NOUVELLE_PAGE = "/contactez-un-expert/"
NOUVEAU_LABEL = "Contactez un expert"
NOUVELLE_URL = f"https://www.comprendre-mon-energie.fr{NOUVELLE_PAGE}"

# Capture : groupe 1 = ce qui suit le slug du simulateur dans l'URL (ex. "?src_post=1234")
#           -- delibere : capture mais non reutilise, le nouveau lien n'a plus
#              de parametre de tracking (?src_post=...), demande explicite.
#           groupe 2 = les autres attributs de la balise <a> (style, rel, etc.)
#           groupe 3 = le texte interne du lien (le libelle du bouton, avec sa fleche eventuelle)
PATTERN_A = re.compile(
    r'<a\s+href="https://www\.comprendre-mon-energie\.fr/(?:'
    + "|".join(SIMULATEURS) + r')/([^"]*)"([^>]*)>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


def construire_nouveau_lien(match):
    reste_attrs = match.group(2) or ""
    texte_interne = match.group(3) or ""

    # Ce n'est plus un lien affilie/sponsorise vers un outil tiers : on retire
    # l'attribut s'il est present, sans toucher aux autres attributs eventuels.
    reste_attrs = re.sub(r'\s*rel="nofollow sponsored"', "", reste_attrs)

    # Preserve la fleche finale du bouton si elle existe (&rarr; ou →),
    # pour ne pas casser la mise en forme visuelle existante.
    m_fleche = re.search(r'(\s*(?:&rarr;|→))\s*$', texte_interne)
    fleche = m_fleche.group(1) if m_fleche else ""
    nouveau_texte = NOUVEAU_LABEL + fleche

    # Pas de parametre de tracking sur le nouveau lien (?src_post=... retire) :
    # une seule destination unique, pas besoin de distinguer la source.
    return f'<a href="{NOUVELLE_URL}"{reste_attrs}>{nouveau_texte}</a>'


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


def main():
    apply = "--apply" in sys.argv
    limite = None
    for arg in sys.argv:
        if arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])

    print("📥 Recuperation de tous les articles publies...")
    posts = lister_tous_les_posts()
    print(f"   {len(posts)} articles trouves au total\n")

    if limite:
        print(f"   (limite : on s'arrete apres {limite} article(s) AVEC un lien a corriger —")
        print(f"    pas les {limite} premiers articles de la liste, qui sont souvent les plus")
        print(f"    recents et deja corriges depuis le patch du pipeline)\n")

    total_touches = 0
    total_liens = 0
    erreurs = 0
    echantillon = []

    for post in posts:
        if limite and total_touches >= limite:
            break

        post_id = post["id"]
        titre = post.get("title", {}).get("rendered", "")
        lien_wp = post.get("link", "")
        contenu = post.get("content", {}).get("raw") or post.get("content", {}).get("rendered", "")

        occurrences = list(PATTERN_A.finditer(contenu))
        if not occurrences:
            continue

        nouveau_contenu = PATTERN_A.sub(construire_nouveau_lien, contenu)
        total_touches += 1
        total_liens += len(occurrences)

        if len(echantillon) < 5:
            echantillon.append({
                "post_id": post_id,
                "titre": titre[:60],
                "lien": lien_wp,
                "nb_liens": len(occurrences),
                "avant": occurrences[0].group(0)[:220],
                "apres": construire_nouveau_lien(occurrences[0])[:220],
            })

        if not apply:
            print(f"  🔍 [SANS ECRITURE] post_id={post_id} — {len(occurrences)} lien(s) — {titre[:60]}")
            print(f"      {lien_wp}")
            continue

        try:
            r = requests.post(
                f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                json={"content": nouveau_contenu},
                auth=AUTH, timeout=30,
            )
            if r.status_code == 200:
                print(f"  ✅ post_id={post_id} — {len(occurrences)} lien(s) corrige(s) — {titre[:60]}")
                print(f"      {lien_wp}")
            else:
                print(f"  ❌ post_id={post_id} — HTTP {r.status_code}")
                erreurs += 1
        except Exception as e:
            print(f"  ❌ post_id={post_id} — erreur : {e}")
            erreurs += 1
        time.sleep(0.3)  # menage pour l'hebergement mutualise, pas de rafale de POST

    print(f"\n{'='*60}")
    print(f"Articles scannes (total sur le site) : {len(posts)}")
    print(f"Articles avec lien(s) a corriger : {total_touches}{' (limite atteinte)' if limite and total_touches >= limite else ''}")
    print(f"Liens trouves au total           : {total_liens}")
    if apply:
        print(f"Erreurs                          : {erreurs}")
    else:
        print("Mode LECTURE SEULE -- relancer avec --apply pour ecrire reellement")
    print(f"{'='*60}")

    if echantillon:
        print("\nEchantillon (jusqu'a 5 articles, premier lien de chacun) :")
        for e in echantillon:
            print(f"\n  post_id={e['post_id']} ({e['nb_liens']} lien(s) dans cet article) — {e['titre']}")
            print(f"    {e['lien']}")
            print(f"    AVANT : {e['avant']}...")
            print(f"    APRES : {e['apres']}...")


if __name__ == "__main__":
    main()
