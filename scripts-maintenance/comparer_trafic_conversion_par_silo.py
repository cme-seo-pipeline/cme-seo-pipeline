"""
CME — Comparatif trafic organique vs conversion (leads), par silo.

Demande operateur du 29/10/2026 : verifier l'hypothese que le silo "Aides"
(aide-energetique) capte beaucoup de trafic organique mais convertit peu
(0 lead sur octobre, cf. doc projet "objectif-100-leads-mois.md"), avant
de decider -- APRES la fenetre de test en cours -- s'il faut construire
un tunnel de conversion dedie pour ce silo.

Sources :
  - 01_raw.ga4_pages (silo deja calcule a la synchronisation, colonne
    'silo', cf. apps-scripts/cme-ga4-to-bq.gs) -- trafic (sessions),
    mois en cours.
  - 04_pipeline_seo.leads_convertis -- leads reels du mois (apres le
    nettoyage du 29/10). Silo derive du champ details.silo pour le
    formulaire inline, ou du prefixe d'URL de source_page pour les
    appels telephone (avec table de repli pour les 2 anciennes pages
    simulateur hors-silo : comparateur-energie-electricite-gaz,
    devis-panneau-solaire).

LECTURE SEULE -- aucune ecriture.
Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 comparer_trafic_conversion_par_silo.py
"""
import json
import re
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"

# Pages legacy hors arborescence /silo/... (anciens simulateurs) -- silo
# attribue manuellement, pas deductible du prefixe d'URL.
SILO_PAGES_LEGACY = {
    "comparateur-energie-electricite-gaz": "electricite",
    "devis-panneau-solaire": "solaire",
}

PREFIXES_CONNUS = {"gaz", "electricite", "aide-energetique", "renovation-energetique", "solaire"}


def deduire_silo(tool, source_page, details_json):
    if tool == "contact-expert-inline" and details_json:
        try:
            d = json.loads(details_json)
            if d.get("silo"):
                return d["silo"]
        except Exception:
            pass
    if source_page:
        m = re.search(r"comprendre-mon-energie\.fr/([a-z-]+)/?", source_page)
        if m:
            segment = m.group(1)
            if segment in PREFIXES_CONNUS:
                return segment
            if segment in SILO_PAGES_LEGACY:
                return SILO_PAGES_LEGACY[segment]
    return "inconnu"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("📥 Leads du mois en cours (leads_convertis)...")
    df_leads = client.query(f"""
        SELECT tool, source_page, details
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE DATE(timestamp) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
    """).to_dataframe()

    leads_par_silo = {}
    for _, row in df_leads.iterrows():
        silo = deduire_silo(row["tool"], row["source_page"], row["details"])
        leads_par_silo[silo] = leads_par_silo.get(silo, 0) + 1

    print("📥 Trafic organique du mois en cours (01_raw.ga4_pages)...")
    df_trafic = client.query(f"""
        SELECT silo, SUM(sessions) AS sessions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE date >= DATE_TRUNC(CURRENT_DATE(), MONTH)
          AND silo IS NOT NULL AND silo != ''
        GROUP BY silo
        ORDER BY sessions DESC
    """).to_dataframe()

    print("\n" + "=" * 80)
    print("COMPARATIF TRAFIC vs CONVERSION PAR SILO -- mois en cours")
    print("=" * 80)
    print(f"{'Silo':<25}{'Sessions GA4':>15}{'Leads':>10}{'Taux conv.':>15}")
    print("-" * 80)
    tous_silos = set(df_trafic["silo"]) | set(leads_par_silo.keys())
    lignes = []
    for silo in tous_silos:
        sessions_row = df_trafic[df_trafic["silo"] == silo]["sessions"]
        sessions = int(sessions_row.iloc[0]) if not sessions_row.empty else 0
        leads = leads_par_silo.get(silo, 0)
        taux = (leads / sessions * 100) if sessions else 0
        lignes.append((silo, sessions, leads, taux))
    lignes.sort(key=lambda x: x[1], reverse=True)
    for silo, sessions, leads, taux in lignes:
        print(f"{silo:<25}{sessions:>15}{leads:>10}{taux:>14.3f}%")


if __name__ == "__main__":
    main()
