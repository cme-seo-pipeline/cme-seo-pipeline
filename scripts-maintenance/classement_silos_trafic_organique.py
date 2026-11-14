"""
CME — Classement des silos par performance organique reelle (GSC).

Demande operateur (14/11/2026) : "quel silo attire plus de trafic
organique et renforce l'autorite du site" -- classement, trafic
organique, clics, et evolution SEO dans le temps (constante / volatile /
en declin), par silo.

Lecture seule, aucune ecriture. Source de verite : `01_raw.gsc_queries`
(colonnes date, query, page, clics, impressions, ctr, position, silo,
sous_silo -- synchronisee quotidiennement par cme-gsc-to-bq.gs), meme
table que `detecter_cannibalisation_gsc.py`. Contexte additionnel (nombre
d'articles publies par silo, toutes dates) tire de
`04_pipeline_seo.historique_publications` -- colonne `silo` distincte
(convention de nommage potentiellement differente de celle de GSC, les
deux tables etant alimentees par des pipelines distincts : jointure faite
par normalisation de la chaine, pas par egalite stricte, pour ne pas
masquer un silo faute de correspondance exacte).

USAGE :
  python3 classement_silos_trafic_organique.py                # 6 derniers mois
  python3 classement_silos_trafic_organique.py --mois=4
"""
import re
import sys
import unicodedata

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def parse_args():
    mois = 6
    for arg in sys.argv:
        if arg.startswith("--mois="):
            mois = int(arg.split("=", 1)[1])
    return mois


def normaliser_silo(nom):
    """'1. Gaz' / 'Gaz' / 'gaz' -> 'gaz' : pour matcher deux tables dont
    les pipelines de classification par silo sont independants."""
    if not nom:
        return ""
    sans_numero = re.sub(r"^\s*\d+\.\s*", "", str(nom))
    sans_accents = unicodedata.normalize("NFKD", sans_numero).encode("ascii", "ignore").decode()
    return sans_accents.strip().lower()


def main():
    mois = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print(f"🔎 Classement des silos par performance organique reelle (GSC) — "
          f"fenetre : {mois} derniers mois complets + mois en cours\n")

    # 1) Totaux + classement sur toute la fenetre.
    query_totaux = f"""
        SELECT
            silo,
            COUNT(DISTINCT page) AS pages_actives,
            COUNT(DISTINCT sous_silo) AS nb_sous_silos,
            SUM(clics) AS clics_totaux,
            SUM(impressions) AS impressions_totales,
            SAFE_DIVIDE(SUM(clics), SUM(impressions)) AS ctr_moyen,
            SAFE_DIVIDE(SUM(position * impressions), SUM(impressions)) AS position_moyenne_ponderee
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL {mois - 1} MONTH)
          AND silo IS NOT NULL AND silo != ''
        GROUP BY silo
        ORDER BY clics_totaux DESC
    """
    try:
        df_totaux = client.query(query_totaux).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery (totaux) : {e}")

    if df_totaux.empty:
        print("⚠️ Aucune donnee GSC trouvee sur cette fenetre (silo renseigne).")
        return

    # 2) Serie mensuelle par silo, pour juger l'evolution (constante /
    #    croissante / en declin / volatile), pas seulement un total figé.
    query_mensuel = f"""
        SELECT
            silo,
            DATE_TRUNC(date, MONTH) AS mois,
            SUM(clics) AS clics,
            SUM(impressions) AS impressions,
            SAFE_DIVIDE(SUM(position * impressions), SUM(impressions)) AS position_moyenne
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL {mois - 1} MONTH)
          AND silo IS NOT NULL AND silo != ''
        GROUP BY silo, mois
        ORDER BY silo, mois
    """
    try:
        df_mensuel = client.query(query_mensuel).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery (mensuel) : {e}")

    # 3) Contexte : nb d'articles publies par silo (toutes dates), pour
    #    distinguer "gros trafic parce que gros silo" de "petit silo mais
    #    tres efficace par article".
    query_articles = f"""
        SELECT silo, COUNT(*) AS nb_articles
        FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
        GROUP BY silo
    """
    try:
        df_articles = client.query(query_articles).to_dataframe()
    except Exception as e:
        print(f"⚠️ Contexte 'nb articles publies' indisponible ({e}) -- classement poursuivi sans ce contexte.")
        df_articles = None

    nb_articles_par_silo_norm = {}
    if df_articles is not None:
        for _, row in df_articles.iterrows():
            nb_articles_par_silo_norm[normaliser_silo(row["silo"])] = int(row["nb_articles"])

    # --- Evolution par silo : decoupe la serie mensuelle en 1re et 2e
    #     moitie de la fenetre, compare les clics cumules des deux moities.
    def classer_evolution(sous_df):
        sous_df = sous_df.sort_values("mois").reset_index(drop=True)
        n = len(sous_df)
        if n < 2:
            return "➡️ Donnees insuffisantes", sous_df
        moitie = n // 2
        premiere = sous_df.iloc[:max(moitie, 1)]["clics"].sum()
        seconde = sous_df.iloc[max(moitie, 1):]["clics"].sum()
        if premiere == 0 and seconde == 0:
            return "➡️ Aucun clic sur la fenetre", sous_df
        variation = (seconde - premiere) / premiere if premiere else float("inf")
        # Volatilite : la serie mensuelle elle-meme zigzague-t-elle, au-dela
        # de la simple tendance 1re/2e moitie ?
        signes = []
        for i in range(1, n):
            delta = sous_df.loc[i, "clics"] - sous_df.loc[i - 1, "clics"]
            if delta != 0:
                signes.append(1 if delta > 0 else -1)
        volatile = len(signes) >= 3 and len(set(signes)) > 1 and len(signes) >= (n - 1) * 0.6

        if volatile and abs(variation) < 0.5:
            label = "🔀 Volatile (mois en dents de scie)"
        elif variation >= 0.15:
            label = "📈 Croissance"
        elif variation <= -0.15:
            label = "📉 Declin"
        else:
            label = "➡️ Stable"
        return label, sous_df

    print(f"{'='*96}")
    print("CLASSEMENT DES SILOS — PERFORMANCE ORGANIQUE REELLE (Google Search Console)")
    print(f"{'='*96}\n")

    for rang, (_, row) in enumerate(df_totaux.iterrows(), start=1):
        silo = row["silo"]
        sous_df = df_mensuel[df_mensuel["silo"] == silo]
        evolution, serie = classer_evolution(sous_df)
        nb_articles = nb_articles_par_silo_norm.get(normaliser_silo(silo))

        print(f"#{rang} — {silo}")
        print(f"   Clics (periode)        : {int(row['clics_totaux'])}")
        print(f"   Impressions (periode)  : {int(row['impressions_totales'])}")
        print(f"   CTR moyen              : {row['ctr_moyen']*100:.2f}%" if row['ctr_moyen'] == row['ctr_moyen'] else "   CTR moyen              : n/a")
        print(f"   Position moyenne       : {row['position_moyenne_ponderee']:.1f}" if row['position_moyenne_ponderee'] == row['position_moyenne_ponderee'] else "   Position moyenne       : n/a")
        print(f"   Pages actives (clics>0 sur la periode) : {int(row['pages_actives'])}")
        print(f"   Sous-silos presents dans GSC           : {int(row['nb_sous_silos'])}")
        if nb_articles is not None:
            clics_par_article = row['clics_totaux'] / nb_articles if nb_articles else 0
            print(f"   Articles publies (toutes dates)        : {nb_articles}  "
                  f"(≈{clics_par_article:.2f} clic/article sur la periode)")
        else:
            print("   Articles publies (toutes dates)        : n/a (silo absent de historique_publications)")
        print(f"   Evolution sur la fenetre                : {evolution}")
        print("   Détail mensuel (clics / impressions / position moy.) :")
        for _, m in serie.iterrows():
            pos = f"{m['position_moyenne']:.1f}" if m['position_moyenne'] == m['position_moyenne'] else "n/a"
            print(f"     - {str(m['mois'])[:7]} : {int(m['clics'])} clics, {int(m['impressions'])} impr., pos. {pos}")
        print()

    print(f"{'='*96}")
    print("Rappel de lecture : le classement ci-dessus mesure le trafic organique REEL "
          "(clics/impressions GSC), pas un proxy. 'Evolution' compare la 1re et la 2e "
          "moitie de la fenetre -- a interpreter avec prudence pour les silos recents "
          "ou a faible volume (bruit statistique plus eleve).")


if __name__ == "__main__":
    main()
