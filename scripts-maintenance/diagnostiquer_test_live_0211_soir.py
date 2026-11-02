"""
CME — Diagnostic express : l'operateur a fait un test reel sur
/contactez-un-expert/ le 02/11 vers 23h41 Paris (22h41 UTC) avec le
telephone de test 0695410020, juste apres avoir deploye le mu-plugin
cme-tracking-conversion.php mis a jour -- rien n'est apparu dans le
Sheet "Leads Formulaire Article".

Objectif : determiner si le probleme est EN AMONT (la soumission n'a
jamais atteint leads_convertis -- donc le JS/deploiement est en cause)
ou EN AVAL (la ligne existe en base mais le relais Sheets a echoue --
donc l'Apps Script/son URL est en cause). Regarde large (tous tools,
fenetre de 2h) pour ne pas manquer le lead si le telephone/tool ne
correspond pas exactement a ce qui etait attendu.

LECTURE SEULE.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("📥 Toutes les lignes leads_convertis des 2 dernieres heures (tous tools)...\n")
    df = client.query(f"""
        SELECT timestamp, tool, prenom, nom, telephone, email, code_postal,
               source_page, source_post_id, details
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
        ORDER BY timestamp DESC
    """).to_dataframe()

    if df.empty:
        print("⚠️ AUCUNE ligne dans leads_convertis sur les 2 dernieres heures, tous tools confondus.")
        print("   -> le test n'a pas du tout atteint BigQuery. Cause probable : deploiement cPanel")
        print("      pas pris effet (cache navigateur/LiteSpeed sur la page testee), ou erreur JS.")
        return

    print(f"✅ {len(df)} ligne(s) trouvee(s) sur les 2 dernieres heures :\n")
    print("=" * 110)
    for _, row in df.iterrows():
        print(f"\n  {row['timestamp']}  tool={row['tool']!r}")
        print(f"    prenom={row['prenom']!r}  telephone={row['telephone']!r}  email={row['email']!r}  code_postal={row['code_postal']!r}")
        print(f"    source_page={row['source_page']!r}")
        print(f"    details={row['details']!r}")

    print("\n" + "=" * 110)
    print("Recherche specifique du telephone de test 0695410020 / 695410020...")
    match = df[df["telephone"].astype(str).str.contains("695410020", na=False)]
    if match.empty:
        print("⚠️ Aucune ligne ne contient ce telephone -- soit le test n'a pas atteint BigQuery,")
        print("   soit le telephone n'a pas ete capture (voir tool='contact-expert-formulaire' ci-dessus,")
        print("   le champ pourrait rester vide si la capture par classe WPForms n'a pas fonctionne).")
    else:
        print(f"✅ {len(match)} ligne(s) avec ce telephone -- la soumission A BIEN atteint BigQuery.")
        print("   Si rien n'apparait dans le Sheet malgre ca, le probleme est dans le relais Apps Script")
        print("   (cme_relayer_log_lead() -> wp_remote_get -> CME_APPS_SCRIPT_LEADS_INLINE_URL), pas en amont.")


if __name__ == "__main__":
    main()
