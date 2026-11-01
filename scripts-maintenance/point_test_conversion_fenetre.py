"""
CME — Point de mesure sur la fenetre de test conversion (7-10 jours a
partir du 28/10/2026, cf. doc projet "objectif-100-leads-mois.md"),
demande operateur du 01/11/2026.

Pourquoi un nouveau script plutot que de relancer
comparer_trafic_conversion_par_silo.py : ce dernier filtre sur
DATE_TRUNC(CURRENT_DATE(), MONTH) ("mois en cours") -- correct le 29/10
(tout octobre), mais FAUX a partir du 01/11 : la fenetre de test
(28/10-05/11 ou 07/11) chevauche maintenant la frontiere de mois, et
"mois en cours" bascule sur novembre seul (quasi aucune donnee encore).
Execute une fois le 01/11 pour verifier : le run a bien retourne une
seule ligne quasi vide (aide-energetique, 0 session, 1 lead) au lieu du
vrai comparatif attendu -- confirme le probleme plutot que de le
supposer.

Ce script reprend exactement la meme logique (sources, deduction de
silo) mais filtre sur une fenetre de dates explicite (--depuis, defaut
2026-10-28) plutot que sur le mois calendaire, pour rester valide quel
que soit le jour d'execution pendant la fenetre de test.

LECTURE SEULE -- aucune ecriture.
Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 point_test_conversion_fenetre.py [--depuis=2026-10-28]
"""
import json
import re
import sys
from datetime import date, datetime

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"

SILO_PAGES_LEGACY = {
    "comparateur-energie-electricite-gaz": "electricite",
    "devis-panneau-solaire": "solaire",
}
PREFIXES_CONNUS = {"gaz", "electricite", "aide-energetique", "renovation-energetique", "solaire"}


def normaliser_silo_ga4(silo_ga4):
    sans_numero = re.sub(r"^\d+\.\s*", "", silo_ga4 or "")
    return sans_numero.strip().lower().replace(" ", "-")


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
    depuis = "2026-10-28"
    for arg in sys.argv[1:]:
        if arg.startswith("--depuis="):
            depuis = arg.split("=", 1)[1]

    depuis_date = datetime.strptime(depuis, "%Y-%m-%d").date()
    aujourd_hui = date.today()
    jours_ecoules = (aujourd_hui - depuis_date).days + 1
    print(f"📅 Fenetre de test : depuis le {depuis} -- jour {jours_ecoules} (sur 7 a 10 jours prevus, "
          f"decision au 5-7/11/2026)")

    client = bigquery.Client(project=PROJECT_ID)

    print(f"\n📥 Leads reels depuis le {depuis} (leads_convertis)...")
    df_leads = client.query(f"""
        SELECT tool, source_page, details, timestamp
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE DATE(timestamp) >= '{depuis}'
    """).to_dataframe()

    leads_par_silo = {}
    leads_par_outil = {}
    for _, row in df_leads.iterrows():
        silo = deduire_silo(row["tool"], row["source_page"], row["details"])
        leads_par_silo[silo] = leads_par_silo.get(silo, 0) + 1
        leads_par_outil[row["tool"]] = leads_par_outil.get(row["tool"], 0) + 1

    print(f"\n📥 Trafic organique depuis le {depuis} (01_raw.ga4_pages)...")
    df_trafic_brut = client.query(f"""
        SELECT silo, SUM(sessions) AS sessions
        FROM `{PROJECT_ID}.01_raw.ga4_pages`
        WHERE date >= '{depuis}'
          AND silo IS NOT NULL AND silo != ''
        GROUP BY silo
    """).to_dataframe()
    sessions_par_silo = {}
    for _, row in df_trafic_brut.iterrows():
        silo_norm = normaliser_silo_ga4(row["silo"])
        sessions_par_silo[silo_norm] = sessions_par_silo.get(silo_norm, 0) + int(row["sessions"])

    print("\n" + "=" * 80)
    print(f"COMPARATIF TRAFIC vs CONVERSION PAR SILO -- depuis le {depuis}")
    print("=" * 80)
    print(f"{'Silo':<25}{'Sessions GA4':>15}{'Leads':>10}{'Taux conv.':>15}")
    print("-" * 80)
    tous_silos = set(sessions_par_silo.keys()) | set(leads_par_silo.keys())
    lignes = []
    for silo in tous_silos:
        sessions = sessions_par_silo.get(silo, 0)
        leads = leads_par_silo.get(silo, 0)
        taux = (leads / sessions * 100) if sessions else 0
        lignes.append((silo, sessions, leads, taux))
    lignes.sort(key=lambda x: x[1], reverse=True)
    for silo, sessions, leads, taux in lignes:
        print(f"{silo:<25}{sessions:>15}{leads:>10}{taux:>14.3f}%")

    print(f"\n📊 Total leads sur la fenetre : {sum(leads_par_outil.values())}")
    for outil, n in sorted(leads_par_outil.items(), key=lambda x: -x[1]):
        print(f"   - {outil:<30} : {n}")

    objectif_mensuel = 100
    rythme_jour = sum(leads_par_outil.values()) / jours_ecoules if jours_ecoules else 0
    projection_30j = rythme_jour * 30
    print(f"\n📈 Rythme observe : {rythme_jour:.2f} lead(s)/jour sur {jours_ecoules} jour(s) "
          f"-- projection a 30 jours : {projection_30j:.0f} (objectif : {objectif_mensuel})")


if __name__ == "__main__":
    main()
