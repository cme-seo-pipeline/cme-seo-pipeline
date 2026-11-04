"""
CME — Synthese (lecture seule) des zones de clic et de la retention de
lecture dans le contenu des articles, depuis le demarrage de la
cartographie des clics (deploiement confirme le 26/10/2026, puis enrichi
du temps de lecture le 01/11/2026 -- voir CLAUDE.md, sections
"Cartographie des clics").

Demande operateur du 04/11/2026, veille du point de decision du 5-7/11
(repositionnement du CTA selon l'engagement -- voir
claude/objectif-100-leads-mois.md, "Prochaine phase d'analyse" axe 1).

Table source : 04_pipeline_seo.interactions_contenu (creer_table_interactions_contenu.py).
Deux types d'evenements exploites ici :
  - clic_contenu : chaque clic sur un lien/image dans .entry-content.
    section = dernier <h2>/<h3> avant le clic ; position_contenu = nb de
    mots de contenu avant le clic ; scroll_pct = profondeur de scroll au
    moment du clic.
  - lecture_position : jalon tous les ~100 mots lus (position_contenu =
    jalon en mots), avec temps_ms = temps ecoule depuis le chargement de
    la page pour l'atteindre -- sert de proxy de RETENTION (nb de
    sessions distinctes ayant atteint un jalon donne = combien de gens
    lisent encore a ce stade) et de VITESSE de lecture reelle.

LECTURE SEULE -- aucune ecriture. Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 synthese_zones_clic_retention.py [--depuis=2026-10-28]
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"
TABLE = f"{PROJECT_ID}.{DATASET_ID}.interactions_contenu"

DEPUIS_DEFAUT = "2026-10-28"


def parse_args():
    depuis = DEPUIS_DEFAUT
    for arg in sys.argv[1:]:
        if arg.startswith("--depuis="):
            depuis = arg.split("=", 1)[1]
    return depuis


def main():
    depuis = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print(f"📅 Fenetre : depuis le {depuis}\n")

    # 1/ Volume global des deux types d'evenements sur la fenetre
    print("=" * 90)
    print("1/ Volume global sur la fenetre")
    print("=" * 90)
    df_vol = client.query(f"""
        SELECT type_evenement, COUNT(*) AS n, COUNT(DISTINCT session_id) AS sessions
        FROM `{TABLE}`
        WHERE DATE(timestamp) >= '{depuis}'
          AND type_evenement IN ('clic_contenu', 'lecture_position')
        GROUP BY type_evenement
        ORDER BY type_evenement
    """).to_dataframe()
    if df_vol.empty:
        print("  ⚠️ Aucun evenement clic_contenu/lecture_position sur cette fenetre.")
        return
    for _, r in df_vol.iterrows():
        print(f"  {r['type_evenement']:<18} : {int(r['n'])} evenement(s), {int(r['sessions'])} session(s) distincte(s)")

    # 2/ Zones de clic : quelles sections captent le plus de clics
    print("\n" + "=" * 90)
    print("2/ Zones de clic les plus actives (clic_contenu, par section)")
    print("=" * 90)
    df_zones = client.query(f"""
        SELECT
          COALESCE(NULLIF(section, ''), '(aucune section / avant 1er h2-h3)') AS section,
          cible,
          COUNT(*) AS nb_clics,
          COUNT(DISTINCT session_id) AS sessions,
          ROUND(AVG(position_contenu), 0) AS position_mots_moy,
          ROUND(AVG(scroll_pct), 1) AS scroll_pct_moy
        FROM `{TABLE}`
        WHERE DATE(timestamp) >= '{depuis}' AND type_evenement = 'clic_contenu'
        GROUP BY section, cible
        ORDER BY nb_clics DESC
        LIMIT 25
    """).to_dataframe()
    if df_zones.empty:
        print("  (aucun clic_contenu sur cette fenetre)")
    else:
        print(f"  {'section':<45}{'cible':<12}{'clics':<8}{'sessions':<10}{'mots_avant':<12}{'scroll%'}")
        for _, r in df_zones.iterrows():
            sec = (r['section'][:42] + '...') if len(r['section']) > 45 else r['section']
            print(f"  {sec:<45}{r['cible']:<12}{int(r['nb_clics']):<8}{int(r['sessions']):<10}{int(r['position_mots_moy']):<12}{r['scroll_pct_moy']}")

    # 3/ Clics par silo x cible (repartition macro)
    print("\n" + "=" * 90)
    print("3/ Clics par silo x cible")
    print("=" * 90)
    df_silo = client.query(f"""
        SELECT COALESCE(NULLIF(silo,''), '(vide)') AS silo, cible, COUNT(*) AS n,
               COUNT(DISTINCT session_id) AS sessions
        FROM `{TABLE}`
        WHERE DATE(timestamp) >= '{depuis}' AND type_evenement = 'clic_contenu'
        GROUP BY silo, cible
        ORDER BY silo, n DESC
    """).to_dataframe()
    if df_silo.empty:
        print("  (aucun clic_contenu sur cette fenetre)")
    else:
        for _, r in df_silo.iterrows():
            print(f"  {r['silo']:<22} | {r['cible']:<14} : {int(r['n'])} clic(s), {int(r['sessions'])} session(s)")

    # 4/ Retention de lecture : combien de sessions atteignent chaque jalon,
    #    et temps median/moyen pour y arriver
    print("\n" + "=" * 90)
    print("4/ Retention de lecture par jalon (lecture_position, tous silos)")
    print("=" * 90)
    df_retention = client.query(f"""
        SELECT
          position_contenu AS jalon_mots,
          COUNT(DISTINCT session_id) AS sessions_ayant_atteint,
          ROUND(AVG(temps_ms) / 1000, 1) AS temps_moy_sec,
          ROUND(APPROX_QUANTILES(temps_ms, 2)[OFFSET(1)] / 1000, 1) AS temps_median_sec
        FROM `{TABLE}`
        WHERE DATE(timestamp) >= '{depuis}' AND type_evenement = 'lecture_position'
        GROUP BY jalon_mots
        ORDER BY jalon_mots
    """).to_dataframe()
    if df_retention.empty:
        print("  ⚠️ Aucun evenement lecture_position -- colonne temps_ms/tracker deploye le 01-02/11, pas encore assez de volume ou pas encore en prod partout.")
    else:
        premiere_session = df_retention['sessions_ayant_atteint'].iloc[0]
        print(f"  {'mots_lus':<12}{'sessions':<12}{'% retenu vs 1er jalon':<24}{'temps_moy(s)':<14}{'temps_median(s)'}")
        for _, r in df_retention.iterrows():
            pct = round(100 * r['sessions_ayant_atteint'] / premiere_session, 1) if premiere_session else 0
            print(f"  {int(r['jalon_mots']):<12}{int(r['sessions_ayant_atteint']):<12}{pct:<24}{r['temps_moy_sec']:<14}{r['temps_median_sec']}")

    # 5/ Retention par silo, limitee aux jalons les plus informatifs (100/200/300 mots)
    print("\n" + "=" * 90)
    print("5/ Retention par silo aux jalons 100/200/300 mots")
    print("=" * 90)
    df_retention_silo = client.query(f"""
        SELECT
          COALESCE(NULLIF(silo,''), '(vide)') AS silo,
          position_contenu AS jalon_mots,
          COUNT(DISTINCT session_id) AS sessions,
          ROUND(AVG(temps_ms) / 1000, 1) AS temps_moy_sec
        FROM `{TABLE}`
        WHERE DATE(timestamp) >= '{depuis}' AND type_evenement = 'lecture_position'
          AND position_contenu IN (100, 200, 300)
        GROUP BY silo, jalon_mots
        ORDER BY silo, jalon_mots
    """).to_dataframe()
    if df_retention_silo.empty:
        print("  (aucune donnee)")
    else:
        for _, r in df_retention_silo.iterrows():
            print(f"  {r['silo']:<22} | {int(r['jalon_mots'])} mots : {int(r['sessions'])} session(s), {r['temps_moy_sec']}s en moyenne")


if __name__ == "__main__":
    main()
