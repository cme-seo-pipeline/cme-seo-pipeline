"""
CME -- Diagnostic (lecture seule) : le 1er emplacement du mini-formulaire
periodique ("contact-expert-inline"), desormais remplace par le comparateur
energie (voir CLAUDE.md, chantier du 16/11/2026), peut-il atterrir a
l'interieur d'une COLONNE GUTENBERG ETROITE (wp-block-column) plutot que
dans la pleine largeur de l'article (.entry-content directement) ?

Contexte du signalement (16-17/11/2026) : l'operateur rapporte une page
dont la structure semble "cassee / ecrite horizontalement" apres ce
deploiement. Hypothese technique concrete, verifiee cote CSS avant ce
script : .cme-comp .g2/.g3 (grille des champs de l'etape 1) utilise
`grid-template-columns:1fr 1fr` SANS minmax(0,...) -- bug CSS Grid
classique, la grille ne peut pas se compresser sous la largeur intrinseque
de son contenu. Si le comparateur est insere dans une colonne Gutenberg
etroite, la grille peut deborder horizontalement et casser visuellement
la mise en page -- le @media(max-width:480px) existant ne protege que les
petits ECRANS, pas un CONTENEUR etroit sur un ecran normal.

Ce script REPLIQUE en Python/BeautifulSoup EXACTEMENT la logique de
placement de cme-cta-progressifs.php (enfantsEffectifs/estCta/estVide/
estConteneurLayout/prochainSeuilContact/MOTS_FIN_MIN/MAX_FORMULAIRES_CONTACT)
pour determiner, pour un article donne, OU atterrirait reellement le 1er
emplacement (poses===0, desormais le comparateur) -- et si son PARENT REEL
(pas la liste aplatie utilisee pour l'iteration, le vrai parent DOM) est un
wp-block-column/wp-block-columns.

Lecture seule stricte -- ne modifie aucun article. Necessite WP_APP_PASSWORD
dans l'environnement (jamais en dur ici).

USAGE :
  python3 diagnostiquer_premier_slot_comparateur.py --slug=<slug-article>
  python3 diagnostiquer_premier_slot_comparateur.py --echantillon=80   # N articles les plus recents
"""
import os
import sys
import requests
from bs4 import BeautifulSoup, NavigableString, Tag

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)

MAX_FORMULAIRES_CONTACT = 7
MOTS_FIN_MIN = 120


def prochain_seuil_contact(poses):
    if poses < 5:
        return 300 + poses * 200
    return 1100 + (poses - 4) * 400


def mots(el):
    t = el.get_text().strip() if hasattr(el, "get_text") else str(el).strip()
    return len(t.split()) if t else 0


def est_cta(el):
    if not isinstance(el, Tag) or el.name != "div":
        return False
    style = el.get("style") or ""
    return "linear-gradient" in style


def est_vide(el):
    if not isinstance(el, Tag) or el.name != "div":
        return False
    has_children = any(isinstance(c, Tag) for c in el.children)
    return (not has_children) and not el.get_text().strip()


def est_conteneur_layout(el):
    if not isinstance(el, Tag):
        return False
    if el.name == "article":
        return True
    if el.name != "div":
        return False
    classes = el.get("class") or []
    return "wp-block-columns" in classes or "wp-block-column" in classes


def enfants_effectifs(zone):
    resultat = []

    def deplier(liste):
        for el in liste:
            if not isinstance(el, Tag):
                continue
            if est_conteneur_layout(el):
                deplier(list(el.children))
            else:
                resultat.append(el)

    deplier(list(zone.children))
    return resultat


def analyser_article(contenu_html):
    """Reproduit EXACTEMENT la boucle de placement 'contact' et renvoie un
    diagnostic sur le 1er emplacement (poses===0, desormais le comparateur)."""
    soup = BeautifulSoup(contenu_html, "html.parser")
    # Emule .entry-content : on traite directement le soup top-level comme
    # la "zone" (le contenu stocke ne contient pas le wrapper .entry-content
    # lui-meme, seulement ce qu'il y a dedans -- equivalent fonctionnel).
    zone = soup
    enfants = enfants_effectifs(zone)
    if not enfants:
        return {"statut": "vide", "total_mots": 0}

    total_mots_article = sum(mots(e) for e in enfants if not est_cta(e))

    # apres[i] : mots restants apres l'element i avant la fin (pas de CTA
    # existant a l'etat initial puisqu'on lit le contenu STOCKE, jamais
    # injecte -- acc ne se reinitialise donc jamais ici, contrairement au
    # JS qui doit gerer d'anciens CTA deja presents).
    apres = [0] * len(enfants)
    acc = 0
    for i in range(len(enfants) - 1, -1, -1):
        apres[i] = acc
        if est_cta(enfants[i]):
            acc = 0
        else:
            acc += mots(enfants[i])

    total_mots_vus = 0
    poses = 0
    premier_slot_info = None
    for i, el in enumerate(enfants):
        if est_cta(el):
            continue
        total_mots_vus += mots(el)
        if poses >= MAX_FORMULAIRES_CONTACT:
            break
        if total_mots_vus < prochain_seuil_contact(poses):
            continue
        if el.name not in ("p", "ul", "ol", "table", "figure", "blockquote"):
            continue
        suivant_el = enfants[i + 1] if i + 1 < len(enfants) else None
        if suivant_el is None or est_cta(suivant_el) or est_vide(suivant_el):
            continue
        if apres[i] < MOTS_FIN_MIN:
            continue

        if poses == 0:
            # C'est ICI que le comparateur serait insere (juste avant
            # suivant_el, dans son parent REEL -- pas la liste aplatie).
            parent_reel = suivant_el.parent
            chemin_parents = []
            p = parent_reel
            while p is not None and p.name not in ("[document]",):
                cls = p.get("class") if isinstance(p, Tag) else None
                chemin_parents.append(f"<{p.name} class={cls}>")
                p = p.parent
            dans_colonne = any(
                isinstance(anc, Tag)
                and anc.name == "div"
                and ("wp-block-column" in (anc.get("class") or []))
                for anc in parent_reel.parents
            ) or (
                isinstance(parent_reel, Tag)
                and "wp-block-column" in (parent_reel.get("class") or [])
            )
            premier_slot_info = {
                "mots_avant_slot": total_mots_vus,
                "tag_element_precedent": el.name,
                "tag_suivant_el": suivant_el.name,
                "parent_reel_tag": parent_reel.name if parent_reel else None,
                "parent_reel_classes": parent_reel.get("class") if isinstance(parent_reel, Tag) else None,
                "chemin_parents": " > ".join(reversed(chemin_parents[:6])),
                "DANS_UNE_COLONNE_ETROITE": dans_colonne,
            }
        poses += 1

    return {
        "statut": "ok",
        "total_mots": total_mots_article,
        "poses_total": poses,
        "premier_slot": premier_slot_info,
    }


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


def recuperer_echantillon(n):
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/posts",
        auth=AUTH,
        params={"per_page": min(n, 100), "page": 1, "status": "publish",
                "context": "edit", "orderby": "date", "order": "desc"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main():
    slug = None
    echantillon_n = None
    for arg in sys.argv[1:]:
        if arg.startswith("--slug="):
            slug = arg.split("=", 1)[1]
        elif arg.startswith("--echantillon="):
            echantillon_n = int(arg.split("=", 1)[1])

    posts = []
    if slug:
        p = recuperer_par_slug(slug)
        if not p:
            sys.exit(f"❌ Aucun article trouve pour le slug '{slug}'")
        posts = [p]
    if echantillon_n:
        posts += recuperer_echantillon(echantillon_n)

    if not posts:
        sys.exit("❌ Rien a analyser -- passer --slug=... et/ou --echantillon=N")

    a_risque = []
    ok = []
    for p in posts:
        titre = p["title"]["raw"] if isinstance(p["title"], dict) else p["title"]
        contenu = p["content"]["raw"] if isinstance(p["content"], dict) else p["content"]
        diag = analyser_article(contenu)
        slot = diag.get("premier_slot")
        print(f"\n--- post_id={p['id']} slug={p['slug']} ---")
        print(f"    titre: {titre[:70]}")
        print(f"    total mots (hors CTA): {diag.get('total_mots')}, formulaires 'contact' places: {diag.get('poses_total')}")
        if slot:
            print(f"    1er emplacement (comparateur) apres {slot['mots_avant_slot']} mots")
            print(f"    parent reel: <{slot['parent_reel_tag']} class={slot['parent_reel_classes']}>")
            print(f"    chemin parents (jusqu'a 6 niveaux): {slot['chemin_parents']}")
            if slot["DANS_UNE_COLONNE_ETROITE"]:
                print("    ⚠️  DANS UNE COLONNE GUTENBERG ETROITE -- risque de debordement grille confirme")
                a_risque.append((p["id"], p["slug"]))
            else:
                print("    ✅ dans la pleine largeur de l'article (pas de colonne)")
                ok.append((p["id"], p["slug"]))
        else:
            print("    (aucun 1er emplacement -- article trop court ou structure non eligible)")

    print(f"\n=== RESUME ===")
    print(f"{len(a_risque)} article(s) a risque (colonne etroite) sur {len(posts)} analyse(s)")
    for pid, s in a_risque:
        print(f"  - post_id={pid} slug={s}")
    print(f"{len(ok)} article(s) sans risque de colonne (pleine largeur)")


if __name__ == "__main__":
    main()
