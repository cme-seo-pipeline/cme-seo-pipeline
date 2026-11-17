"""
CME -- Correctif cible (dry-run par defaut, --apply pour ecrire) : retire le
bloc Gutenberg "Groupe" en layout flex/nowrap qui enferme 100% du contenu de
l'article 'prix-installation-devis-systeme-solaire-combine' (post_id=13255),
cause confirmee de la mise en page horizontale/cassee signalee par
l'operateur le 17/11/2026 (voir diagnostiquer_wrapper_flex_group.py --tous :
incident ISOLE, 1/1057 articles, aucun defaut systemique du pipeline).

Le contenu stocke est : <!-- wp:group {"layout":{"type":"flex",
"flexWrap":"nowrap"}} --><div class="wp-block-group">...tout l'article...
</div><!-- /wp:group -->. display:flex + flex-wrap:nowrap force chaque
enfant direct (chaque <p>/<h2>/<table>/<ul>...) a s'aligner horizontalement
sans retour a la ligne -- exactement le symptome rapporte.

Correctif : "deplier" (unwrap) ce bloc -- retire les 2 commentaires
Gutenberg (wp:group / /wp:group) et le <div class="wp-block-group"> lui
meme, en gardant TOUT son contenu interne intact, aux memes positions.
Les commentaires <!-- wp:freeform --> internes (non retires, invisibles au
rendu) sont laisses tels quels -- ce ne sont que des marqueurs Gutenberg
sans effet CSS.

N'ecrit JAMAIS la cle 'slug' (voir CLAUDE.md, "Audit -- le slug d'un
article deja publie peut-il etre modifie") -- uniquement 'content'.

Lecture seule par defaut (dry-run affiche le avant/apres) ; --apply pour
ecrire reellement via l'API REST WordPress. Necessite WP_APP_PASSWORD dans
l'environnement (jamais en dur ici).

USAGE :
  python3 fix_wrapper_flex_group_1711.py --slug=<slug>              # dry-run
  python3 fix_wrapper_flex_group_1711.py --slug=<slug> --apply       # ecrit
"""
import os
import sys
import requests
from bs4 import BeautifulSoup, Comment, NavigableString

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)


def _est_commentaire_wp_group_ouvrant(node):
    return isinstance(node, Comment) and "wp:group" in str(node) and "/wp:group" not in str(node) and '"type":"flex"' in str(node).replace(" ", "")


def _est_commentaire_wp_group_fermant(node):
    return isinstance(node, Comment) and "/wp:group" in str(node)


def _sibling_non_vide(node, sens):
    """Avance vers previous_sibling ou next_sibling en sautant les
    NavigableString qui ne sont que du whitespace (retours a la ligne entre
    les tags du contenu stocke)."""
    while node is not None and isinstance(node, NavigableString) and not isinstance(node, Comment) and not str(node).strip():
        node = node.previous_sibling if sens == "prev" else node.next_sibling
    return node


def deplier_groupes_flex(contenu_html):
    """Retire chaque <div class="wp-block-group"> dont le layout Gutenberg
    est flex, en gardant son contenu interne intact. Renvoie (nouveau_html,
    nb_groupes_retires)."""
    soup = BeautifulSoup(contenu_html, "html.parser")
    nb = 0
    # list() pour figer la liste avant mutation (unwrap/extract pendant l'iteration)
    for div in list(soup.find_all("div", class_=lambda c: c and "wp-block-group" in c)):
        comm_ouvrant = _sibling_non_vide(div.previous_sibling, "prev")
        if not _est_commentaire_wp_group_ouvrant(comm_ouvrant):
            continue
        comm_fermant = _sibling_non_vide(div.next_sibling, "next")
        if not _est_commentaire_wp_group_fermant(comm_fermant):
            continue
        comm_ouvrant.extract()
        comm_fermant.extract()
        div.unwrap()
        nb += 1
    return str(soup), nb


def recuperer_par_slug(slug):
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/posts",
        auth=AUTH,
        params={"slug": slug, "status": "publish", "context": "edit"},
        timeout=30,
    )
    r.raise_for_status()
    batch = r.json()
    return batch[0] if batch else None


def ecrire_contenu(post_id, nouveau_contenu):
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
        auth=AUTH,
        json={"content": nouveau_contenu},  # jamais 'slug'
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main():
    slug = None
    apply_ = False
    for arg in sys.argv[1:]:
        if arg.startswith("--slug="):
            slug = arg.split("=", 1)[1]
        elif arg == "--apply":
            apply_ = True

    if not slug:
        sys.exit("❌ --slug=<slug> requis")

    p = recuperer_par_slug(slug)
    if not p:
        sys.exit(f"❌ Aucun article trouve pour le slug '{slug}'")

    contenu = p["content"]["raw"] if isinstance(p["content"], dict) else p["content"]
    titre = p["title"]["raw"] if isinstance(p["title"], dict) else p["title"]
    print(f"post_id={p['id']} slug={p['slug']}")
    print(f"titre: {titre}")
    print(f"taille contenu avant : {len(contenu)} caracteres")

    nouveau_contenu, nb = deplier_groupes_flex(contenu)

    if nb == 0:
        print("ℹ️  Aucun bloc wp:group{flex} trouve dans cet article -- rien a faire.")
        return

    print(f"\n✅ {nb} bloc(s) wp:group{{flex}} deplie(s)")
    print(f"taille contenu apres  : {len(nouveau_contenu)} caracteres")
    print(f"\n--- Debut du contenu APRES correction (800 premiers caracteres) ---")
    print(nouveau_contenu[:800])

    if not apply_:
        print("\n--- DRY-RUN -- rien n'a ete ecrit. Relancer avec --apply pour publier le correctif. ---")
        return

    resultat = ecrire_contenu(p["id"], nouveau_contenu)
    print(f"\n✅ Article {p['id']} mis a jour via l'API REST WordPress.")
    print(f"   Verifier : {WP_URL}/{'/'.join(filter(None, p.get('link', '').split('/')[3:]))}?t=RANDOM" if p.get("link") else "")


if __name__ == "__main__":
    main()
