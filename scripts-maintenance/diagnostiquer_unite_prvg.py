"""
CME -- Diagnostic lecture seule : l'endpoint /api/tarif-gaz-repere a renvoye
un prix hors plage plausible (0.20626 EUR/kWh) lors du test du 16/11/2026
(scripts-maintenance/tester_endpoints_tarifs_comparateur.py). Avant tout
redeploiement Cloud Run, on verifie si la conversion /1000 (supposant que
'valeur' est stockee en EUR/MWh) est la bonne hypothese -- en lisant la
colonne 'unite' reelle + l'historique de l'indicateur PRVG_moyen_TTC, et en
comparant au TRVE (electricite, dont la conversion est differente -- /12
pour la part fixe, pas de /1000 pour la part variable) pour voir si les deux
indicateurs utilisent des conventions d'unite coherentes entre eux.
"""
from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"
TABLE = f"{PROJECT_ID}.04_pipeline_seo.indicateurs_reglementaires"


def section(t):
    print(f"\n{'='*100}\n{t}\n{'='*100}")


def main():
    client = bigquery.Client(project=PROJECT_ID)

    section("1. Colonne 'unite' + 'domaine' + 'source_url' pour PRVG_moyen_TTC (derniere valeur)")
    df = client.query(f"""
        SELECT indicateur, domaine, sous_categorie, valeur, unite, date_debut_validite, date_verification, source_url
        FROM `{TABLE}`
        WHERE indicateur = 'PRVG_moyen_TTC'
        ORDER BY date_verification DESC
        LIMIT 1
    """).to_dataframe()
    print(df.to_string(index=False))

    section("2. Historique complet de PRVG_moyen_TTC (toutes les valeurs connues, triees par date_debut_validite)")
    df2 = client.query(f"""
        SELECT valeur, unite, date_debut_validite, date_verification, run_id
        FROM `{TABLE}`
        WHERE indicateur = 'PRVG_moyen_TTC'
        ORDER BY date_debut_validite
    """).to_dataframe()
    print(df2.to_string(index=False))

    section("3. Pour comparaison -- colonne 'unite' des 2 indicateurs TRVE (electricite, deja domaine connu, conversion /12 uniquement sur la part fixe)")
    df3 = client.query(f"""
        SELECT indicateur, sous_categorie, valeur, unite, date_debut_validite
        FROM `{TABLE}`
        WHERE indicateur IN ('TRVE_part_variable_TTC', 'TRVE_part_fixe_TTC')
          AND sous_categorie = '6 kVA'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY indicateur ORDER BY date_verification DESC) = 1
    """).to_dataframe()
    print(df3.to_string(index=False))

    section("4. Interpretation")
    if not df.empty:
        row = df.iloc[0]
        unite = str(row.get("unite", "")).strip()
        valeur = float(row["valeur"])
        print(f"  unite stockee pour PRVG_moyen_TTC : '{unite}'")
        print(f"  valeur brute : {valeur}")
        print(f"  Hypothese server.py (valeur en EUR/MWh) -> valeur/1000 = {round(valeur/1000, 5)} EUR/kWh")
        print(f"  Si en realite la valeur est deja en centimes EUR/kWh ou une autre unite,")
        print(f"  la conversion /1000 de tracking-api/server.py serait fausse.")
        if "mwh" in unite.lower():
            print("  -> 'unite' confirme EUR/MWh : la conversion /1000 est correcte, 0.206 EUR/kWh TTC est le vrai prix repere actuel (plausible si en forte hausse recente -- cf. historique ci-dessus).")
        elif unite:
            print(f"  -> ATTENTION : 'unite' ({unite}) ne mentionne pas explicitement MWh -- a examiner avant de faire confiance a la conversion /1000.")
        else:
            print("  -> 'unite' est vide/non renseignee -- aucune confirmation possible depuis la donnee elle-meme, se fier a l'historique/tendance pour juger de la plausibilite.")


if __name__ == "__main__":
    main()
