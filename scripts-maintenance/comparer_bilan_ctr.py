"""
CME — Comparaison du bilan CTR par periode (semaine/mois/trimestre/
semestre/annee), a partir de l'historique deja stocke par
historiser_bilan_ctr_hebdo.py. Lecture seule, aucune ecriture.

Contexte (21/11/2026) : suite directe de l'historisation hebdomadaire --
l'operateur veut comparer le bilan CTR par semaine/mois/trimestre/
semestre/annee. Decision operateur explicite ("la plus stratégique et
rigoureuse") : ces comparaisons ne refont JAMAIS de requete GSC -- elles
agregent par SQL les lignes hebdomadaires deja historisees dans
`bilan_ctr_historique_silo` (voir creer_tables_historique_ctr.py). Ca
garantit que la comparaison d'un mois/trimestre/etc. est TOUJOURS la
somme exacte des semaines qui le composent, sans jamais diverger d'une
nouvelle requete a fenetre glissante (qui donnerait un chiffre legerement
different a chaque execution, meme pour une periode "close").

**Rigueur de la recombinaison -- point le plus important de ce script** :
`position_moyenne` est deja ponderee par impressions AU NIVEAU DE LA
SEMAINE (voir historiser_bilan_ctr_hebdo.py :
SUM(position*impressions)/SUM(impressions)). Pour recombiner plusieurs
semaines en un mois/trimestre/semestre/annee, il FAUT reponderer par
impressions une seconde fois :
    position_moyenne_periode =
        SUM(position_moyenne_semaine * impressions_semaine) / SUM(impressions_semaine)
Une simple moyenne arithmetique des `position_moyenne` hebdomadaires
serait fausse (elle donnerait le meme poids a une semaine de 50
impressions qu'a une semaine de 5000). `ctr_attendu` est ensuite
RE-DERIVE de cette position recombinee via la grille sectorielle
(import direct de `ctr_attendu()`, auditer_ctr_potentiel_perdu.py) --
jamais une moyenne des `ctr_attendu` hebdomadaires stockes, qui ne serait
pas la valeur attendue pour la VRAIE position moyenne de la periode.

Les clics/impressions se recombinent par simple somme (additifs par
construction). `ctr_reel` de la periode = SUM(clics)/SUM(impressions)
(pas une moyenne des ctr_reel hebdomadaires non plus, meme raison).

Pour le TOP articles (`bilan_ctr_historique_articles`), AUCUNE
recombinaison mathematique n'a de sens a une granularite superieure
(deux semaines peuvent avoir des top 15 completement differents, un
article peut sortir et rentrer du top) -- ce script affiche a la place,
pour la granularite demandee, le TOP articles agrege par URL sur
l'ensemble de la periode (SUM clics/impressions, recalcul ctr/ecart a
partir de cet agregat), ce qui reste rigoureusement correct (une vraie
recombinaison par URL, pas par rang).

**Comparaison periode vs periode precedente** : la periode la plus
recente COMPLETE (pas la periode en cours, forcement partielle) est
comparee a la periode immediatement precedente, meme duree.

Execution via le pont GitHub Actions (maintenance-a-la-demande.yml) --
meme credentials BigQuery, meme principe "resultat dans les logs du
run, rien commite" que les audits recurrents existants.

USAGE :
  python3 comparer_bilan_ctr.py --periode=semaine
  python3 comparer_bilan_ctr.py --periode=mois
  python3 comparer_bilan_ctr.py --periode=trimestre
  python3 comparer_bilan_ctr.py --periode=semestre
  python3 comparer_bilan_ctr.py --periode=annee
  python3 comparer_bilan_ctr.py --periode=mois --top=10
"""
import sys
import os
from datetime import date, timedelta

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auditer_ctr_potentiel_perdu import ctr_attendu  # noqa: E402

PROJECT_ID = "seo-data-hub-cme"
DATASET = "04_pipeline_seo"
TABLE_SILO = f"{PROJECT_ID}.{DATASET}.bilan_ctr_historique_silo"
TABLE_ARTICLES = f"{PROJECT_ID}.{DATASET}.bilan_ctr_historique_articles"

PERIODES_VALIDES = ("semaine", "mois", "trimestre", "semestre", "annee")


def borne_periode(d, periode):
    """Renvoie (debut, fin_exclusive) de la periode de type `periode`
    contenant la date `d` -- `fin_exclusive` est le premier jour de la
    periode suivante (bornes demi-ouvertes, pratique pour comparer).
    """
    if periode == "semaine":
        debut = d - timedelta(days=d.weekday())  # lundi de cette semaine
        fin = debut + timedelta(days=7)
    elif periode == "mois":
        debut = d.replace(day=1)
        fin = date(debut.year + (1 if debut.month == 12 else 0),
                    1 if debut.month == 12 else debut.month + 1, 1)
    elif periode == "trimestre":
        mois_debut_trimestre = ((d.month - 1) // 3) * 3 + 1
        debut = date(d.year, mois_debut_trimestre, 1)
        mois_fin = mois_debut_trimestre + 3
        annee_fin = d.year + (1 if mois_fin > 12 else 0)
        mois_fin = mois_fin - 12 if mois_fin > 12 else mois_fin
        fin = date(annee_fin, mois_fin, 1)
    elif periode == "semestre":
        mois_debut_semestre = 1 if d.month <= 6 else 7
        debut = date(d.year, mois_debut_semestre, 1)
        fin = date(d.year + (1 if mois_debut_semestre == 7 else 0),
                    1 if mois_debut_semestre == 7 else 7, 1)
    elif periode == "annee":
        debut = date(d.year, 1, 1)
        fin = date(d.year + 1, 1, 1)
    else:
        raise ValueError(f"periode inconnue : {periode}")
    return debut, fin


def periode_precedente(debut, periode):
    """Renvoie (debut, fin_exclusive) de la periode immediatement avant
    `debut` -- un jour avant `debut` tombe forcement dans la periode
    precedente, quelle que soit sa longueur variable (mois/trimestre).
    """
    return borne_periode(debut - timedelta(days=1), periode)


def periode_est_complete(fin_exclusive, aujourdhui):
    return fin_exclusive <= aujourdhui


def agreger_silo(client, debut, fin_exclusive):
    """Agrege les lignes hebdomadaires de bilan_ctr_historique_silo dont
    periode_debut tombe dans [debut, fin_exclusive) -- reponderation par
    impressions, ctr_attendu re-derive (voir docstring du module)."""
    query = f"""
        SELECT
            silo,
            SUM(clics) AS clics,
            SUM(impressions) AS impressions,
            SAFE_DIVIDE(SUM(position_moyenne * impressions), SUM(impressions)) AS position_moyenne
        FROM `{TABLE_SILO}`
        WHERE periode_debut >= @debut AND periode_debut < @fin
        GROUP BY silo
        ORDER BY clics DESC
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("debut", "DATE", debut.isoformat()),
        bigquery.ScalarQueryParameter("fin", "DATE", fin_exclusive.isoformat()),
    ])
    df = client.query(query, job_config=job_config).to_dataframe()
    resultats = {}
    for _, row in df.iterrows():
        pos = row["position_moyenne"]
        impressions = int(row["impressions"]) if row["impressions"] == row["impressions"] else 0
        if pos != pos or impressions == 0:
            continue
        attendu = ctr_attendu(pos)
        reel = row["clics"] / impressions if impressions else 0.0
        resultats[row["silo"]] = {
            "clics": int(row["clics"]),
            "impressions": impressions,
            "position_moyenne": float(pos),
            "ctr_reel": reel,
            "ctr_attendu": attendu,
            "ecart_pts": (attendu - reel) * 100,
        }
    return resultats


def top_articles_periode(client, debut, fin_exclusive, top):
    """Agrege bilan_ctr_historique_articles par URL sur toute la periode
    (pas par rang hebdomadaire -- voir docstring du module) et renvoie le
    top N par clics manques estimes recalcules sur l'agregat."""
    query = f"""
        SELECT
            url,
            ANY_VALUE(silo) AS silo,
            ANY_VALUE(sous_silo) AS sous_silo,
            SUM(clics_reels) AS clics,
            SUM(impressions) AS impressions,
            SAFE_DIVIDE(SUM(position_moyenne * impressions), SUM(impressions)) AS position_moyenne
        FROM `{TABLE_ARTICLES}`
        WHERE periode_debut >= @debut AND periode_debut < @fin
        GROUP BY url
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("debut", "DATE", debut.isoformat()),
        bigquery.ScalarQueryParameter("fin", "DATE", fin_exclusive.isoformat()),
    ])
    df = client.query(query, job_config=job_config).to_dataframe()
    lignes = []
    for _, row in df.iterrows():
        pos = row["position_moyenne"]
        impressions = int(row["impressions"]) if row["impressions"] == row["impressions"] else 0
        if pos != pos or impressions == 0:
            continue
        attendu = ctr_attendu(pos)
        reel = row["clics"] / impressions if impressions else 0.0
        clics_manques = max(0.0, (attendu - reel) * impressions)
        if clics_manques <= 0:
            continue
        lignes.append({
            "url": row["url"], "silo": row["silo"], "sous_silo": row["sous_silo"],
            "position_moyenne": float(pos), "impressions": impressions,
            "clics": int(row["clics"]), "ctr_reel": reel, "ctr_attendu": attendu,
            "ecart_pts": (attendu - reel) * 100, "clics_manques_estimes": clics_manques,
        })
    lignes.sort(key=lambda x: x["clics_manques_estimes"], reverse=True)
    return lignes[:top]


def afficher_bilan_silo(titre, bilan):
    print(f"\n{titre}")
    if not bilan:
        print("  ⚠️ Aucune donnee historisee sur cette periode.")
        return
    total_clics = sum(v["clics"] for v in bilan.values())
    total_impr = sum(v["impressions"] for v in bilan.values())
    for silo, v in sorted(bilan.items(), key=lambda kv: kv[1]["clics"], reverse=True):
        print(f"  {silo:<28} clics={v['clics']:<6} impr.={v['impressions']:<8} "
              f"pos.moy={v['position_moyenne']:.1f}  CTR reel={v['ctr_reel']*100:.2f}%  "
              f"CTR attendu≈{v['ctr_attendu']*100:.2f}%  ecart={v['ecart_pts']:+.2f}pts")
    ctr_global = total_clics / total_impr if total_impr else 0.0
    print(f"  {'TOTAL':<28} clics={total_clics:<6} impr.={total_impr:<8} CTR global={ctr_global*100:.2f}%")


def afficher_comparaison(bilan_actuel, bilan_precedent):
    print("\n--- Evolution vs periode precedente (meme duree) ---")
    silos = sorted(set(bilan_actuel) | set(bilan_precedent))
    if not silos:
        print("  ⚠️ Rien a comparer.")
        return
    for silo in silos:
        actuel = bilan_actuel.get(silo)
        precedent = bilan_precedent.get(silo)
        if actuel is None:
            print(f"  {silo:<28} absent cette periode (etait present avant)")
            continue
        if precedent is None:
            print(f"  {silo:<28} nouveau -- clics={actuel['clics']} (aucune donnee la periode precedente)")
            continue
        delta_clics = actuel["clics"] - precedent["clics"]
        delta_ctr_pts = (actuel["ctr_reel"] - precedent["ctr_reel"]) * 100
        delta_pos = actuel["position_moyenne"] - precedent["position_moyenne"]
        print(f"  {silo:<28} clics {precedent['clics']}→{actuel['clics']} ({delta_clics:+d})  "
              f"CTR {precedent['ctr_reel']*100:.2f}%→{actuel['ctr_reel']*100:.2f}% ({delta_ctr_pts:+.2f}pts)  "
              f"position {precedent['position_moyenne']:.1f}→{actuel['position_moyenne']:.1f} ({delta_pos:+.1f})")


def parse_args():
    periode = "semaine"
    top = 15
    for arg in sys.argv:
        if arg.startswith("--periode="):
            periode = arg.split("=", 1)[1]
        elif arg.startswith("--top="):
            top = int(arg.split("=", 1)[1])
    if periode not in PERIODES_VALIDES:
        sys.exit(f"❌ --periode doit etre l'un de {PERIODES_VALIDES} (recu : {periode!r})")
    return periode, top


def main():
    periode, top = parse_args()
    aujourdhui = date.today()

    debut, fin = borne_periode(aujourdhui, periode)
    if not periode_est_complete(fin, aujourdhui):
        # la periode en cours n'est pas terminee -- comparer la DERNIERE
        # periode complete, pas la periode en cours (forcement partielle).
        debut, fin = periode_precedente(debut, periode)
    debut_prec, fin_prec = periode_precedente(debut, periode)

    print(f"🔎 Bilan CTR — periode : {periode} — {debut.isoformat()} -> "
          f"{(fin - timedelta(days=1)).isoformat()} (vs periode precedente "
          f"{debut_prec.isoformat()} -> {(fin_prec - timedelta(days=1)).isoformat()})\n")
    print("⚠️ Calcule par agregation de l'historique hebdomadaire deja stocke "
          "(bilan_ctr_historique_silo/_articles) -- aucune nouvelle requete GSC "
          "a cette granularite.\n")

    client = bigquery.Client(project=PROJECT_ID)

    bilan_actuel = agreger_silo(client, debut, fin)
    bilan_precedent = agreger_silo(client, debut_prec, fin_prec)

    afficher_bilan_silo(f"{'='*90}\nBILAN CTR PAR SILO -- {periode.upper()}\n{'='*90}", bilan_actuel)
    afficher_comparaison(bilan_actuel, bilan_precedent)

    top_articles = top_articles_periode(client, debut, fin, top)
    print(f"\n{'='*90}\nTOP {top} ARTICLES A FORT POTENTIEL MAIS CTR FAIBLE -- {periode.upper()} "
          f"(agrege par URL sur toute la periode)\n{'='*90}")
    if not top_articles:
        print("✅ Aucun article ne ressort comme 'bien positionne mais sous-clique' sur cette periode.")
    else:
        for rang, ligne in enumerate(top_articles, start=1):
            print(f"  #{rang} — {ligne['url']} ({ligne['silo']}/{ligne['sous_silo']}) "
                  f"pos={ligne['position_moyenne']:.1f} impr={ligne['impressions']} "
                  f"clics={ligne['clics']} ecart={ligne['ecart_pts']:+.2f}pts "
                  f"clics_manques≈{ligne['clics_manques_estimes']:.1f}")


if __name__ == "__main__":
    main()
