"""
CME — Diagnostic des 7 URLs remontees en 404 par un audit externe du
02/11/2026 (export CSV fourni par l'operateur, colonnes "Page URL with
Http 400-499 errors" + "Page depth").

Pour chaque URL :
1. Statut HTTP reel en live (le runner GitHub Actions a un acces reseau
   complet au site, contrairement a ce sandbox).
2. Recherche dans historique_publications (BigQuery) par correspondance de
   slug, pour recuperer post_id/date_publication/silo/sous_silo/mot_cle/
   run_id/type_publication si l'article a bien ete publie par ce pipeline.
3. Si un post_id est trouve : etat reel du post cote WordPress
   (`?context=edit`, authentifie -- seul moyen de voir un statut
   draft/trash/pending, invisible de l'API publique) pour savoir si
   l'article existe toujours mais a change de statut, ou s'il n'existe
   plus du tout (404 API aussi).

LECTURE SEULE. Necessite WP_APP_PASSWORD (+ WP_USERNAME optionnel) dans
l'environnement, meme pattern que auditer_liens_internes.py.
"""
import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

import requests

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)
TIMEOUT = 15

URLS_404 = [
    "https://www.comprendre-mon-energie.fr/solaire/systeme-solaire-combine/aides-systeme-solaire-combine-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/batterie-panneaux-solaires/aides-batterie-solaire-2026/",
    "https://www.comprendre-mon-energie.fr/electricite/facture-electricite/augmentation-electricite-causes/",
    "https://www.comprendre-mon-energie.fr/solaire/panneaux-solaires/maprimerenov-panneaux-solaires-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/aides-chauffe-eau-solaire-2026/",
    "https://www.comprendre-mon-energie.fr/solaire/chauffe-eau-solaire/prix-chauffe-eau-solaire-2026-cout-installation/",
    "https://www.comprendre-mon-energie.fr/solaire/panneaux-solaires/prix-panneaux-solaires-2026-tarifs/",
]


def slug_de(url):
    return url.rstrip("/").rsplit("/", 1)[-1]


def statut_http(url):
    try:
        r = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        chain = " -> ".join(str(h.status_code) for h in r.history) + (" -> " if r.history else "")
        return f"{chain}{r.status_code}", r.url
    except Exception as e:
        return f"ERREUR({e})", None


def chercher_post_wp_par_slug(slug):
    # API publique : ne renvoie que les posts publies. Si vide, on tente
    # en authentifie avec tous les statuts pour voir si le post existe
    # mais est en draft/trash/pending.
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={"slug": slug, "context": "edit"},
            auth=AUTH, timeout=TIMEOUT,
        )
        if r.status_code == 200 and r.json():
            return r.json()[0]
    except Exception:
        pass
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            params={"slug": slug, "status": "draft,trash,pending,future,private", "context": "edit"},
            auth=AUTH, timeout=TIMEOUT,
        )
        if r.status_code == 200 and r.json():
            return r.json()[0]
    except Exception:
        pass
    return None


def main():
    client_bq = init_bigquery()

    print("=" * 100)
    for url in URLS_404:
        slug = slug_de(url)
        print(f"\n### {url}")
        print(f"    slug = {slug!r}")

        statut, url_finale = statut_http(url)
        print(f"    HTTP live : {statut}" + (f" (redirige vers {url_finale})" if url_finale and url_finale != url else ""))

        # BigQuery : correspondance par slug dans source_page/mot_cle/titre
        df = client_bq.query(f"""
            SELECT post_id, date_publication, silo, sous_silo_strategique,
                   titre, mot_cle, run_id, type_publication, url_wp
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE url_wp LIKE '%{slug}%' OR url_wp LIKE '%{slug}/'
            ORDER BY date_publication
        """).to_dataframe()

        if len(df) == 0:
            print("    historique_publications : AUCUNE ligne trouvee pour ce slug")
        else:
            for _, r in df.iterrows():
                print(f"    historique_publications : post_id={r['post_id']} | "
                      f"{r['date_publication']} | silo={r['silo']} | "
                      f"sous_silo={r['sous_silo_strategique']} | mot_cle={r['mot_cle']!r}")
                print(f"        titre={r['titre'][:90]!r} | run_id={r['run_id']!r} | "
                      f"type_publication={r['type_publication']!r}")

                post_wp = None
                try:
                    r_wp = requests.get(
                        f"{WP_URL}/wp-json/wp/v2/posts/{int(r['post_id'])}",
                        params={"context": "edit"}, auth=AUTH, timeout=TIMEOUT,
                    )
                    if r_wp.status_code == 200:
                        post_wp = r_wp.json()
                        print(f"        WP post_id={r['post_id']} existe toujours -- "
                              f"status={post_wp.get('status')!r}, slug reel={post_wp.get('slug')!r}, "
                              f"link={post_wp.get('link')!r}")
                    else:
                        print(f"        WP post_id={r['post_id']} -> HTTP {r_wp.status_code} "
                              f"(introuvable meme en API authentifiee)")
                except Exception as e:
                    print(f"        Erreur verif WP post_id={r['post_id']} : {e}")

        post_direct = chercher_post_wp_par_slug(slug)
        if post_direct:
            print(f"    Recherche directe par slug WP : trouve, id={post_direct.get('id')}, "
                  f"status={post_direct.get('status')!r}, link={post_direct.get('link')!r}")
        else:
            print("    Recherche directe par slug WP : aucun post (publie ou non) avec ce slug exact")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
