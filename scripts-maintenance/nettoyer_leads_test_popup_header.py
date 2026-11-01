"""
CME — Nettoyage (DRY-RUN par defaut, --apply pour ecrire) des 2 leads de
test crees par l'operateur le 01/11/2026 en validant le nouveau popup
"avant d'appeler" sur le bouton tel: du header (voir CLAUDE.md, section
"Popup avant d'appeler sur le bouton du header").

Les 2 lignes (visibles dans l'onglet Sheets "Leads Formulaire Article",
meme article, meme numero de test, a 30 secondes d'intervalle) :
  1. 2026-11-01 17:42:58.799548 UTC -- prenom='test', tool='appel-header-formulaire'
     -> test du nouveau popup header.
  2. 2026-11-01 17:43:29.833653 UTC -- prenom='oussama', tool='contact-expert-inline'
     -> test du mini-formulaire periodique existant sur le meme article,
        fait dans la foulee par l'operateur.

CORRECTIF (diagnostiquer_leads_0111.py) : le telephone stocke en base est
en realite '0695410020' (zero initial) -- Sheets l'affiche '695410020' car
la colonne Telephone y est interpretee comme un nombre, qui supprime le 0
de tete a l'affichage. Le filtre ci-dessous utilise la vraie valeur stockee.
Confirme par le meme diagnostic : il existe un 3e lead ce jour-la
('Walter Auguste', tel='0636458741', autre article) qui n'est PAS un test et
ne doit surtout pas etre touche -- le filtre telephone+source_post_id ci-
dessous l'exclut naturellement (numero et article differents).

Verifie aussi, a titre PUREMENT INFORMATIF (pas supprime automatiquement :
l'operateur n'a demande explicitement que les 2 lignes leads_convertis/Sheets),
si des lignes interactions_contenu existent pour le test 'oussama' (le test
'appel-header-formulaire' n'en genere aucune de son cote, voir
cme-tracking-conversion.php -- creerPopupAppel() n'appelle jamais
journaliserInteraction()).

USAGE :
  python3 nettoyer_leads_test_popup_header.py                  # dry-run
  python3 nettoyer_leads_test_popup_header.py --apply --attendu=2
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
TABLE_LEADS = f"{PROJECT_ID}.04_pipeline_seo.leads_convertis"
TABLE_INTERACTIONS = f"{PROJECT_ID}.04_pipeline_seo.interactions_contenu"
ARTICLE_URL = (
    "https://www.comprendre-mon-energie.fr/aide-energetique/cheque-energie/"
    "comment-utiliser-cheque-energie-fournisseurs-1101/"
)

FILTRE_LEADS = """
    telephone = '0695410020' AND source_post_id = '13183'
    AND tool IN ('appel-header-formulaire', 'contact-expert-inline')
"""


def parse_args():
    apply_ = "--apply" in sys.argv
    attendu = None
    for arg in sys.argv:
        if arg.startswith("--attendu="):
            attendu = int(arg.split("=", 1)[1])
    return apply_, attendu


def main():
    apply_, attendu = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print("📋 1) Lignes candidates dans leads_convertis :")
    df_leads = client.query(f"""
        SELECT timestamp, tool, prenom, telephone, source_post_id, source_page
        FROM `{TABLE_LEADS}` WHERE {FILTRE_LEADS}
        ORDER BY timestamp
    """).to_dataframe()
    print(df_leads.to_string(index=False) if len(df_leads) else "  (aucune)")
    nb_leads = len(df_leads)

    print("\n📋 2) A titre informatif uniquement -- lignes interactions_contenu "
          "sur le meme article, meme jour (PAS supprimees par ce script) :")
    df_int = client.query(f"""
        SELECT timestamp, type_evenement, etape, cible, position_contenu, session_id
        FROM `{TABLE_INTERACTIONS}`
        WHERE source_page = '{ARTICLE_URL}' AND DATE(timestamp) = '2026-11-01'
        ORDER BY timestamp
    """).to_dataframe()
    print(df_int.to_string(index=False) if len(df_int) else "  (aucune)")

    print(f"\nTotal : {nb_leads} ligne(s) leads_convertis candidates a la suppression.")

    if not apply_:
        print("\n(dry-run -- aucune ecriture. Relancer avec --apply --attendu=N pour "
              "supprimer les N lignes leads_convertis.)")
        return

    if attendu is None or nb_leads != attendu:
        sys.exit(f"❌ Garde-fou : {nb_leads} lignes trouvees, --attendu={attendu} -- "
                 f"abandon sans ecrire.")

    print(f"\n✍️ Suppression de {nb_leads} ligne(s) dans leads_convertis...")
    job = client.query(f"DELETE FROM `{TABLE_LEADS}` WHERE {FILTRE_LEADS}")
    job.result()
    print(f"✅ {job.num_dml_affected_rows} ligne(s) supprimee(s) dans leads_convertis.")


if __name__ == "__main__":
    main()
