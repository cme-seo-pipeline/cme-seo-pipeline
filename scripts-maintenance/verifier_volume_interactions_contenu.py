"""
CME — Verification ponctuelle (lecture seule) du volume reellement
accumule dans 04_pipeline_seo.interactions_contenu depuis son deploiement
le 26/10/2026, et de la repartition par silo -- demande operateur du
28/10 : l'instrumentation capture-t-elle bien le parcours PAR SILO, et
peut-on deja en extraire quelque chose.

La colonne 'silo' existe dans le schema (voir
creer_table_interactions_contenu.py) : derivee du premier segment de
l'URL cote clics-contenu (prefixeSilo() dans cme-tracking-conversion.php),
et du prefixe du formulaire (GAZ/ELEC/AIDES/SOLAIRE) cote progression
formulaire (cme-cta-progressifs.php). Ce script verifie juste le VOLUME
et verifie qu'elle est bien remplie en pratique (pas vide/NULL).

Script de diagnostic jetable, pas destine a rester durablement dans
scripts-maintenance/ (pas de --apply : lecture seule uniquement).

USAGE :
  python3 verifier_volume_interactions_contenu.py
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("📊 Volume total par jour et par type d'evenement")
    df1 = client.query(f"""
        SELECT DATE(timestamp) AS jour, type_evenement, COUNT(*) AS n
        FROM `{PROJECT_ID}.{DATASET_ID}.interactions_contenu`
        GROUP BY jour, type_evenement
        ORDER BY jour, type_evenement
    """).to_dataframe()
    if df1.empty:
        print("  ⚠️ Table vide -- aucune donnee accumulee pour l'instant.")
        return
    for _, r in df1.iterrows():
        print(f"  {r['jour']} | {r['type_evenement']:<15} : {int(r['n'])}")

    print("\n📊 Volume par silo (toutes dates, tous types d'evenement confondus)")
    df2 = client.query(f"""
        SELECT COALESCE(silo, '(vide)') AS silo, COUNT(*) AS n,
               COUNTIF(silo IS NULL OR silo = '') AS n_vide
        FROM `{PROJECT_ID}.{DATASET_ID}.interactions_contenu`
        GROUP BY silo
        ORDER BY n DESC
    """).to_dataframe()
    for _, r in df2.iterrows():
        print(f"  {r['silo']:<20} : {int(r['n'])} lignes")

    print("\n📊 Repartition clics (clic_contenu) par silo x cible (lien interne/externe/image)")
    df3 = client.query(f"""
        SELECT COALESCE(silo,'(vide)') AS silo, cible, COUNT(*) AS n
        FROM `{PROJECT_ID}.{DATASET_ID}.interactions_contenu`
        WHERE type_evenement = 'clic_contenu'
        GROUP BY silo, cible
        ORDER BY silo, n DESC
    """).to_dataframe()
    if df3.empty:
        print("  (aucun clic_contenu enregistre pour l'instant)")
    else:
        for _, r in df3.iterrows():
            print(f"  {r['silo']:<20} | {r['cible']:<15} : {int(r['n'])}")

    print("\n📊 Abandon du formulaire par silo (form_abandon)")
    df4 = client.query(f"""
        SELECT COALESCE(silo,'(vide)') AS silo, COUNT(*) AS n_abandon
        FROM `{PROJECT_ID}.{DATASET_ID}.interactions_contenu`
        WHERE type_evenement = 'form_abandon'
        GROUP BY silo
        ORDER BY n_abandon DESC
    """).to_dataframe()
    if df4.empty:
        print("  (aucun form_abandon enregistre pour l'instant)")
    else:
        for _, r in df4.iterrows():
            print(f"  {r['silo']:<20} : {int(r['n_abandon'])}")


if __name__ == "__main__":
    main()
