"""
CME — Test (lecture seule) de la logique SQL des deux nouveaux endpoints
/api/tarif-edf et /api/tarif-gaz-repere (tracking-api/server.py, ajoutes le
16/11/2026 pour brancher le comparateur-energie sur indicateurs_reglementaires
en remplacement du stub /api/tarifs mort).

Rejoue EXACTEMENT les memes requetes SQL que les deux fonctions Flask, sans
passer par Cloud Run (pas encore redeploye) -- confirme que la logique
renvoie des valeurs coherentes AVANT le redeploiement operateur, demande
explicitement avant tout redeploiement vu que ce comparateur va devenir la
capture de leads principale sur 5 silos.
"""
from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"
INDICATEURS_PROJECT = f"{PROJECT_ID}.04_pipeline_seo.indicateurs_reglementaires"


def section(t):
    print(f"\n{'='*100}\n{t}\n{'='*100}")


def main():
    client = bigquery.Client(project=PROJECT_ID)

    section("1. /api/tarif-edf — requete exacte de tarif_edf()")
    df = client.query(f"""
        SELECT indicateur, valeur, date_debut_validite
        FROM `{INDICATEURS_PROJECT}`
        WHERE indicateur IN ('TRVE_part_variable_TTC', 'TRVE_part_fixe_TTC')
          AND sous_categorie = '6 kVA'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY indicateur ORDER BY date_verification DESC) = 1
    """).to_dataframe()
    print(df.to_string(index=False))
    valeurs = {row["indicateur"]: row for _, row in df.iterrows()}
    ok_edf = "TRVE_part_variable_TTC" in valeurs and "TRVE_part_fixe_TTC" in valeurs
    if ok_edf:
        variable = valeurs["TRVE_part_variable_TTC"]
        fixe = valeurs["TRVE_part_fixe_TTC"]
        prix_kwh = round(float(variable["valeur"]), 5)
        abo_mois = round(float(fixe["valeur"]) / 12, 2)
        date_validite = variable["date_debut_validite"].strftime("%d/%m/%Y")
        print(f"\n  -> Reponse simulee : prix_kwh_ttc={prix_kwh}, abo_mois_ttc={abo_mois}, date_debut_validite={date_validite}")
        # Garde-fous de plausibilite (pas une assertion stricte -- juste un signal si une valeur
        # BigQuery aberrante passerait silencieusement dans le comparateur, ex. erreur d'unite)
        if not (0.10 <= prix_kwh <= 0.40):
            print(f"  ⚠️ prix_kwh_ttc hors plage plausible (0.10-0.40 €/kWh) : {prix_kwh}")
        if not (5 <= abo_mois <= 25):
            print(f"  ⚠️ abo_mois_ttc hors plage plausible (5-25 €/mois) : {abo_mois}")
    else:
        print("  ❌ ECHEC : un ou les deux indicateurs TRVE introuvables -- l'endpoint renverrait 404.")

    section("2. /api/tarif-gaz-repere — requete exacte de tarif_gaz_repere()")
    df2 = client.query(f"""
        SELECT valeur, date_debut_validite
        FROM `{INDICATEURS_PROJECT}`
        WHERE indicateur = 'PRVG_moyen_TTC'
        ORDER BY date_verification DESC
        LIMIT 1
    """).to_dataframe()
    print(df2.to_string(index=False))
    ok_gaz = not df2.empty
    if ok_gaz:
        row = df2.iloc[0]
        prix_kwh_gaz = round(float(row["valeur"]) / 1000, 5)
        date_validite_gaz = row["date_debut_validite"].strftime("%d/%m/%Y")
        print(f"\n  -> Reponse simulee : prix_kwh_ttc={prix_kwh_gaz}, date_debut_validite={date_validite_gaz}")
        # Plage relevee le 16/11/2026 (diagnostiquer_unite_prvg.py) : 'unite' confirme
        # explicitement '€/MWh' pour PRVG_moyen_TTC -- la conversion /1000 est correcte.
        # L'indicateur est en hausse continue (172.05 -> 182.88 -> 194.90 -> 206.26 €/MWh
        # sur sept./oct./nov./dec. 2026, environ +6-7%/mois) : la borne haute initiale de
        # 0.20 €/kWh etait trop basse pour une tendance reelle, pas le signe d'un bug de
        # conversion. Relevee a 0.30 pour absorber la poursuite plausible de cette hausse
        # sans redevenir un faux positif a chaque run mensuel.
        if not (0.05 <= prix_kwh_gaz <= 0.30):
            print(f"  ⚠️ prix_kwh_ttc gaz hors plage plausible (0.05-0.30 €/kWh) : {prix_kwh_gaz}")
    else:
        print("  ❌ ECHEC : indicateur PRVG_moyen_TTC introuvable -- l'endpoint renverrait 404.")

    section("3. Comparaison avec les valeurs actuellement codees en dur dans le plugin (avant branchement live)")
    print("  EDF (plugin, S.edfPrix/S.edfAbo par defaut) : 0.19398 €/kWh, 11.80 €/mois")
    print("  Gaz (plugin, GAZ 'edf-gaz'/S.gazRef/S.gazAbo) : 0.12766 €/kWh, 6.49 €/mois (abo)")
    if ok_edf:
        ecart_prix = (prix_kwh - 0.19398) / 0.19398 * 100
        ecart_abo = (abo_mois - 11.80) / 11.80 * 100
        print(f"  -> Ecart EDF détecté par le branchement live : prix {ecart_prix:+.1f}% / abo {ecart_abo:+.1f}%")
    if ok_gaz:
        ecart_gaz = (prix_kwh_gaz - 0.12766) / 0.12766 * 100
        print(f"  -> Ecart gaz détecté par le branchement live : prix {ecart_gaz:+.1f}%")

    section("RESULTAT")
    if ok_edf and ok_gaz:
        print("✅ Les deux endpoints renverraient des valeurs exploitables -- pret pour redeploiement Cloud Run.")
    else:
        print("❌ Au moins un endpoint echouerait (404) -- NE PAS redeployer sans corriger la source de donnees d'abord.")


if __name__ == "__main__":
    main()
