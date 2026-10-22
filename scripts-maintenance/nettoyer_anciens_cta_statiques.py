"""
CME — Nettoyage retroactif des anciens boutons CTA statiques "bakes" dans le
contenu des articles DEJA PUBLIES.

Contexte (chantier du 22/10/2026, voir CLAUDE.md "Formulaire progressif") :
le mu-plugin cme-cta-progressifs.php insere desormais, cote client, un
mini-formulaire interactif toutes les ~230 mots sur CHAQUE article (ancien ET
nouveau) -- remplacant les boutons CTA statiques qui etaient autrefois baked
en dur dans post_content au moment de la publication (fonction
inserer_ctas_repartis() de pipeline/pipeline.py, desormais desactivee pour
les nouveaux articles).

Mais ce changement cote mu-plugin ne retire PAS les anciens boutons deja
ecrits dans le contenu stocke des articles publies AVANT ce chantier --
sans ce script, ces vieux boutons statiques ("Contactez un expert") restent
visibles EN PLUS du nouveau formulaire dynamique, qui s'insere a cote (le
mu-plugin ne les detecte que pour reinitialiser son compteur de mots, pas
pour les retirer). Ce script retire ces blocs CTA statiques devenus
redondants, pour que seul le nouveau mini-formulaire reste visible.

Detection : le gabarit genere par generer_cta_html() (pipeline/pipeline.py)
est un <div style="background:linear-gradient(...)..."> contenant un <h3>,
un <p> et un <a>...Contactez un expert...</a> (parfois precede d'un petit
<div style="clear:both;..."> de clearfix). On parse le HTML avec
BeautifulSoup (pas de regex sur du HTML imbrique : plus fiable face aux
variations de mise en forme deja documentees dans ce projet, cf. le piege
d'ordre des attributs connu pour <a href=...>) et on retire tout <div> dont
le style contient "linear-gradient" ET dont le texte contient le libelle du
bouton "Contactez un expert" -- signature suffisamment specifique pour ne
jamais toucher un autre bloc de contenu editorial.

Touche UNIQUEMENT ces blocs CTA. Tout le reste du contenu (texte, images,
tableaux, liens internes) est laisse intact.

USAGE :
  python3 nettoyer_anciens_cta_statiques.py                    # lecture seule (defaut) : rapport + echantillon
  python3 nettoyer_anciens_cta_statiques.py --limite=5 --apply # ecrit reellement, sur 5 articles concernes seulement (test)
  python3 nettoyer_anciens_cta_statiques.py --apply            # ecrit reellement, sur TOUS les articles concernes

Necessite WP_APP_PASSWORD (et WP_USERNAME, optionnel) dans l'environnement.
"""
import os
import sys
import time
import requests
from bs4 import BeautifulSoup

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")

AUTH = (WP_USERNAME, WP_APP_PASSWORD)

LIBELLE_BOUTON = "contactez un expert"   # comparaison en minuscules


def retirer_vieux_cta(contenu_html):
    """Retire les blocs CTA statiques (gradient + 'Contactez un expert') et
    leur eventuel clearfix juste avant. Retourne (nouveau_html, nb_retires)."""
    soup = BeautifulSoup(contenu_html, "html.parser")
    a_retirer = []

    for div in soup.find_all("div"):
        style = div.get("style") or ""
        if "linear-gradient" not in style:
            continue
        texte = div.get_text(" ", strip=True).lower()
        if LIBELLE_BOUTON not in texte:
            continue
        a_retirer.append(div)

    if not a_retirer:
        return contenu_html, 0

    for div in a_retirer:
        precedent = div.find_previous_sibling("div")
        if precedent is not None:
            style_prec = (precedent.get("style") or "").lower()
            # clearfix genere par generer_cta_html() juste avant le bloc gradient
            if "clear:both" in style_prec and not precedent.get_text(strip=True):
                precedent.decompose()
        div.decompose()

    # BeautifulSoup reserialise le document complet ; on ne lui a donne que
    # le fragment post_content, donc str(soup) reste bien un fragment.
    return str(soup), len(a_retirer)


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
        print(f"   (limite : on s'arrete apres {limite} article(s) AVEC un vieux CTA a retirer —")
        print(f"    pas les {limite} premiers articles de la liste)\n")

    total_touches = 0
    total_blocs = 0
    erreurs = 0
    echantillon = []

    for post in posts:
        if limite and total_touches >= limite:
            break

        post_id = post["id"]
        titre = post.get("title", {}).get("rendered", "")
        lien_wp = post.get("link", "")
        contenu = post.get("content", {}).get("raw") or post.get("content", {}).get("rendered", "")

        nouveau_contenu, nb_retires = retirer_vieux_cta(contenu)
        if nb_retires == 0:
            continue

        total_touches += 1
        total_blocs += nb_retires

        if len(echantillon) < 5:
            echantillon.append({
                "post_id": post_id,
                "titre": titre[:60],
                "lien": lien_wp,
                "nb_blocs": nb_retires,
            })

        if not apply:
            print(f"  🔍 [SANS ECRITURE] post_id={post_id} — {nb_retires} bloc(s) CTA statique(s) a retirer — {titre[:60]}")
            print(f"      {lien_wp}")
            continue

        try:
            r = requests.post(
                f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                json={"content": nouveau_contenu},
                auth=AUTH, timeout=30,
            )
            if r.status_code == 200:
                print(f"  ✅ post_id={post_id} — {nb_retires} bloc(s) retire(s) — {titre[:60]}")
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
    print(f"Articles avec vieux CTA a retirer     : {total_touches}{' (limite atteinte)' if limite and total_touches >= limite else ''}")
    print(f"Blocs CTA statiques retires au total  : {total_blocs}")
    if apply:
        print(f"Erreurs                               : {erreurs}")
    else:
        print("Mode LECTURE SEULE -- relancer avec --apply pour ecrire reellement")
    print(f"{'='*60}")

    if echantillon:
        print("\nEchantillon (jusqu'a 5 articles concernes) :")
        for e in echantillon:
            print(f"  post_id={e['post_id']} ({e['nb_blocs']} bloc(s)) — {e['titre']}")
            print(f"    {e['lien']}")


if __name__ == "__main__":
    main()
