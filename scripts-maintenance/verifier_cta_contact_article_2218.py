"""
CME — Complement de diagnostic (lecture seule) pour l'article
attestation-de-contrat-delectricite (id=2218) : le diagnostic precedent
(diagnostiquer_cta_manquant_et_cache_obsolete.py, LIMIT 20) ne montrait
QUE des evenements cible='appel' -- jamais cible='contact' -- malgre un
article de 4461 mots qui devrait declencher jusqu'a 7 occurrences du
mini-formulaire 'contact' (seuils 300/500/700/900/1100/1500/1900 mots).

Agrege ICI, sans LIMIT, par (type_evenement, cible, position_contenu)
pour trancher entre deux hypotheses :
  a) le mini-formulaire 'contact' n'est jamais vu/declenche sur cet
     article precis (vrai probleme a investiguer plus loin) ;
  b) il est vu normalement, le precedent diagnostic n'en montrait
     simplement pas dans ses 20 lignes les plus recentes (cas probable :
     navigation rapide de l'operateur qui n'a pas declenche
     l'IntersectionObserver sur les positions intermediaires).

LECTURE SEULE -- aucune ecriture.

USAGE :
  python3 verifier_cta_contact_article_2218.py
"""
from google.cloud import bigquery

PROJECT = "seo-data-hub-cme"
DATASET = "04_pipeline_seo"
TABLE = "interactions_contenu"
POST_ID = 2218


def main():
    client = bigquery.Client(project=PROJECT)

    query = f"""
        SELECT type_evenement, cible, position_contenu, COUNT(*) AS nb, MIN(timestamp) AS premier, MAX(timestamp) AS dernier
        FROM `{PROJECT}.{DATASET}.{TABLE}`
        WHERE CAST(source_post_id AS STRING) = '{POST_ID}'
        GROUP BY type_evenement, cible, position_contenu
        ORDER BY type_evenement, cible, position_contenu
    """
    rows = list(client.query(query).result())
    if not rows:
        print(f"  (aucun evenement du tout pour post_id={POST_ID})")
        return

    print(f"Agregation complete des evenements interactions_contenu pour post_id={POST_ID} :")
    for r in rows:
        print(f"  {r.type_evenement:16s} | cible={r.cible!r:12s} | position={r.position_contenu} | {r.nb} evt | {r.premier} -> {r.dernier}")

    cibles_contact = [r for r in rows if r.cible == "contact"]
    print()
    if cibles_contact:
        print(f"✅ {len(cibles_contact)} ligne(s) agregee(s) avec cible='contact' trouvee(s) -- le mini-formulaire 'contact' est bien vu sur cet article.")
    else:
        print("⚠️ AUCUNE ligne avec cible='contact' -- le mini-formulaire 'contact' n'a jamais ete vu/declenche sur cet article, a investiguer plus loin.")


if __name__ == "__main__":
    main()
