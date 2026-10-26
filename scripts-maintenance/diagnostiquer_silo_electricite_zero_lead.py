"""
CME — Diagnostic cible : pages du silo Electricite a fort trafic mais 0 lead.

Suite directe de analyser_potentiel_silos.py (26/10/2026) : le silo
Electricite capte le 2e plus gros volume d'impressions SEO du site (2983
sur 30j, position moyenne correcte 41.9) mais affiche 0 lead sur 421
sessions GA4/30j -- le pire taux de conversion des 5 silos, sur un
echantillon assez large pour etre un vrai signal (contrairement aux
taux positifs bases sur 2 leads ailleurs). Avant de proposer quoi que ce
soit sur ce silo, on identifie LES PAGES precises concernees (pas juste le
chiffre agrege), pour voir si le probleme est concentre (quelques pages a
fort trafic qui n'ont jamais converti) ou diffus (beaucoup de pages a
trafic modeste, aucune ne convertit).

Reutilise la vue tunnel_conversion_unifie (sessions/leads par page, voir
tunnel_conversion_unifie.sh) -- le probleme de sous-comptage SEO identifie
dans analyser_potentiel_silos.py concernait specifiquement la jointure GSC
(gsc_agg), pas les jointures GA4 (ga4_agg) ni leads (leads_final), donc
sessions/leads par page restent fiables ici.

LECTURE SEULE. Necessite GOOGLE_APPLICATION_CREDENTIALS dans l'environnement.
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
VUE = f"{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie"


def run(client, titre, sql):
    print("\n" + "=" * 78)
    print(titre)
    print("=" * 78)
    try:
        df = client.query(sql).to_dataframe()
        if df.empty:
            print("   (0 ligne)")
        else:
            print(df.to_string(index=False))
        return df
    except Exception as e:
        print(f"   ❌ Erreur SQL : {e}")
        return None


def main():
    client = bigquery.Client(project=PROJECT_ID)

    run(client, "1. Pages Electricite -- fort trafic (>=5 sessions/30j), 0 lead -- triees par trafic", f"""
        SELECT url, sessions, bounce_rate_pct, rage_click_sessions, scroll_depth_moyen
        FROM `{VUE}`
        WHERE REGEXP_CONTAINS(url, r'(?:https?://)?(?:www\\.)?[^/]+/electricite/')
          AND sessions >= 5 AND nb_leads = 0
        ORDER BY sessions DESC
        LIMIT 20
    """)

    run(client, "2. Comparaison -- pages Electricite qui ONT converti (s'il y en a, pour comprendre la difference)", f"""
        SELECT url, sessions, nb_leads, bounce_rate_pct, rage_click_sessions, scroll_depth_moyen
        FROM `{VUE}`
        WHERE REGEXP_CONTAINS(url, r'(?:https?://)?(?:www\\.)?[^/]+/electricite/')
          AND nb_leads > 0
        ORDER BY sessions DESC
    """)

    run(client, "3. Totaux Electricite -- concentre ou diffus ? (nb pages concernees, repartition sessions)", f"""
        SELECT
          COUNT(*) AS nb_pages_avec_trafic,
          SUM(sessions) AS sessions_totales,
          COUNTIF(sessions >= 20) AS nb_pages_grosses_20plus,
          SUM(IF(sessions >= 20, sessions, 0)) AS sessions_sur_grosses_pages
        FROM `{VUE}`
        WHERE REGEXP_CONTAINS(url, r'(?:https?://)?(?:www\\.)?[^/]+/electricite/')
          AND sessions > 0
    """)

    run(client, "4. Bounce rate moyen Electricite vs autres silos -- indice de desalignement intention de recherche", f"""
        SELECT
          CASE WHEN REGEXP_CONTAINS(url, r'(?:https?://)?(?:www\\.)?[^/]+/electricite/') THEN 'Electricite'
               ELSE 'Autres silos' END AS groupe,
          ROUND(AVG(bounce_rate_pct), 1) AS bounce_rate_moyen_pct,
          ROUND(AVG(scroll_depth_moyen), 1) AS scroll_moyen,
          SUM(rage_click_sessions) AS rage_clicks_totaux,
          COUNT(*) AS nb_pages
        FROM `{VUE}`
        WHERE sessions > 0
        GROUP BY groupe
    """)


if __name__ == "__main__":
    main()
