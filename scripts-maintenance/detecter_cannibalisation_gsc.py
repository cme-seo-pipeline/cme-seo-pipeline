"""
CME — Detection de cannibalisation SEO par requete Google Search Console.

Different de `agent_orcaas_analyser_chevauchement` (dans pipeline.py), qui
ne regarde QUE les pages en etat d'indexation "Crawled - currently not
indexed" et compare des pages voisines par prefixe d'URL. Ici on part des
VRAIES donnees de requetes GSC (01_raw.gsc_queries, synchronisees
quotidiennement par cme-gsc-to-bq.gs) : pour chaque requete tapee par de
vrais internautes, on regarde si plusieurs pages DU SITE se disputent son
classement -- c'est la definition la plus directe de la cannibalisation de
mots-cles, independamment de l'etat d'indexation.

Lecture seule (detection uniquement, aucune correction automatique : fusionner
du contenu ou choisir quelle page garder est une decision editoriale, pas un
automatisme).

USAGE :
  python3 detecter_cannibalisation_gsc.py                    # fenetre par defaut (90 jours)
  python3 detecter_cannibalisation_gsc.py --jours=30          # fenetre personnalisee
  python3 detecter_cannibalisation_gsc.py --impressions-min=30  # seuil de bruit (defaut 30)

Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def parse_args():
    jours = 90
    impressions_min = 30
    for arg in sys.argv:
        if arg.startswith("--jours="):
            jours = int(arg.split("=", 1)[1])
        elif arg.startswith("--impressions-min="):
            impressions_min = int(arg.split("=", 1)[1])
    return jours, impressions_min


def main():
    jours, impressions_min = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print(f"🔎 Fenetre d'analyse : {jours} derniers jours — seuil de bruit : "
          f"{impressions_min} impressions cumulees minimum par requete\n")

    # Agrege par (requete, page) sur la fenetre, puis ne garde que les
    # requetes couvertes par plusieurs pages DISTINCTES du site -- c'est la
    # definition operationnelle de la cannibalisation : Google hesite entre
    # plusieurs de nos propres pages pour la meme intention de recherche.
    query = f"""
        WITH agrege AS (
            SELECT
                query,
                page,
                ANY_VALUE(silo) AS silo,
                ANY_VALUE(sous_silo) AS sous_silo,
                SUM(impressions) AS impressions,
                SUM(clics) AS clics,
                AVG(position) AS position_moyenne
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {jours} DAY)
            GROUP BY query, page
        ),
        par_requete AS (
            SELECT
                query,
                COUNT(DISTINCT page) AS nb_pages,
                SUM(impressions) AS impressions_totales
            FROM agrege
            GROUP BY query
        )
        SELECT a.*
        FROM agrege a
        JOIN par_requete pr ON pr.query = a.query
        WHERE pr.nb_pages > 1 AND pr.impressions_totales >= {impressions_min}
        ORDER BY pr.impressions_totales DESC, a.query, a.impressions DESC
    """

    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery : {e}")

    if df.empty:
        print("✅ Aucune cannibalisation detectee sur cette fenetre / ce seuil.")
        return

    cas_forts = []
    cas_faibles = []

    for q, groupe in df.groupby("query", sort=False):
        groupe = groupe.sort_values("impressions", ascending=False).reset_index(drop=True)
        total_impressions = int(groupe["impressions"].sum())
        top = groupe.iloc[0]
        second = groupe.iloc[1]

        # "Forte" : la 2e page capte une part significative des impressions
        # ET se classe elle-meme dans une zone ou elle pourrait raisonnablement
        # etre cliquee (position <= 30) -- signe que Google hesite vraiment
        # entre les deux, pas juste un bruit marginal de longue traine.
        part_seconde = second["impressions"] / total_impressions if total_impressions else 0
        est_forte = part_seconde >= 0.25 and second["position_moyenne"] <= 30

        cas = {
            "query": q,
            "silo": top["silo"],
            "sous_silo": top["sous_silo"],
            "impressions_totales": total_impressions,
            "pages": groupe[["page", "impressions", "clics", "position_moyenne"]].to_dict("records"),
        }
        (cas_forts if est_forte else cas_faibles).append(cas)

    print(f"{'='*70}")
    print("RAPPORT — CANNIBALISATION DE MOTS-CLES (donnees GSC)")
    print(f"{'='*70}")
    print(f"Requetes avec plusieurs pages en concurrence : {df['query'].nunique()}")
    print(f"  dont forte concurrence (action prioritaire) : {len(cas_forts)}")
    print(f"  dont concurrence faible (a surveiller)       : {len(cas_faibles)}")
    print(f"{'='*70}")

    def afficher(titre_section, liste):
        if not liste:
            print(f"\n✅ {titre_section} : aucun cas")
            return
        print(f"\n⚠️ {titre_section} ({len(liste)}) :")
        for cas in sorted(liste, key=lambda c: c["impressions_totales"], reverse=True):
            print(f"\n  🔑 \"{cas['query']}\" — {cas['silo']} / {cas['sous_silo']}")
            print(f"     Impressions cumulees (toutes pages) : {cas['impressions_totales']}")
            for p in cas["pages"]:
                print(f"       - {p['page']}")
                print(f"         impressions={p['impressions']} clics={p['clics']} "
                      f"position_moyenne={p['position_moyenne']:.1f}")

    afficher("CANNIBALISATION FORTE — action prioritaire (fusionner, differencier ou rediriger)", cas_forts)
    afficher("CANNIBALISATION FAIBLE — a surveiller, pas forcement a traiter", cas_faibles)


if __name__ == "__main__":
    main()
