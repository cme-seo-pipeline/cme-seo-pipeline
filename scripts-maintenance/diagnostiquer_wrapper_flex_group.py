"""
CME -- Diagnostic (lecture seule) : combien d'articles publies ont tout (ou
une grande partie) de leur contenu enferme dans UN SEUL bloc Gutenberg
"Groupe" en layout flex/nowrap (<!-- wp:group {"layout":{"type":"flex",
"flexWrap":"nowrap"}} -->) ?

Contexte (17/11/2026) : l'operateur rapporte une page dont la structure est
"cassee / ecrite horizontalement". diagnostiquer_premier_slot_comparateur.py
--dump a confirme que le contenu stocke de
'prix-installation-devis-systeme-solaire-combine' est integralement enferme
dans un unique <div class="wp-block-group"> avec ce layout flex/nowrap --
chaque enfant direct (chaque <p>/<h2>/<table>...) devient alors un flex item
aligne horizontalement sans retour a la ligne, ce qui explique exactement
le symptome visuel signale. Rien a voir avec le chantier comparateur/CTA
(l'article avait 0 emplacement d'insertion trouve, cote a cote avec ce
nouveau constat -- l'un explique l'autre : enfantsEffectifs() ne deplie pas
wp-block-group, donc tout le bloc est vu comme 1 seul enfant opaque).

Ce script scanne un echantillon (ou tous) les articles publies et detecte
ce motif precis, pour savoir si c'est un incident isole ou un defaut plus
large. Lecture seule stricte -- ne modifie rien. Necessite WP_APP_PASSWORD
dans l'environnement (jamais en dur ici).

USAGE :
  python3 diagnostiquer_wrapper_flex_group.py --slug=<slug-article>
  python3 diagnostiquer_wrapper_flex_group.py --tous   # scanne TOUS les articles publies (pagine)
  python3 diagnostiquer_wrapper_flex_group.py --echantillon=200
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

# Detecte un commentaire Gutenberg wp:group dont le layout est flex (avec ou
# sans flexWrap explicite) -- l'ordre des cles JSON n'est pas garanti donc on
# cherche juste la presence des deux signatures dans le MEME commentaire.
RE_WPGROUP_FLEX = re.compile(
    r'<!--\s*wp:group\s*(\{[^}]*"type"\s*:\s*"flex"[^}]*\})\s*-->',
    re.IGNORECASE,
)


def mots(texte):
    t = re.sub(r"<[^>]+>", " ", texte or "")
    t = t.strip()
    return len(t.split()) if t else 0


def analyser_contenu(contenu_html):
    """Renvoie la liste des blocs wp:group{flex} trouves, avec pour chacun
    une estimation grossiere de sa taille (en mots de texte brut dans la
    portion du HTML qui lui est associee, approxime par la distance jusqu'au
    commentaire </!-- /wp:group --> correspondant le plus proche -- sans
    parser proprement l'imbrication, volontairement simple pour ce diagnostic)."""
    matches = list(RE_WPGROUP_FLEX.finditer(contenu_html))
    if not matches:
        return []
    total_mots_article = mots(contenu_html)
    resultats = []
    for m in matches:
        start = m.end()
        fin_tag = contenu_html.find("<!-- /wp:group -->", start)
        portion = contenu_html[start:fin_tag] if fin_tag != -1 else contenu_html[start:start + 3000]
        mots_portion = mots(portion)
        resultats.append({
            "layout_json": m.group(1),
            "mots_dans_le_groupe": mots_portion,
            "pct_de_larticle": round(100 * mots_portion / total_mots_article, 1) if total_mots_article else 0,
        })
    return resultats


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


def recuperer_page(page, per_page=100):
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/posts",
        auth=AUTH,
        params={"per_page": per_page, "page": page, "status": "publish",
                "context": "edit", "orderby": "date", "order": "desc"},
        timeout=30,
    )
    r.raise_for_status()
    total_pages = int(r.headers.get("X-WP-TotalPages", "1"))
    return r.json(), total_pages


def main():
    slug = None
    echantillon_n = None
    tous = False
    for arg in sys.argv[1:]:
        if arg.startswith("--slug="):
            slug = arg.split("=", 1)[1]
        elif arg.startswith("--echantillon="):
            echantillon_n = int(arg.split("=", 1)[1])
        elif arg == "--tous":
            tous = True

    posts = []
    if slug:
        p = recuperer_par_slug(slug)
        if not p:
            sys.exit(f"❌ Aucun article trouve pour le slug '{slug}'")
        posts = [p]
    elif tous:
        page = 1
        total_pages = 1
        while page <= total_pages:
            batch, total_pages = recuperer_page(page)
            if not batch:
                break
            posts += batch
            print(f"  ... page {page}/{total_pages} recuperee ({len(posts)} articles au total)")
            page += 1
    elif echantillon_n:
        page = 1
        while len(posts) < echantillon_n:
            batch, total_pages = recuperer_page(page, per_page=min(100, echantillon_n - len(posts)))
            if not batch:
                break
            posts += batch
            page += 1
            if page > total_pages:
                break
    else:
        sys.exit("❌ Rien a analyser -- passer --slug=..., --echantillon=N ou --tous")

    a_risque = []
    for p in posts:
        contenu = p["content"]["raw"] if isinstance(p["content"], dict) else p["content"]
        titre = p["title"]["raw"] if isinstance(p["title"], dict) else p["title"]
        groupes = analyser_contenu(contenu)
        if groupes:
            # On ne retient comme "a risque" que si AU MOINS un des groupes flex
            # couvre une part significative de l'article (>=30%) -- un petit
            # groupe flex volontaire (ex: 2 boutons cote a cote) n'est pas un bug.
            gros = [g for g in groupes if g["pct_de_larticle"] >= 30]
            if gros:
                a_risque.append((p["id"], p["slug"], titre[:70], gros))

    print(f"\n=== RESUME ===")
    print(f"{len(posts)} article(s) analyse(s)")
    print(f"{len(a_risque)} article(s) avec un bloc wp:group{{flex}} couvrant >=30% du contenu")
    for pid, s, titre, gros in a_risque:
        print(f"\n  - post_id={pid} slug={s}")
        print(f"    titre: {titre}")
        for g in gros:
            print(f"    layout={g['layout_json']} -- {g['mots_dans_le_groupe']} mots ({g['pct_de_larticle']}% de l'article)")


if __name__ == "__main__":
    main()
