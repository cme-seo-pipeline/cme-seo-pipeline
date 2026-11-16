"""
CME — Diagnostic 360 (lecture seule) du comparateur-energie, demande par
l'operateur le 16/11/2026, volet "calcul & API de mise a jour des prix".

Objectif : comparer les valeurs REELLEMENT figees dans le JS du
comparateur (EDF Tarif Bleu, Prix Repere CRE gaz) aux dernieres valeurs
reglementaires REELLES deja suivies par le pipeline (indicateurs_reglementaires,
sync quotidien, deja utilisees pour l'audit mensuel des articles) -- pour
quantifier l'ecart et confirmer si cette source peut etre reutilisee comme
flux de rafraichissement automatique pour les 2 offres de reference.

Verifie aussi le schema reel de leads_convertis.details (type de colonne)
pour savoir si les champs de profil (surface, chauffage, etc.) peuvent y
etre ajoutes sans migration.

Lecture seule -- aucune ecriture.
"""
import sys
from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"


def section(t):
    print(f"\n{'='*100}\n{t}\n{'='*100}")


def main():
    client = bigquery.Client(project=PROJECT_ID)

    section("1. DERNIERES VALEURS REGLEMENTAIRES REELLES (indicateurs_reglementaires)")
    df = client.query(f"""
        SELECT nom_indicateur, valeur, date_valeur, date_maj
        FROM `{PROJECT_ID}.{DATASET_ID}.indicateurs_reglementaires`
        WHERE nom_indicateur IN ('TRVE_part_variable_TTC','TRVE_part_fixe_TTC','PRVG_moyen_TTC')
        ORDER BY nom_indicateur
    """).to_dataframe()
    if df.empty:
        print("  Aucune ligne trouvee -- noms d'indicateurs a reverifier.")
    else:
        for _, r in df.iterrows():
            print(f"  {r['nom_indicateur']:28s} = {r['valeur']}  (valable au {r['date_valeur']}, synchronise le {r['date_maj']})")

    print("\n  Valeurs actuellement figees dans le JS du comparateur (code source repo, S.edfPrix/S.gazRef) :")
    print("    EDF Tarif Bleu (elec)      : px=0.19398 EUR/kWh, abo=11.80 EUR/mois, date affichee 01/02/2026")
    print("    EDF Prix Repere CRE (gaz)  : px=0.12766 EUR/kWh, abo=6.49 EUR/mois")
    print("  -> a comparer manuellement aux valeurs ci-dessus pour mesurer l'ecart reel.")

    section("2. SCHEMA REEL DE leads_convertis (colonne details)")
    try:
        table = client.get_table(f"{PROJECT_ID}.{DATASET_ID}.leads_convertis")
        for field in table.schema:
            if field.name in ("details", "tool", "source_page", "source_post_id"):
                print(f"  {field.name:18s} type={field.field_type:10s} mode={field.mode}")
    except Exception as e:
        print(f"  ❌ Erreur schema : {e}")

    section("3. LEADS_CONVERTIS — exemple reel d'un 'details' deja utilise par un autre outil")
    try:
        df2 = client.query(f"""
            SELECT tool, details
            FROM `{PROJECT_ID}.{DATASET_ID}.leads_convertis`
            WHERE details IS NOT NULL AND details != ''
            ORDER BY timestamp DESC
            LIMIT 3
        """).to_dataframe()
        for _, r in df2.iterrows():
            print(f"  tool={r['tool']} -> details={r['details']}")
    except Exception as e:
        print(f"  ❌ Erreur : {e}")

    section("FIN DU DIAGNOSTIC")


if __name__ == "__main__":
    main()
