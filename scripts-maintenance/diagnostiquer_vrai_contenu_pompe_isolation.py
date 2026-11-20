"""
CME — Diagnostic (20/11/2026) : re-verification de l'"effet secondaire"
documente le 16/11/2026 (section "Fallback anciennete a 100%..." de
CLAUDE.md), qui affirmait que la vue 03_final.seo_opportunities classe
"Aide pompe a chaleur"/"Aide isolation" PAR ERREUR sous le silo
"2. Renovation Energetique" (slugs "pompe-a-chaleur"/"isolation", sans
prefixe "aide-").

En relisant le code le 20/11 (cme-gsc-to-bq.gs, parseUrl()/SILO_MAP/
detectSilo() -- la seule fonction qui derive silo/sous_silo depuis l'URL,
AVANT l'ecriture dans 01_raw.gsc_queries ; fix_seo_opportunities_postid.sh
ne fait que RELABELLER l'orthographe du silo deja present, jamais une
re-derivation depuis l'URL), le mapping semble en realite correct pour
une URL /aide-energetique/aide-pompe-a-chaleur/... (parts[0]="aide-
energetique" -> SILO_MAP -> Aide Energetique ; parts[1]="aide-pompe-a-
chaleur", PAS "pompe-a-chaleur"). Hypothese alternative testee ici : les
19/4 lignes GSC "pompe-a-chaleur"/"isolation" sous Renovation Energetique
reperees le 16/11 sont en realite le sous-silo PRE-EXISTANT et DISTINCT
"Renovation Energetique > Pompe a chaleur"/"> Isolation" (present dans
QUOTAS_SOUS_SILO historique, cf. CLAUDE.md), pas une mauvaise
classification du contenu "Aide pompe a chaleur"/"Aide isolation" -- une
simple coincidence de nommage, pas un bug de routage.

Lecture seule. Croise 3 sources : (1) les pages reelles derriere les
lignes gsc_queries "pompe-a-chaleur"/"isolation" sous Renovation
Energetique, (2) l'existence de lignes gsc_queries pour des pages
contenant litteralement "aide-pompe-a-chaleur"/"aide-isolation", (3) les
URLs reelles publiees sous ces deux sous-silos (historique_publications)
et si elles apparaissent dans gsc_queries, sous quel silo/sous_silo.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print(f"{'='*100}")
    print("1. PAGES REELLES derriere silo~Renovation + sous_silo brut IN ('pompe-a-chaleur','isolation')")
    print(f"   (30 jours, table brute 01_raw.gsc_queries -- avant tout relabel de la vue)")
    print(f"{'='*100}")
    df1 = client.query(f"""
        SELECT page, silo AS silo_brut, sous_silo AS sous_silo_brut,
               COUNT(*) AS nb_requetes, SUM(impressions) AS impressions
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
          AND LOWER(silo) LIKE '%renovation%'
          AND sous_silo IN ('pompe-a-chaleur', 'isolation')
        GROUP BY page, silo_brut, sous_silo_brut
        ORDER BY impressions DESC
        LIMIT 25
    """).to_dataframe()
    with __import__("pandas").option_context("display.max_colwidth", 90, "display.width", 160):
        print(df1.to_string(index=False) if not df1.empty else "  (aucune ligne)")

    print(f"\n{'='*100}")
    print("2. Existe-t-il des lignes gsc_queries pour des pages contenant 'aide-pompe-a-chaleur' ou 'aide-isolation' ?")
    print(f"   (90 jours, peu importe le silo/sous_silo attribue)")
    print(f"{'='*100}")
    df2 = client.query(f"""
        SELECT page, silo AS silo_brut, sous_silo AS sous_silo_brut,
               COUNT(*) AS nb_requetes, SUM(impressions) AS impressions
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
          AND (LOWER(page) LIKE '%aide-pompe-a-chaleur%' OR LOWER(page) LIKE '%aide-isolation%')
        GROUP BY page, silo_brut, sous_silo_brut
        ORDER BY impressions DESC
        LIMIT 25
    """).to_dataframe()
    with __import__("pandas").option_context("display.max_colwidth", 90, "display.width", 160):
        print(df2.to_string(index=False) if not df2.empty else "  (aucune ligne -- zero donnee GSC pour ces slugs)")

    print(f"\n{'='*100}")
    print("3. URLs REELLEMENT PUBLIEES sous 'Aide pompe a chaleur' / 'Aide isolation' (historique_publications)")
    print(f"   -- et, pour chacune, apparait-elle dans gsc_queries (90j), sous quel silo/sous_silo ?")
    print(f"{'='*100}")
    df3 = client.query(f"""
        SELECT silo, sous_silo_strategique, url_wp, date_publication
        FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
        WHERE sous_silo_strategique IN ('Aide pompe à chaleur', 'Aide isolation')
        ORDER BY date_publication DESC
    """).to_dataframe()
    print(f"  {len(df3)} article(s) publie(s) au total sous ces 2 sous-silos.")
    if df3.empty:
        print("  (rien a croiser)")
    else:
        with __import__("pandas").option_context("display.max_colwidth", 90, "display.width", 160):
            print(df3.to_string(index=False))
        print("\n  Croisement avec gsc_queries (match par suffixe d'URL, 90 jours) :")
        for _, row in df3.iterrows():
            url = row['url_wp']
            df_match = client.query(f"""
                SELECT DISTINCT silo, sous_silo
                FROM `{PROJECT_ID}.01_raw.gsc_queries`
                WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
                  AND page LIKE '%{url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]}%'
            """).to_dataframe()
            if df_match.empty:
                print(f"    - {url} -> AUCUNE ligne GSC (pas assez de donnees/trop recent)")
            else:
                for _, m in df_match.iterrows():
                    print(f"    - {url} -> silo={m['silo']!r} sous_silo={m['sous_silo']!r}")


if __name__ == "__main__":
    main()
