"""
CME — Diagnostic cible des 2 cas sortis de reverifier_deficit_partiel_48.py
(run du 11/11/2026) qui ne sont pas un simple "OK" :

  - id=8816 : l'API REST WordPress n'a pas repondu 200 -> a comprendre
    pourquoi (article supprime/deplace/prive, ou simple souci reseau
    transitoire du run precedent).
  - id=563  : seul "deficit reel confirme" (4 formulaires rendus contre 7
    attendus par l'algorithme a jour) -- deja corrige le 04/11 (bloc
    Colonnes). A verifier si le deficit est un vrai residu structurel ou
    un artefact (ex. contenu modifie depuis, cache, ou la structure reelle
    differe de ce que simuler_attendu_realiste() suppose).

LECTURE SEULE.
"""
import json

import requests
from bs4 import BeautifulSoup, Tag

SITE = "https://www.comprendre-mon-energie.fr"


def diagnostiquer_8816():
    print("=" * 80)
    print("id=8816 -- pourquoi l'API REST ne repond pas 200 ?")
    print("=" * 80)
    for statuts in [None, "publish,draft,pending,future,private,trash"]:
        params = {"_fields": "id,content,status,link"}
        if statuts:
            params["status"] = statuts
            params["context"] = "edit"
        try:
            resp = requests.get(f"{SITE}/wp-json/wp/v2/posts/8816", params=params, timeout=30,
                                 auth=None)
            print(f"  params={params} -> HTTP {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"    status={data.get('status')} link={data.get('link')}")
            else:
                print(f"    corps (300 premiers car.) : {resp.text[:300]}")
        except Exception as e:
            print(f"  params={params} -> exception : {e}")

    # Essai par recherche (slug/titre) au cas ou l'id aurait change.
    try:
        resp = requests.get(f"{SITE}/wp-json/wp/v2/posts", params={"search": "8816"}, timeout=30)
        print(f"  recherche search=8816 -> HTTP {resp.status_code}, {len(resp.json()) if resp.status_code == 200 else 'n/a'} resultat(s)")
    except Exception as e:
        print(f"  recherche -> exception : {e}")


def mots(el):
    if isinstance(el, Tag):
        texte = el.get_text(separator=" ").strip()
    else:
        texte = str(el).strip()
    return len(texte.split()) if texte else 0


def est_cta(el):
    if not isinstance(el, Tag) or el.name != "div":
        return False
    style = el.get("style", "")
    if isinstance(style, list):
        style = " ".join(style)
    return "linear-gradient" in (style or "")


def est_vide(el):
    if not isinstance(el, Tag) or el.name != "div":
        return False
    a_des_enfants_tag = any(isinstance(c, Tag) for c in el.children)
    texte = el.get_text().strip()
    return (not a_des_enfants_tag) and (not texte)


def est_conteneur_layout(el):
    if not isinstance(el, Tag):
        return False
    if el.name == "article":
        return True
    if el.name != "div":
        return False
    classes = el.get("class", [])
    return "wp-block-columns" in classes or "wp-block-column" in classes


def enfants_effectifs(racine):
    resultat = []

    def deplier(liste):
        for el in liste:
            if est_conteneur_layout(el):
                deplier([c for c in el.children if isinstance(c, Tag)])
            else:
                resultat.append(el)

    deplier([c for c in racine.contents if isinstance(c, Tag)])
    return resultat


def diagnostiquer_563():
    print()
    print("=" * 80)
    print("id=563 -- pourquoi 4 rendus / 7 attendus ?")
    print("=" * 80)
    resp = requests.get(f"{SITE}/wp-json/wp/v2/posts/563", params={"_fields": "id,content,modified"}, timeout=30)
    if resp.status_code != 200:
        print(f"  ❌ HTTP {resp.status_code} en recuperant le contenu")
        return
    data = resp.json()
    print(f"  Derniere modification : {data.get('modified')}")
    html = (data.get("content") or {}).get("rendered", "")
    soup = BeautifulSoup(html, "html.parser")

    enfants = enfants_effectifs(soup)
    print(f"  Nombre d'enfants effectifs (apres depliage Colonnes/<article>) : {len(enfants)}")

    total_mots = sum(mots(e) for e in enfants if not est_cta(e))
    print(f"  Total mots (hors CTA) : {total_mots}")

    # Detail des elements CTA deja presents dans le contenu stocke --
    # si des CTA statiques sont deja baked in, ca change l'accumulation
    # de mots_vus et peut expliquer un ecart par rapport a la simulation.
    n_cta_stockes = sum(1 for e in enfants if est_cta(e))
    print(f"  Blocs deja marques 'CTA' dans le contenu stocke : {n_cta_stockes}")

    # Liste les tags/mots de chaque enfant pour comprendre la structure.
    print("  Detail des enfants effectifs :")
    for i, el in enumerate(enfants):
        tag = el.name
        m = mots(el)
        cta = " [CTA]" if est_cta(el) else ""
        vide = " [VIDE]" if est_vide(el) else ""
        print(f"    [{i:>3}] <{tag}> {m} mots{cta}{vide}")

    # Combien de niveaux d'imbrication de blocs Colonnes/<article> --
    # si plusieurs niveaux s'emboitent, enfants_effectifs() les deplie
    # tous, mais ca vaut la peine de confirmer qu'il n'y a pas un cas
    # de structure plus profonde/inattendue (ex. Colonnes DANS un
    # <article> DANS des Colonnes) qui ferait diverger la simulation
    # de la realite du DOM rendu cote client (le JS vrai utilise les
    # memes regles, donc en theorie identique -- sauf si le HTML
    # *stocke* a change depuis le dernier run du vrai script cote
    # client, ex. cache serveur pas encore purge au moment du rendu).
    print(f"\n  HTML brut (1500 premiers caracteres) :")
    print(f"  {html[:1500]}")


if __name__ == "__main__":
    diagnostiquer_8816()
    diagnostiquer_563()
