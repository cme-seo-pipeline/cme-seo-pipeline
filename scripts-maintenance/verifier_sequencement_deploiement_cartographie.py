"""
CME — Verifie si le "bug soumis=0" de l'entonnoir est un vrai bug de
tracking ou un probleme de SEQUENCEMENT DE DEPLOIEMENT (meme famille que
l'incident "Lionel" du 22/10 -- voir CLAUDE.md : une soumission reelle
survenue avant que le code/la configuration necessaire ne soit deployee
en prod n'a, structurellement, aucune chance d'etre tracee).

Declenche par le resultat de diagnostiquer_bug_soumis_entonnoir.py
(01/11/2026) : sur 3 leads reels inline depuis le 28/10, les 2 du 28/10
matin (10:55-10:56 UTC) n'ont AUCUNE ligne interactions_contenu (meme pas
'form_vu'), alors que le 3e, du 01/11 15h19 UTC, a les 4 etapes
parfaitement tracees. Hypothese a tester : la cartographie des clics
(table + code de tracking dans cme-cta-progressifs.php) a ete DEPLOYEE en
cPanel plus tard dans la journee du 28/10, apres ces 2 leads -- pas un
bug de tracking qui persisterait aujourd'hui.

Verifie : le tout premier timestamp d'un evenement interactions_contenu
jamais enregistre (toutes sources), pour situer precisement le moment ou
le tracking a commence a produire des donnees reelles en prod.

LECTURE SEULE -- aucune ecriture.
Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 verifier_sequencement_deploiement_cartographie.py
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("📥 Tout premier evenement jamais enregistre dans interactions_contenu...")
    df_premier = client.query(f"""
        SELECT MIN(timestamp) AS premier_evenement
        FROM `{PROJECT_ID}.04_pipeline_seo.interactions_contenu`
    """).to_dataframe()
    premier = df_premier.iloc[0]["premier_evenement"]
    print(f"   -> {premier}")

    print("\n📥 Volume d'evenements par heure le 28/10/2026 (toutes sources)...")
    df_28 = client.query(f"""
        SELECT TIMESTAMP_TRUNC(timestamp, HOUR) AS heure, type_evenement, COUNT(*) AS n
        FROM `{PROJECT_ID}.04_pipeline_seo.interactions_contenu`
        WHERE DATE(timestamp) = '2026-10-28'
        GROUP BY heure, type_evenement
        ORDER BY heure
    """).to_dataframe()
    if df_28.empty:
        print("   ⚠️ Aucun evenement du tout le 28/10 -- le tracking n'a peut-etre commence que le 29/10 ou plus tard.")
    else:
        print(df_28.to_string(index=False))

    print("\n📥 Rappel des 2 leads du 28/10 sans trace (diagnostiquer_bug_soumis_entonnoir.py) :")
    print("   2026-10-28 10:55:43 UTC -- post_id=5274")
    print("   2026-10-28 10:56:30 UTC -- post_id=5274")

    if not df_28.empty:
        premiere_heure_28 = df_28["heure"].min()
        print(f"\n📊 Premier evenement trace le 28/10 : {premiere_heure_28} "
              f"-- {'APRES' if premiere_heure_28 > __import__('pandas').Timestamp('2026-10-28 10:56:30', tz='UTC') else 'AVANT'} "
              f"les 2 leads sans trace.")


if __name__ == "__main__":
    main()
