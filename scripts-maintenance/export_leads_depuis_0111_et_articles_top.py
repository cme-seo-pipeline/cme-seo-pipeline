"""
CME — Export des leads depuis le 01/11/2026 (colonnes alignees sur l'onglet
Sheets "Leads Formulaire Article") + classement des articles qui convertissent
le mieux.

Demande operateur du 11/11/2026, en 2 volets :
1. "extraire les leads convertis depuis le 01 dans un tableau pour comparer
   avec ce que j'ai sur le fichier sheets" -- on reproduit ICI exactement
   les memes colonnes/memes valeurs que celles ecrites par
   apps-scripts/cme-formulaire-article-leads.gs::ecrireSheet() (source de
   verite du mapping : Date & Heure, Prenom, Telephone, Email, Code Postal,
   Silo (details.silo), Position dans l'article (details.position), URL de
   l'article (source_page), CTA (tool)) -- pour que l'operateur puisse
   comparer ligne a ligne avec son Sheet sans ecart de colonnes/format.
   NB : le Sheet ne recoit que 4 des 5 "tool" (contact-expert-inline,
   appel-expert-inline, appel-header-formulaire, contact-expert-formulaire
   -- filtre cme_relayer_log_lead()) ; appel-telephone (clic tel: generique,
   hors formulaire) n'y arrive jamais -- affiche ici separement pour ne pas
   fausser la comparaison.
2. "creuser sur les articles qui convertissent le mieux" -- classement des
   articles (source_page/source_post_id) par nombre de leads sur la meme
   fenetre, avec le silo associe.

LECTURE SEULE.
"""
import json
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"
TABLE_LEADS = f"{PROJECT_ID}.{DATASET_ID}.leads_convertis"

DEPUIS = "2026-11-01"

# Memes 4 outils que le filtre reel de cme_relayer_log_lead() (wordpress-mu-plugins/
# cme-tracking-conversion.php) -- seuls ceux-la partent vers le Sheet.
OUTILS_RELAYES_SHEET = (
    "contact-expert-inline", "appel-expert-inline",
    "appel-header-formulaire", "contact-expert-formulaire",
)


def extraire_details(details_raw):
    try:
        d = json.loads(details_raw) if details_raw else {}
        if isinstance(d, str):  # parfois double-encode (meme piege que classer_position_formulaire_leads.py)
            d = json.loads(d)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def tableau_comparaison_sheet(client):
    print("=" * 110)
    print(f"1/ Leads depuis le {DEPUIS} -- colonnes alignees sur l'onglet Sheets 'Leads Formulaire Article'")
    print("=" * 110)
    df = client.query(f"""
        SELECT timestamp, tool, prenom, telephone, email, code_postal, source_page, details
        FROM `{TABLE_LEADS}`
        WHERE DATE(timestamp) >= '{DEPUIS}'
        ORDER BY timestamp ASC
    """).to_dataframe()

    if df.empty:
        print(f"  Aucun lead depuis le {DEPUIS}.")
        return df

    relayes = df[df["tool"].isin(OUTILS_RELAYES_SHEET)].copy()
    hors_sheet = df[~df["tool"].isin(OUTILS_RELAYES_SHEET)].copy()

    print(f"\n  {len(relayes)} lead(s) qui DOIVENT apparaitre dans le Sheet (meme filtre que le relais reel) :")
    print("-" * 110)
    header = f"  {'Date & Heure (UTC)':<20} | {'Prenom':<20} | {'Telephone':<13} | {'Email':<22} | {'CP':<6} | {'Silo':<22} | {'Position':<10} | {'CTA':<26}"
    print(header)
    print("  " + "-" * 108)
    for _, row in relayes.iterrows():
        d = extraire_details(row["details"])
        ts = str(row["timestamp"])[:19]
        prenom = (row["prenom"] or "")[:20]
        tel = (row["telephone"] or "")[:13]
        email = (row["email"] or "")[:22]
        cp = (row["code_postal"] or "")[:6]
        silo = str(d.get("silo", "") or "")[:22]
        position = str(d.get("position", "") or "")[:10]
        cta = (row["tool"] or "")[:26]
        print(f"  {ts:<20} | {prenom:<20} | {tel:<13} | {email:<22} | {cp:<6} | {silo:<22} | {position:<10} | {cta:<26}")
        url = row["source_page"] or ""
        if url:
            print(f"      URL : {url}")

    if not hors_sheet.empty:
        print(f"\n  + {len(hors_sheet)} lead(s) HORS Sheet par design (outil non relaye, ex. appel-telephone) :")
        print("-" * 110)
        for _, row in hors_sheet.iterrows():
            ts = str(row["timestamp"])[:19]
            print(f"  {ts}  tool={row['tool']}  tel={row['telephone'] or '(vide)'}  page={row['source_page'] or '(vide)'}")

    print(f"\n  Total toutes lignes depuis le {DEPUIS} : {len(df)} ({len(relayes)} dans le Sheet + {len(hors_sheet)} hors Sheet)")
    return df


def classement_articles(df):
    print()
    print("=" * 110)
    print("2/ Articles qui convertissent le mieux (meme fenetre)")
    print("=" * 110)
    if df.empty:
        print("  Aucune donnee.")
        return

    avec_page = df[df["source_page"].notna() & (df["source_page"] != "")].copy()
    if avec_page.empty:
        print("  Aucun lead avec source_page renseignee sur la fenetre.")
        return

    avec_page["silo"] = avec_page["details"].apply(lambda x: extraire_details(x).get("silo", ""))

    agg = (
        avec_page.groupby("source_page")
        .agg(nb_leads=("source_page", "size"), silo=("silo", lambda s: next((x for x in s if x), "")))
        .sort_values("nb_leads", ascending=False)
    )
    print(f"\n  {len(agg)} article(s) distinct(s) avec au moins 1 lead sur la fenetre :\n")
    for url, row in agg.iterrows():
        print(f"  {row['nb_leads']:>2} lead(s)  |  silo={row['silo'] or '(vide)':<22}  |  {url}")

    print(f"\n  Repartition par silo (leads avec source_page, tous outils) :")
    print(avec_page.groupby("silo").size().sort_values(ascending=False).to_string())


def main():
    client = bigquery.Client(project=PROJECT_ID)
    df = tableau_comparaison_sheet(client)
    classement_articles(df)


if __name__ == "__main__":
    main()
