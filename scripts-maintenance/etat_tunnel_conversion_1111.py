"""
CME — Etat du tunnel de conversion (demande operateur du 11/11/2026,
"ou en est le tunnel de conversion, les stats apres 11 jours").

Contexte (doc projet objectif-100-leads-mois.md, derniere maj 04/11) :
le 04/11, decision de fusionner le mini-formulaire inline en UN SEUL
ECRAN (nom+prenom et telephone affiches ensemble, un seul bouton) avec
une nouvelle cadence (300/500/700/900/1100 puis +400, plafond 7),
commit 9e1a03c (04/11 18:38). Le doc projet notait "deploiement cPanel
en attente" a cette date -- ce script ne devine pas si/quand le
deploiement reel a eu lieu, il donne les chiffres bruts sur plusieurs
fenetres pour que l'operateur/Claude puisse reconcilier avec la realite
du terrain.

Ce script calcule, sur plusieurs fenetres (11 derniers jours calendaires,
depuis le commit du 04/11, et depuis l'ancienne fenetre de mesure du
28/10) :
  1/ Leads reels par jour et par outil (leads_convertis)
  2/ Funnel de progression du mini-formulaire (interactions_contenu :
     form_vu -> form_etape -> form_abandon) et taux d'abandon
  3/ Sessions GA4 par silo pour calculer un taux de conversion par silo

LECTURE SEULE.
"""
from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"


def leads_par_jour(client):
    print("=" * 90)
    print("1/ Leads reels par jour et par outil (20 derniers jours)")
    print("=" * 90)
    df = client.query(f"""
        SELECT DATE(timestamp) AS jour, tool, COUNT(*) AS nb
        FROM `{PROJECT_ID}.{DATASET_ID}.leads_convertis`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 20 DAY)
        GROUP BY jour, tool
        ORDER BY jour, tool
    """).to_dataframe()
    if df.empty:
        print("  Aucun lead sur la fenetre.")
        return df
    pivot = df.pivot_table(index="jour", columns="tool", values="nb", fill_value=0, aggfunc="sum")
    print(pivot.to_string())
    print(f"\n  Total par outil sur la fenetre :")
    print(df.groupby("tool")["nb"].sum().sort_values(ascending=False).to_string())
    return df


def resume_fenetres(df_leads):
    print()
    print("=" * 90)
    print("Resume par fenetre")
    print("=" * 90)
    import pandas as pd
    aujourdhui = pd.Timestamp.now(tz="UTC").date()
    fenetres = {
        "11 derniers jours calendaires": aujourdhui - pd.Timedelta(days=11),
        "Depuis le commit 'un seul ecran' (04/11)": pd.Timestamp("2026-11-04").date(),
        "Depuis l'ancienne fenetre de mesure (28/10)": pd.Timestamp("2026-10-28").date(),
    }
    if df_leads.empty:
        for nom in fenetres:
            print(f"  {nom} : 0 lead")
        return
    df_leads["jour"] = df_leads["jour"].astype(str).apply(lambda x: pd.Timestamp(x).date())
    for nom, date_debut in fenetres.items():
        sous_ensemble = df_leads[df_leads["jour"] >= date_debut]
        nb_jours = (aujourdhui - date_debut).days or 1
        total = sous_ensemble["nb"].sum()
        print(f"  {nom} ({date_debut} -> aujourd'hui, {nb_jours}j) : {total} lead(s) -> {total/nb_jours:.2f}/jour -> projection {total/nb_jours*30:.0f}/mois")


def funnel_formulaire(client):
    print()
    print("=" * 90)
    print("2/ Funnel du mini-formulaire inline (interactions_contenu, 20 derniers jours)")
    print("=" * 90)
    df = client.query(f"""
        SELECT DATE(timestamp) AS jour, type_evenement, cible, etape, COUNT(*) AS nb
        FROM `{PROJECT_ID}.{DATASET_ID}.interactions_contenu`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 20 DAY)
          AND type_evenement IN ('form_vu', 'form_etape', 'form_abandon')
        GROUP BY jour, type_evenement, cible, etape
        ORDER BY jour
    """).to_dataframe()
    if df.empty:
        print("  Aucun evenement de funnel sur la fenetre (interactions_contenu vide ou pas encore deployee).")
        return
    print(df.to_string(index=False))

    print("\n  Totaux par type d'evenement / variante (cible) / etape :")
    print(df.groupby(["type_evenement", "cible", "etape"])["nb"].sum().to_string())

    print("\n  Taux d'abandon global (form_abandon / (form_etape ou idx>0)) :")
    nb_vu = df[df["type_evenement"] == "form_vu"]["nb"].sum()
    nb_termine = df[(df["type_evenement"] == "form_etape") & (df["etape"] == "termine")]["nb"].sum()
    nb_abandon = df[df["type_evenement"] == "form_abandon"]["nb"].sum()
    print(f"    form_vu total      : {nb_vu}")
    print(f"    form_etape=termine : {nb_termine}")
    print(f"    form_abandon       : {nb_abandon}")
    if nb_vu:
        print(f"    taux de completion (termine/vu) : {nb_termine/nb_vu*100:.1f}%")


def sessions_ga4_silo(client):
    print()
    print("=" * 90)
    print("3/ Sessions GA4 par silo (approx. via pages vues, 11 derniers jours)")
    print("=" * 90)
    try:
        df = client.query(f"""
            SELECT silo, SUM(sessions) AS sessions, SUM(page_views) AS vues, SUM(conversions) AS conversions_ga4
            FROM `{PROJECT_ID}.01_raw.ga4_pages`
            WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 11 DAY)
            GROUP BY silo
            ORDER BY sessions DESC
        """).to_dataframe()
        print(df.to_string(index=False))
    except Exception as e:
        print(f"  ⚠️ Erreur (schema possiblement different) : {e}")


def main():
    client = bigquery.Client(project=PROJECT_ID)
    df_leads = leads_par_jour(client)
    resume_fenetres(df_leads)
    funnel_formulaire(client)
    sessions_ga4_silo(client)


if __name__ == "__main__":
    main()
