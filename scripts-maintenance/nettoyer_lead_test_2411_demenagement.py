"""
CME — Nettoyage d'un lead de test unique (24/11/2026), suite au test de bout
en bout du formulaire contact-expert-inline etendu a 6 champs (schema
"2 -> 2 -> 2", voir CLAUDE.md section du 24/11/2026). Confirme fonctionnel
par l'operateur (lead visible cote BigQuery ET cote Sheets, colonnes
Type de logement / Statut occupation bien remplies) -- meme precaution que
les nettoyages de leads de test precedents de ce projet
(nettoyer_leads_test_popup_header.py le 01/11, nettoyer_leads_test_0211_0302.py
le 02-03/11) : dry-run par defaut, --apply pour executer reellement.

Lead cible (identifie par l'operateur, ligne Sheets fournie le 24/11/2026) :
  tool = contact-expert-inline
  telephone de test = ...695410020 (meme numero de test deja utilise et
    nettoye le 01/11 -- piege deja documente : le vrai zero de tete peut
    etre absent de la copie Sheets (colonne interpretee comme nombre), donc
    le filtre ci-dessous matche sur le SUFFIXE du numero, pas sur l'egalite
    stricte, pour couvrir les deux ecritures possibles ("695410020" et
    "0695410020"))
  article = /electricite/demenagement/electricite-demenagement-checklist-avant-apres/
  horodatage Sheets = 24/11/2026 17:37:35 -- CONFIRME par diagnostic
    (diagnostiquer_lead_test_2411.py, 24/11/2026) que ce timestamp est deja
    en UTC (2026-11-24 17:37:33.421583+00:00 cote BigQuery, pas une
    conversion Paris->UTC comme suppose dans une premiere version de ce
    script) -- telephone confirme stocke avec le zero de tete ('0695410020',
    pas de piege supplementaire sur ce point).

AUCUNE adresse email n'est utilisee comme filtre ici (et aucune n'est
ecrite dans ce fichier) -- principe absolu du projet (ne jamais coder en
dur une donnee personnelle identifiante dans le repo), le filtre
tool + telephone + article + fenetre temporelle suffit amplement a isoler
ce lead precis sans ambiguite.

USAGE :
  python3 nettoyer_lead_test_2411_demenagement.py           # dry-run
  python3 nettoyer_lead_test_2411_demenagement.py --apply   # supprime reellement
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE_REF = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"

TOOL_CIBLE = "contact-expert-inline"
TELEPHONE_SUFFIXE = "695410020"
URL_ARTICLE = "https://www.comprendre-mon-energie.fr/electricite/demenagement/electricite-demenagement-checklist-avant-apres/"
FENETRE_DEBUT = "2026-11-24 17:30:00"
FENETRE_FIN = "2026-11-24 17:45:00"


def main():
    apply_reel = "--apply" in sys.argv
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
    SELECT timestamp, tool, telephone, source_post_id, source_page, details
    FROM `{TABLE_REF}`
    WHERE tool = @tool_cible
      AND ENDS_WITH(telephone, @tel_suffixe)
      AND source_page = @url_article
      AND timestamp BETWEEN TIMESTAMP(@debut) AND TIMESTAMP(@fin)
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("tool_cible", "STRING", TOOL_CIBLE),
        bigquery.ScalarQueryParameter("tel_suffixe", "STRING", TELEPHONE_SUFFIXE),
        bigquery.ScalarQueryParameter("url_article", "STRING", URL_ARTICLE),
        bigquery.ScalarQueryParameter("debut", "STRING", FENETRE_DEBUT),
        bigquery.ScalarQueryParameter("fin", "STRING", FENETRE_FIN),
    ])
    lignes = list(client.query(query, job_config=job_config).result())

    print(f"{len(lignes)} ligne(s) correspondante(s) trouvee(s) :")
    for l in lignes:
        print(f"  - {l.timestamp} | tool={l.tool} | tel=...{str(l.telephone)[-6:]} | "
              f"post_id={l.source_post_id} | page={l.source_page} | details={l.details}")

    if not lignes:
        print("Rien a supprimer.")
        return

    if len(lignes) != 1:
        print("⚠️ Plus d'une ligne trouvee -- verification manuelle requise avant --apply, "
              "aucune suppression effectuee par securite.")
        return

    if not apply_reel:
        print("\nDry-run : aucune suppression effectuee. Relancer avec --apply pour supprimer reellement.")
        return

    delete_query = f"""
    DELETE FROM `{TABLE_REF}`
    WHERE tool = @tool_cible
      AND ENDS_WITH(telephone, @tel_suffixe)
      AND source_page = @url_article
      AND timestamp BETWEEN TIMESTAMP(@debut) AND TIMESTAMP(@fin)
    """
    job = client.query(delete_query, job_config=job_config)
    job.result()
    print(f"✅ {job.num_dml_affected_rows} ligne(s) supprimee(s).")


if __name__ == "__main__":
    main()
