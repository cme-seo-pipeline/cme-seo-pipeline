"""
CME — Diagnostic du bug "soumis=0" dans l'entonnoir interactions_contenu
(signale le 29/10, toujours constate le 01/11 -- voir CLAUDE.md et
objectif-100-leads-mois.md, section "Point intermediaire").

Objectif explicite de l'operateur (01/11/2026) : creuser la VRAIE cause
avant de conclure quoi que ce soit, en se mefiant d'une fausse alerte
(precedent du 26/10 : une conclusion erronee avait ete tiree avant de
verifier le run_id reel). Ici, l'equivalent du "run_id" est : est-ce que
chaque lead reel (`leads_convertis`, tool='contact-expert-inline') a
VRAIMENT un evenement 'termine' manquant dans `interactions_contenu`, ou
est-ce qu'on compare par erreur les mauvaises lignes (silo mal rapproche,
fenetre de temps trop stricte, etc.) ?

Methode : pour chaque lead reel inline depuis le 28/10 (date de debut de
la fenetre de test, chaine de tracking confirmee fonctionnelle), on
cherche dans interactions_contenu, PAR source_post_id (cle fiable commune
aux deux tables) et dans une fenetre de +/- 10 minutes autour du
timestamp du lead, s'il existe une ligne :
  - type_evenement='form_vu'                              (formulaire vu)
  - type_evenement='form_etape' AND etape='0'              (etape 1 affichee)
  - type_evenement='form_etape' AND etape='1'              (etape tel atteinte)
  - type_evenement='form_etape' AND etape='termine'        (soumission tracee)
Rapporte le resultat ligne par ligne -- pas d'agregat qui pourrait
masquer un rapprochement errone.

LECTURE SEULE -- aucune ecriture.
Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 diagnostiquer_bug_soumis_entonnoir.py [--depuis=2026-10-28]
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    depuis = "2026-10-28"
    for arg in sys.argv[1:]:
        if arg.startswith("--depuis="):
            depuis = arg.split("=", 1)[1]

    client = bigquery.Client(project=PROJECT_ID)

    print(f"📥 Leads inline reels depuis le {depuis} (leads_convertis)...")
    df_leads = client.query(f"""
        SELECT timestamp, source_post_id, source_page, details
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE tool = 'contact-expert-inline'
          AND DATE(timestamp) >= '{depuis}'
        ORDER BY timestamp
    """).to_dataframe()

    if df_leads.empty:
        print("⚠️ Aucun lead inline sur cette fenetre -- rien a diagnostiquer.")
        return

    print(f"   -> {len(df_leads)} lead(s) trouve(s)\n")

    print("=" * 100)
    print("RAPPROCHEMENT lead reel <-> interactions_contenu (par source_post_id, fenetre +/-10 min)")
    print("=" * 100)

    n_vu = n_etape0 = n_etape1 = n_termine = 0

    for _, lead in df_leads.iterrows():
        ts = lead["timestamp"]
        post_id = lead["source_post_id"] or ""
        print(f"\n🔹 Lead {ts} -- source_post_id={post_id} -- {lead['source_page']}")
        print(f"   details={lead['details']}")

        if not post_id:
            print("   ⚠️ source_post_id vide sur ce lead -- rapprochement impossible")
            continue

        df_match = client.query(f"""
            SELECT timestamp, type_evenement, etape, position_contenu, session_id
            FROM `{PROJECT_ID}.04_pipeline_seo.interactions_contenu`
            WHERE source_post_id = '{post_id}'
              AND timestamp BETWEEN TIMESTAMP_SUB(TIMESTAMP('{ts}'), INTERVAL 10 MINUTE)
                               AND TIMESTAMP_ADD(TIMESTAMP('{ts}'), INTERVAL 10 MINUTE)
              AND type_evenement IN ('form_vu', 'form_etape')
            ORDER BY timestamp
        """).to_dataframe()

        if df_match.empty:
            print("   ❌ AUCUNE ligne interactions_contenu trouvee pour ce post_id dans la fenetre "
                  "(ni vu, ni etape 0, ni etape 1, ni termine)")
            continue

        a_vu = (df_match["type_evenement"] == "form_vu").any()
        a_etape0 = ((df_match["type_evenement"] == "form_etape") & (df_match["etape"] == "0")).any()
        a_etape1 = ((df_match["type_evenement"] == "form_etape") & (df_match["etape"] == "1")).any()
        a_termine = ((df_match["type_evenement"] == "form_etape") & (df_match["etape"] == "termine")).any()
        n_vu += a_vu; n_etape0 += a_etape0; n_etape1 += a_etape1; n_termine += a_termine

        print(f"   {len(df_match)} ligne(s) trouvee(s) -- vu={a_vu} etape0={a_etape0} "
              f"etape1={a_etape1} termine={a_termine}")
        for _, r in df_match.iterrows():
            print(f"      {r['timestamp']}  {r['type_evenement']:<12} etape={r['etape']!r:<10} "
                  f"session_id={r['session_id']}")

    n = len(df_leads)
    print("\n" + "=" * 100)
    print(f"SYNTHESE sur {n} lead(s) reel(s) inline :")
    print(f"  form_vu retrouve      : {n_vu}/{n}")
    print(f"  etape '0' retrouvee   : {n_etape0}/{n}")
    print(f"  etape '1' retrouvee   : {n_etape1}/{n}")
    print(f"  etape 'termine' retrouvee : {n_termine}/{n}")
    print("=" * 100)
    if n_termine < n:
        print("\n⚠️ Confirme : au moins un lead reel n'a PAS de trace 'termine' correspondante "
              "dans interactions_contenu -- pas une fausse alerte de rapprochement (fait par "
              "source_post_id + fenetre temporelle large de 10 min), le probleme est reel.")
    else:
        print("\n✅ Tous les leads reels ont bien un evenement 'termine' correspondant -- "
              "le bug signale le 29/10 serait donc une fausse alerte (probablement un probleme "
              "de GROUP BY/silo dans le script d'entonnoir, pas une perte reelle de donnees).")


if __name__ == "__main__":
    main()
