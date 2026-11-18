"""
CME -- Diagnostic (lecture seule) : pourquoi le run du 18/11/2026 a publie
18 articles au lieu de 20 -- les 2 sous-silos manquants ('1. Gaz | Compteur
gaz' et '5. Electricite | Compteur') ont ete selectionnes (20 sujets
confirmes dans le log : "TOTAL : 20 sujets selectionnes sur 20 sous-silos
cibles") et scrapes, mais aucun brief n'a ete genere pour eux -- aucune
ligne d'erreur dans le log (generer_tous_briefs() fait un simple
`if df_silo_clean.empty: continue`, sans aucun log dans ce cas precis).

Hypothese a confirmer : les sources retournees par SearchApi pour la
requete "compteur Linky fonctionnement consommation optimisation"
(generee pour les 2 sous-silos -- meme requete, bien que l'un soit sur le
GAZ) etaient en grande partie des fichiers non-HTML (PDF, uploads) ou
bloquees (403/timeout), laissant 0 mot de contenu exploitable
(volume_mots) une fois filtre.

Verifie directement dans analyse_concurrents (table BigQuery alimentee par
exporter_bigquery(), contient une ligne par URL scrapee avec son
volume_mots reel) pour le run du jour.

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

    print("📥 Lignes analyse_concurrents du 18/11/2026 pour les 2 sous-silos sans brief...\n")
    df = client.query(f"""
        SELECT run_id, silo, sous_silo, url, volume_mots
        FROM `{PROJECT_ID}.04_pipeline_seo.analyse_concurrents`
        WHERE date_run = '2026-11-18'
          AND ((silo = '1. Gaz' AND sous_silo = 'Compteur gaz')
               OR (silo = '5. Électricité' AND sous_silo = 'Compteur'))
        ORDER BY silo, sous_silo, url
    """).to_dataframe()

    if df.empty:
        print("  ⚠️ AUCUNE ligne du tout pour ces 2 sous-silos aujourd'hui -- meme le scraping n'a produit aucune ligne exportable (pas seulement volume_mots=0).")
    else:
        print(f"  {len(df)} ligne(s) trouvee(s) :\n")
        for _, row in df.iterrows():
            print(f"  run_id={row['run_id']}  {row['silo']} | {row['sous_silo']}  volume_mots={row['volume_mots']}  url={row['url'][:80]}")
        print(f"\n  Volume_mots max sur ces lignes : {df['volume_mots'].max()}")
        print(f"  Nombre de lignes avec volume_mots > 0 : {(df['volume_mots'] > 0).sum()} / {len(df)}")

    print("\n" + "=" * 100)
    print("📥 Pour comparaison -- meme chose sur un sous-silo qui A eu un brief aujourd'hui (Bouteilles)...\n")
    df2 = client.query(f"""
        SELECT url, volume_mots
        FROM `{PROJECT_ID}.04_pipeline_seo.analyse_concurrents`
        WHERE date_run = '2026-11-18' AND silo = '1. Gaz' AND sous_silo = 'Bouteilles'
        ORDER BY url
    """).to_dataframe()
    for _, row in df2.iterrows():
        print(f"  volume_mots={row['volume_mots']}  url={row['url'][:80]}")


if __name__ == "__main__":
    main()
