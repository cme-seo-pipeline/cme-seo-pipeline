"""
CME — Lecture seule : verifie s'il y a eu des leads reels (soumissions
completes) sur le nouveau popup "avant d'appeler" du bouton tel: du header,
depuis son deploiement/validation en prod le 01/11/2026 (voir CLAUDE.md,
section "Popup avant d'appeler sur le bouton du header").

IMPORTANT -- limite de mesure a rappeler dans le rapport :
le popup (`creerPopupAppel()` dans cme-tracking-conversion.php) ne journalise
AUCUN evenement dans `interactions_contenu` (pas de 'popup_vu'/'popup_abandon'
equivalent aux 'form_vu'/'form_abandon' du mini-formulaire des articles) --
une ligne `leads_convertis` (tool='appel-header-formulaire') n'est ecrite
QUE si le visiteur termine le formulaire (nom + telephone + RGPD valides) et
clique sur "Appeler". Ce script ne peut donc repondre qu'a "combien de
personnes ont complete le formulaire et appele", pas "combien de personnes
ont clique sur le bouton du header" au sens large (clics bruts/abandons
invisibles avec l'instrumentation actuelle).

Exclut explicitement les 2 leads de test du 01/11 (tel. '0695410020',
post_id '13183', 17:42:58 UTC) deja nettoyes par
nettoyer_leads_test_popup_header.py -- gardes ici seulement par securite au
cas ou une autre ligne de test apparaitrait avec le meme telephone.

USAGE :
  python3 verifier_clics_popup_header.py
  python3 verifier_clics_popup_header.py --depuis=2026-11-01
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE_LEADS = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"

DEPUIS_DEFAUT = "2026-11-01"
TEL_TEST = "0695410020"


def parse_args():
    depuis = DEPUIS_DEFAUT
    for arg in sys.argv:
        if arg.startswith("--depuis="):
            depuis = arg.split("=", 1)[1]
    return depuis


def main():
    depuis = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print(f"📋 Leads 'appel-header-formulaire' depuis {depuis} "
          f"(hors telephone de test {TEL_TEST}) :\n")

    query = f"""
        SELECT timestamp, prenom, telephone, source_post_id, source_page
        FROM `{TABLE_LEADS}`
        WHERE tool = 'appel-header-formulaire'
          AND DATE(timestamp) >= '{depuis}'
          AND telephone != '{TEL_TEST}'
        ORDER BY timestamp
    """
    df = client.query(query).to_dataframe()

    if len(df) == 0:
        print("  (aucun lead reel trouve sur cette periode)")
    else:
        print(df.to_string(index=False))

    print(f"\nTotal : {len(df)} lead(s) reel(s) via le popup header depuis {depuis}.")

    # Contexte : pour comparaison, volume de l'ancien tracking generique
    # appel-telephone sur la meme periode (clics tel: hors header, ou clics
    # header AVANT le deploiement du popup).
    query_generique = f"""
        SELECT COUNT(*) AS n
        FROM `{TABLE_LEADS}`
        WHERE tool = 'appel-telephone'
          AND DATE(timestamp) >= '{depuis}'
    """
    n_generique = client.query(query_generique).to_dataframe()["n"].iloc[0]
    print(f"(Pour contexte : {n_generique} ligne(s) 'appel-telephone' "
          f"(tracking generique tel:, hors header) sur la meme periode.)")


if __name__ == "__main__":
    main()
