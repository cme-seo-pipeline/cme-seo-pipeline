"""
CME — Bilan CTR hebdomadaire : taux de clic reel vs attendu, et articles
a fort potentiel (bien positionnes) mais penalises par un CTR faible.

Demande operateur (14/11/2026) : un bilan recurrent, chaque vendredi
matin, du taux de CTR et des articles qui "meriteraient" plus de clics
vu leur position, mais n'en recoivent pas -- probable probleme de
titre/meta-description (snippet SERP) plutot que de classement.

Lecture seule, aucune ecriture. Meme source que
`detecter_cannibalisation_gsc.py`/`classement_silos_trafic_organique.py`
(`01_raw.gsc_queries`, colonnes date/query/page/clics/impressions/ctr/
position/silo/sous_silo).

METHODE : le CTR "normal" attendu depend fortement de la position
moyenne dans les resultats Google (position 1 = ~28% de CTR attendu,
position 20 = ~1%, etc.) -- comparer un CTR brut entre deux pages a des
positions tres differentes n'a pas de sens. Ce script agrege par PAGE
(toutes requetes confondues), calcule un CTR attendu a partir d'une grille
de reference (benchmarks sectoriels moyens, PAS specifiques a ce site --
le volume de clics de ce site est encore trop faible pour construire sa
propre courbe fiable, voir classement_silos_trafic_organique.py), puis
isole les pages dont la position est deja correcte (donc du "potentiel"
reel, visible par Google) mais dont le CTR reel est nettement sous ce
qu'on attendrait -- signe le plus probable : titre/meta peu engageants,
pas un probleme de classement.

USAGE :
  python3 auditer_ctr_potentiel_perdu.py                          # defaut : 90j, position<=20, 50 impr. min, top 15
  python3 auditer_ctr_potentiel_perdu.py --jours=28 --position-max=10 --impressions-min=30 --top=20
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"

# Grille de CTR attendu par position moyenne -- benchmarks sectoriels
# agreges couramment cites (ex. Advanced Web Ranking / Backlinko),
# INDICATIFS : a affiner un jour avec la propre courbe du site une fois
# qu'il aura assez de volume de clics en position 1-10 pour etre fiable.
PALIERS_CTR_ATTENDU = [
    (1, 0.28), (2, 0.15), (3, 0.11), (4, 0.08), (5, 0.07),
    (6, 0.05), (8, 0.04), (10, 0.03), (15, 0.015), (20, 0.01),
    (30, 0.005),
]


def ctr_attendu(position):
    for borne, ctr in PALIERS_CTR_ATTENDU:
        if position <= borne:
            return ctr
    return 0.002


def parse_args():
    jours = 90
    position_max = 20.0
    impressions_min = 50
    top = 15
    for arg in sys.argv:
        if arg.startswith("--jours="):
            jours = int(arg.split("=", 1)[1])
        elif arg.startswith("--position-max="):
            position_max = float(arg.split("=", 1)[1])
        elif arg.startswith("--impressions-min="):
            impressions_min = int(arg.split("=", 1)[1])
        elif arg.startswith("--top="):
            top = int(arg.split("=", 1)[1])
    return jours, position_max, impressions_min, top


def main():
    jours, position_max, impressions_min, top = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print(f"🔎 Bilan CTR — fenetre glissante : {jours} derniers jours — "
          f"'fort potentiel' = position moyenne <= {position_max} et "
          f">= {impressions_min} impressions cumulees\n")
    print("⚠️ Le CTR attendu utilise une grille sectorielle INDICATIVE "
          "(pas une courbe propre a ce site, volume encore trop faible "
          "pour en construire une fiable) -- a lire comme un ordre de "
          "grandeur, pas une cible exacte.\n")

    # --- 1) Bilan global + par silo sur la fenetre.
    query_silo = f"""
        SELECT
            silo,
            SUM(clics) AS clics,
            SUM(impressions) AS impressions,
            SAFE_DIVIDE(SUM(clics), SUM(impressions)) AS ctr_reel,
            SAFE_DIVIDE(SUM(position * impressions), SUM(impressions)) AS position_moyenne
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {jours} DAY)
          AND silo IS NOT NULL AND silo != ''
        GROUP BY silo
        ORDER BY clics DESC
    """
    try:
        df_silo = client.query(query_silo).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery (bilan silo) : {e}")

    print(f"{'='*90}")
    print("BILAN CTR PAR SILO")
    print(f"{'='*90}")
    if df_silo.empty:
        print("⚠️ Aucune donnee sur cette fenetre.")
    else:
        for _, row in df_silo.iterrows():
            pos = row["position_moyenne"]
            if pos != pos:  # NaN -- silo sans impressions sur la fenetre
                print(f"  {row['silo']:<28} aucune impression sur la fenetre")
                continue
            attendu = ctr_attendu(pos)
            reel = row["ctr_reel"] if row["ctr_reel"] == row["ctr_reel"] else 0.0
            ecart_pts = (attendu - reel) * 100
            print(f"  {row['silo']:<28} clics={int(row['clics']):<5} "
                  f"impr.={int(row['impressions']):<7} "
                  f"pos.moy={pos:.1f}  "
                  f"CTR reel={reel*100:.2f}%  "
                  f"CTR attendu≈{attendu*100:.2f}%  "
                  f"ecart={ecart_pts:+.2f}pts")

    # --- 2) Par PAGE : potentiel reel (position correcte) mais CTR faible.
    query_pages = f"""
        SELECT
            page,
            ANY_VALUE(silo) AS silo,
            ANY_VALUE(sous_silo) AS sous_silo,
            SUM(clics) AS clics,
            SUM(impressions) AS impressions,
            SAFE_DIVIDE(SUM(clics), SUM(impressions)) AS ctr_reel,
            SAFE_DIVIDE(SUM(position * impressions), SUM(impressions)) AS position_moyenne
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {jours} DAY)
        GROUP BY page
        HAVING impressions >= {impressions_min}
    """
    try:
        df_pages = client.query(query_pages).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery (pages) : {e}")

    print(f"\n{'='*90}")
    print(f"ARTICLES A FORT POTENTIEL MAIS CTR FAIBLE (position <= {position_max}, "
          f">= {impressions_min} impr., top {top} par clics manques estimes)")
    print(f"{'='*90}")

    if df_pages.empty:
        print("⚠️ Aucune page ne depasse le seuil d'impressions sur cette fenetre.")
        return

    df_pages["ctr_attendu"] = df_pages["position_moyenne"].apply(
        lambda p: ctr_attendu(p) if p == p else None
    )
    df_pages["ecart_pts"] = (df_pages["ctr_attendu"] - df_pages["ctr_reel"]) * 100
    df_pages["clics_manques_estimes"] = (
        (df_pages["ctr_attendu"] - df_pages["ctr_reel"]) * df_pages["impressions"]
    ).clip(lower=0)

    candidats = df_pages[
        (df_pages["position_moyenne"] <= position_max)
        & (df_pages["clics_manques_estimes"] > 0)
    ].sort_values("clics_manques_estimes", ascending=False).head(top)

    if candidats.empty:
        print("✅ Aucun article ne ressort comme 'bien positionne mais sous-clique' "
              "sur ce seuil -- rien de flagrant cette semaine.")
        return

    for rang, (_, row) in enumerate(candidats.iterrows(), start=1):
        print(f"\n  #{rang} — {row['page']}")
        print(f"     {row['silo']} / {row['sous_silo']}")
        print(f"     Position moyenne : {row['position_moyenne']:.1f}   "
              f"Impressions : {int(row['impressions'])}   Clics reels : {int(row['clics'])}")
        print(f"     CTR reel : {row['ctr_reel']*100:.2f}%   "
              f"CTR attendu≈ : {row['ctr_attendu']*100:.2f}%   "
              f"ecart : {row['ecart_pts']:+.2f} pts")
        print(f"     ≈ Clics manques estimes sur la fenetre : {row['clics_manques_estimes']:.1f}")

    total_manques = candidats["clics_manques_estimes"].sum()
    print(f"\n{'='*90}")
    print(f"Total clics manques estimes (top {len(candidats)} affiches) : {total_manques:.1f} "
          f"sur {jours} jours.")
    print("Piste d'action la plus probable pour ces pages : retravailler le titre SEO "
          "et la meta-description (snippet affiche dans Google) -- la position elle-meme "
          "n'est pas le probleme ici.")


if __name__ == "__main__":
    main()
