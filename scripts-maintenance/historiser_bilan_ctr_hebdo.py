"""
CME — Historisation hebdomadaire du bilan CTR (ECRITURE, PAS lecture seule
-- exception documentee ici et dans CLAUDE.md, meme famille que
creer_table_interactions_contenu.py : celui-ci cree les deux tables,
ce script les alimente chaque semaine).

Contexte (21/11/2026) : demande operateur d'historiser le bilan CTR
hebdomadaire (jusqu'ici purement ad-hoc/glissant, voir
auditer_ctr_potentiel_perdu.py, aucune ecriture nulle part) pour pouvoir
comparer semaine/mois/trimestre/semestre/annee -- voir comparer_bilan_ctr.py
pour la lecture/agregation de cet historique. Decisions operateur
(echange du 21/11) : stockage BigQuery dedie, les DEUX niveaux de detail
(silo + top articles), comparaisons superieures calculees par agregation
SQL pure de cet historique (jamais de nouvelle requete GSC a ces
granularites).

**Pourquoi MERCREDI et pas LUNDI (demande initiale de l'operateur)** :
`apps-scripts/cme-gsc-to-bq.gs` definit `CFG.GSC_LAG = 3` -- les donnees
GSC d'un jour calendaire ne sont considerees fiables qu'a partir de
J+3. Pour une semaine lundi-dimanche, le dernier jour a couvrir est le
dimanche -- fiable seulement a partir du dimanche+3 jours = mercredi
SUIVANT. Un run du lundi (demande initiale) n'aurait donc jamais de
donnees fiables sur le samedi/dimanche de la semaine qui vient de se
terminer (seulement 1 jour de marge, il en faut 3) -- verifie par calcul
de dates le 21/11/2026. Le mercredi est le premier jour qui garantit une
semaine complete 100% fiable. Signale a l'operateur, qui a tranche pour
"decaler le run au mercredi" plutot que d'accepter une semaine
partiellement fiable ou de retarder le calcul a +2 jours
supplementaires.

`semaine_fiable_la_plus_recente()` ci-dessous est volontairement
GENERIQUE (pas seulement valide pour un run du mercredi) : elle recule
semaine par semaine jusqu'a trouver la plus recente semaine lundi-dimanche
dont le dimanche a au moins `GSC_LAG` jours de marge par rapport a la
date de reference -- robuste a un `workflow_dispatch` manuel un autre
jour de la semaine (ex. rattrapage), pas seulement au cron du mercredi.

**Garde de demarrage** : l'operateur a explicitement demande de SAUTER la
toute premiere occurrence a venir au moment de la demande (mercredi
25/11/2026, trop proche pour avoir ete anticipee dans le planning) et de
commencer reellement a partir de celle d'apres (mercredi 02/12/2026) --
meme logique que l'intention initiale ("on exclut le suivant, a partir de
celui d'apres"), transposee du lundi au mercredi suite au changement de
cadence. `--force` permet de passer cette garde (rattrapage manuel
voulu).

**Idempotent** : une ligne existante pour le meme `periode_debut` est
supprimee (DELETE parametre, jamais de concatenation de chaine -- evite
toute la famille de bugs d'echappement d'apostrophe deja rencontree
ailleurs dans ce fichier/CLAUDE.md) puis reinseree -- un re-run sur la
meme semaine (rattrapage, correction) ecrase proprement sans dupliquer.

**Reutilise la grille CTR attendu de auditer_ctr_potentiel_perdu.py par
IMPORT direct** (meme fichier, meme repertoire scripts-maintenance/) --
jamais une seconde copie de la grille qui pourrait deriver de l'original.

Execution via le pont GitHub Actions (maintenance-a-la-demande.yml) :
necessite les memes credentials BigQuery (GOOGLE_APPLICATION_CREDENTIALS)
que les scripts habituels. Les deux tables cibles doivent déjà exister
(creer_tables_historique_ctr.py, execute une seule fois avant le tout
premier run de ce script).

USAGE :
  python3 historiser_bilan_ctr_hebdo.py                       # semaine fiable la plus recente, garde de date active
  python3 historiser_bilan_ctr_hebdo.py --force                # ignore la garde de date de demarrage
  python3 historiser_bilan_ctr_hebdo.py --date-reference=2026-12-03   # rejoue pour une date de reference donnee (tests/rattrapage)
  python3 historiser_bilan_ctr_hebdo.py --position-max=20 --impressions-min=50 --top=15
"""
import sys
import os
from datetime import date, datetime, timedelta, timezone

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

# Meme repertoire (scripts-maintenance/) -- import direct, aucune
# duplication de la grille CTR attendu ni de sa fonction.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auditer_ctr_potentiel_perdu import ctr_attendu  # noqa: E402

PROJECT_ID = "seo-data-hub-cme"
DATASET = "04_pipeline_seo"
TABLE_SILO = f"{PROJECT_ID}.{DATASET}.bilan_ctr_historique_silo"
TABLE_ARTICLES = f"{PROJECT_ID}.{DATASET}.bilan_ctr_historique_articles"

GSC_LAG = 3  # jours -- doit rester identique a CFG.GSC_LAG dans cme-gsc-to-bq.gs

# Demande operateur du 21/11/2026 : sauter la toute premiere occurrence du
# mercredi a venir au moment de la decision (trop proche, pas anticipee),
# demarrer reellement a partir de celle d'apres.
DATE_DEBUT_HISTORISATION = date(2026, 12, 2)


def semaine_fiable_la_plus_recente(date_reference, gsc_lag=GSC_LAG):
    """Renvoie (lundi, dimanche) de la semaine lundi-dimanche la plus
    recente dont TOUS les jours ont au moins `gsc_lag` jours de marge par
    rapport a `date_reference` -- recule semaine par semaine jusqu'a
    trouver une semaine entierement fiable. `date.weekday()` : lundi=0,
    dimanche=6.
    """
    jours_depuis_dimanche = (date_reference.weekday() - 6) % 7
    if jours_depuis_dimanche == 0:
        # date_reference est elle-meme un dimanche : cette semaine n'est
        # pas encore terminee (le dimanche n'est pas fini) -- repart sur
        # le dimanche precedent.
        jours_depuis_dimanche = 7
    dimanche_candidat = date_reference - timedelta(days=jours_depuis_dimanche)
    while (date_reference - dimanche_candidat).days < gsc_lag:
        dimanche_candidat -= timedelta(days=7)
    lundi_candidat = dimanche_candidat - timedelta(days=6)
    return lundi_candidat, dimanche_candidat


def parse_args():
    force = False
    date_reference = date.today()
    position_max = 20.0
    impressions_min = 50
    top = 15
    for arg in sys.argv:
        if arg == "--force":
            force = True
        elif arg.startswith("--date-reference="):
            date_reference = date.fromisoformat(arg.split("=", 1)[1])
        elif arg.startswith("--position-max="):
            position_max = float(arg.split("=", 1)[1])
        elif arg.startswith("--impressions-min="):
            impressions_min = int(arg.split("=", 1)[1])
        elif arg.startswith("--top="):
            top = int(arg.split("=", 1)[1])
    return force, date_reference, position_max, impressions_min, top


def supprimer_lignes_existantes(client, table_ref, lundi):
    query = f"DELETE FROM `{table_ref}` WHERE periode_debut = @lundi"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("lundi", "DATE", lundi.isoformat())]
    )
    client.query(query, job_config=job_config).result()


def main():
    force, date_reference, position_max, impressions_min, top = parse_args()

    if date_reference < DATE_DEBUT_HISTORISATION and not force:
        print(f"⏸️  Historisation pas encore active (demarrage prevu le "
              f"{DATE_DEBUT_HISTORISATION.isoformat()}, demande operateur -- "
              f"sauter la toute premiere occurrence a venir) -- date de "
              f"reference : {date_reference.isoformat()}. Utiliser --force "
              f"pour forcer malgre tout.")
        return

    lundi, dimanche = semaine_fiable_la_plus_recente(date_reference)
    print(f"📅 Semaine historisee : {lundi.isoformat()} (lundi) -> "
          f"{dimanche.isoformat()} (dimanche) -- "
          f"GSC_LAG={GSC_LAG}j, date de reference={date_reference.isoformat()}\n")

    client = bigquery.Client(project=PROJECT_ID)
    date_calcul = datetime.now(timezone.utc).isoformat()

    date_params = [
        bigquery.ScalarQueryParameter("debut", "DATE", lundi.isoformat()),
        bigquery.ScalarQueryParameter("fin", "DATE", dimanche.isoformat()),
    ]

    # --- 1) Bilan par silo, fenetre exacte (pas glissante).
    query_silo = f"""
        SELECT
            silo,
            SUM(clics) AS clics,
            SUM(impressions) AS impressions,
            SAFE_DIVIDE(SUM(clics), SUM(impressions)) AS ctr_reel,
            SAFE_DIVIDE(SUM(position * impressions), SUM(impressions)) AS position_moyenne
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date BETWEEN @debut AND @fin
          AND silo IS NOT NULL AND silo != ''
        GROUP BY silo
    """
    job_config = bigquery.QueryJobConfig(query_parameters=date_params)
    try:
        df_silo = client.query(query_silo, job_config=job_config).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery (bilan silo) : {e}")

    lignes_silo = []
    print(f"{'='*90}\nBILAN CTR PAR SILO -- {lundi.isoformat()} / {dimanche.isoformat()}\n{'='*90}")
    if df_silo.empty:
        print("⚠️ Aucune donnee sur cette semaine.")
    else:
        for _, row in df_silo.iterrows():
            pos = row["position_moyenne"]
            impressions = int(row["impressions"]) if row["impressions"] == row["impressions"] else 0
            if pos != pos or impressions == 0:  # NaN -- pas d'impression sur la semaine
                print(f"  {row['silo']:<28} aucune impression cette semaine")
                continue
            attendu = ctr_attendu(pos)
            reel = row["ctr_reel"] if row["ctr_reel"] == row["ctr_reel"] else 0.0
            ecart_pts = (attendu - reel) * 100
            print(f"  {row['silo']:<28} clics={int(row['clics']):<5} "
                  f"impr.={impressions:<7} pos.moy={pos:.1f}  "
                  f"CTR reel={reel*100:.2f}%  CTR attendu≈{attendu*100:.2f}%  "
                  f"ecart={ecart_pts:+.2f}pts")
            lignes_silo.append({
                "periode_debut": lundi.isoformat(),
                "periode_fin": dimanche.isoformat(),
                "silo": row["silo"],
                "clics": int(row["clics"]),
                "impressions": impressions,
                "position_moyenne": float(pos),
                "ctr_reel": float(reel),
                "ctr_attendu": float(attendu),
                "ecart_pts": float(ecart_pts),
                "date_calcul": date_calcul,
            })

    # --- 2) Top articles a fort potentiel mais CTR faible, fenetre exacte.
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
        WHERE date BETWEEN @debut AND @fin
        GROUP BY page
        HAVING impressions >= {impressions_min}
    """
    job_config = bigquery.QueryJobConfig(query_parameters=date_params)
    try:
        df_pages = client.query(query_pages, job_config=job_config).to_dataframe()
    except Exception as e:
        sys.exit(f"❌ Erreur BigQuery (pages) : {e}")

    lignes_articles = []
    print(f"\n{'='*90}\nTOP {top} ARTICLES A FORT POTENTIEL MAIS CTR FAIBLE "
          f"(position <= {position_max}, >= {impressions_min} impr.)\n{'='*90}")

    if df_pages.empty:
        print("⚠️ Aucune page ne depasse le seuil d'impressions cette semaine.")
    else:
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
            print("✅ Aucun article ne ressort comme 'bien positionne mais sous-clique' cette semaine.")
        else:
            for rang, (_, row) in enumerate(candidats.iterrows(), start=1):
                print(f"  #{rang} — {row['page']} ({row['silo']}/{row['sous_silo']}) "
                      f"pos={row['position_moyenne']:.1f} impr={int(row['impressions'])} "
                      f"clics={int(row['clics'])} ecart={row['ecart_pts']:+.2f}pts "
                      f"clics_manques≈{row['clics_manques_estimes']:.1f}")
                lignes_articles.append({
                    "periode_debut": lundi.isoformat(),
                    "periode_fin": dimanche.isoformat(),
                    "rang": rang,
                    "url": row["page"],
                    "silo": row["silo"],
                    "sous_silo": row["sous_silo"],
                    "position_moyenne": float(row["position_moyenne"]),
                    "impressions": int(row["impressions"]),
                    "clics_reels": int(row["clics"]),
                    "ctr_reel": float(row["ctr_reel"]) if row["ctr_reel"] == row["ctr_reel"] else 0.0,
                    "ctr_attendu": float(row["ctr_attendu"]),
                    "ecart_pts": float(row["ecart_pts"]),
                    "clics_manques_estimes": float(row["clics_manques_estimes"]),
                    "date_calcul": date_calcul,
                })

    # --- 3) Ecriture idempotente (DELETE parametre puis insert_rows_json).
    supprimer_lignes_existantes(client, TABLE_SILO, lundi)
    supprimer_lignes_existantes(client, TABLE_ARTICLES, lundi)

    erreurs = []
    if lignes_silo:
        erreurs += client.insert_rows_json(TABLE_SILO, lignes_silo)
    if lignes_articles:
        erreurs += client.insert_rows_json(TABLE_ARTICLES, lignes_articles)

    if erreurs:
        sys.exit(f"❌ Erreur(s) d'insertion BigQuery : {erreurs}")

    print(f"\n✅ Historisation ecrite : {len(lignes_silo)} ligne(s) silo + "
          f"{len(lignes_articles)} ligne(s) article pour la semaine "
          f"{lundi.isoformat()} -> {dimanche.isoformat()}.")


if __name__ == "__main__":
    main()
