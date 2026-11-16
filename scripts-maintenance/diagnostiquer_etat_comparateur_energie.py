"""
CME — Diagnostic complet de l'état actuel du simulateur comparateur-energie
(gaz & électricité), demandé par l'opérateur le 16/11/2026 avant d'étudier
une intégration de ce simulateur dans les articles du silo Gaz/Électricité.

Couvre : état de la page live (poids, rendu), fraîcheur des prix, leads
réels capturés, clics réels sur les offres, trafic GSC/GA4 réel sur la
page. Lecture seule, aucune écriture.
"""
import re
import sys
import time
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    sys.exit("❌ requests manquant")

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"
PAGE_URL = "https://www.comprendre-mon-energie.fr/comparateur-energie-electricite-gaz/"
PAGE_SLUG_LIKE = "%comparateur-energie%"


def section(titre):
    print(f"\n{'='*100}\n{titre}\n{'='*100}")


def diag_page_live():
    section("1. ÉTAT DE LA PAGE LIVE (poids réel, rendu, cache)")
    try:
        t0 = time.time()
        r = requests.get(PAGE_URL, timeout=20, headers={"User-Agent": "Mozilla/5.0 (diagnostic CME)"})
        elapsed = time.time() - t0
    except Exception as e:
        print(f"  ❌ Page inaccessible : {e}")
        return
    poids_ko = len(r.content) / 1024
    print(f"  URL testée       : {PAGE_URL}")
    print(f"  Statut HTTP      : {r.status_code}")
    print(f"  Temps de réponse : {elapsed:.2f}s")
    print(f"  Poids total HTML : {poids_ko:.0f} Ko")
    print(f"  Cache LiteSpeed  : {r.headers.get('x-litespeed-cache', 'en-tete absent')}")

    html = r.text
    rendu_ok = bool(re.search(r"Mon profil|offer-card|lmodal-ov", html))
    print(f"  Shortcode bien rendu (marqueurs trouvés) : {'oui' if rendu_ok else 'NON — a verifier manuellement'}")

    # Poids du bloc shortcode lui-même (style + script injectés inline)
    m = re.search(r"<style>.*?lmodal-sub:disabled.*?</style>", html, re.DOTALL)
    style_ko = len(m.group(0)) / 1024 if m else None
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.DOTALL)
    script_cmp = max(scripts, key=len) if scripts else ""
    script_ko = len(script_cmp) / 1024
    print(f"  Poids du <style> inline du comparateur   : {style_ko:.0f} Ko" if style_ko else "  Poids du <style> inline : non isolé automatiquement")
    print(f"  Poids du plus gros <script> inline       : {script_ko:.0f} Ko (sur {len(scripts)} balises <script> trouvées sur la page)")
    print(f"  -> Pour comparaison, poids TOTAL de la page : {poids_ko:.0f} Ko")

    # Date affichée des tarifs (S.edfDate dans le JS, ou texte "Tarifs indicatifs au")
    m2 = re.search(r"Tarifs indicatifs au ([\d/]+)", html)
    m3 = re.search(r"edfDate:'([\d/]+)'", html)
    print(f"  Date de tarifs affichée dans le HTML/JS live : "
          f"{m2.group(1) if m2 else (m3.group(1) if m3 else 'aucune trouvée sur la page rendue')}")


def diag_fraicheur_code_source():
    section("2. FRAÎCHEUR DES PRIX — CODE SOURCE DU REPO (comparateur-energie.php)")
    try:
        with open("wordpress-plugins/comparateur-energie/comparateur-energie.php", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print("  ❌ fichier introuvable depuis ce répertoire (lancer depuis la racine du repo)")
        return
    m = re.search(r"edfDate:'([\d/]+)'", content)
    print(f"  Date de tarifs codée en dur dans le repo (S.edfDate) : {m.group(1) if m else 'non trouvée'}")
    offres = re.findall(r"id:'([^']+)',logo:'[^']*',nom:'([^']+)',offre:'[^']*',type:'[^']*',px:([\d.]+),abo:([\d.]+)", content)
    print(f"  Nombre d'offres codées en dur (ELEC+GAZ) trouvées : {len(offres)}")
    if offres:
        print(f"  Exemple : {offres[0][1]} — {offres[0][2]} EUR/kWh, abo {offres[0][3]} EUR/mois (en dur dans le JS, aucune source dynamique)")

    # Vérifie si le script de mise à jour trimestrielle est encore compatible
    try:
        with open("maj-trimestrielle/update_prix.py", encoding="utf-8") as f:
            script_maj = f.read()
        pattern_attendu = "prix_kwh:" in script_maj and "abo_mois:" in script_maj
        champs_reels_ok = "px:" in content and "abo:" in content
        print(f"\n  Script maj-trimestrielle/update_prix.py attend les champs : prix_kwh:/abo_mois:")
        print(f"  Champs réellement utilisés dans le PHP actuel            : px:/abo:")
        if pattern_attendu and champs_reels_ok:
            print(f"  ⚠️ INCOMPATIBILITÉ CONFIRMÉE : le script de mise à jour trimestrielle ne retrouvera AUCUNE "
                  f"offre avec les noms de champs actuels (px:/abo:) — son regex cherche prix_kwh:/abo_mois:. "
                  f"Ce script est cassé depuis un refactor du fichier PHP, silencieusement (il afficherait "
                  f"'ERREUR : aucune offre trouvee').")
    except FileNotFoundError:
        print("  (maj-trimestrielle/update_prix.py introuvable depuis ce répertoire)")


def diag_leads_et_clics(client_bq):
    section("3. LEADS RÉELS CAPTURÉS (leads_convertis, tool='comparateur-energie')")
    df = client_bq.query(f"""
        SELECT COUNT(*) AS n, MIN(timestamp) AS premier, MAX(timestamp) AS dernier
        FROM `{PROJECT_ID}.{DATASET_ID}.leads_convertis`
        WHERE tool = 'comparateur-energie'
    """).to_dataframe()
    row = df.iloc[0]
    print(f"  Total leads convertis depuis le début du suivi : {int(row['n'])}")
    print(f"  Premier lead : {row['premier']}")
    print(f"  Dernier lead : {row['dernier']}")

    if int(row["n"]) > 0:
        df2 = client_bq.query(f"""
            SELECT timestamp, prenom, source_page, details
            FROM `{PROJECT_ID}.{DATASET_ID}.leads_convertis`
            WHERE tool = 'comparateur-energie'
            ORDER BY timestamp DESC
            LIMIT 5
        """).to_dataframe()
        print("\n  5 derniers leads :")
        for _, r in df2.iterrows():
            print(f"    {r['timestamp']} — {r['prenom']} — {r['source_page']}")

    section("4. CLICS RÉELS SUR LES OFFRES (historique_clics_comparateur)")
    try:
        df3 = client_bq.query(f"""
            SELECT COUNT(*) AS n, MIN(timestamp) AS premier, MAX(timestamp) AS dernier
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_clics_comparateur`
        """).to_dataframe()
        row3 = df3.iloc[0]
        print(f"  Total clics enregistrés : {int(row3['n'])}")
        print(f"  Premier clic : {row3['premier']}")
        print(f"  Dernier clic : {row3['dernier']}")
        if int(row3["n"]) > 0:
            df4 = client_bq.query(f"""
                SELECT offre_nom, COUNT(*) AS n
                FROM `{PROJECT_ID}.{DATASET_ID}.historique_clics_comparateur`
                GROUP BY offre_nom ORDER BY n DESC LIMIT 10
            """).to_dataframe()
            print("\n  Répartition par offre cliquée :")
            for _, r in df4.iterrows():
                print(f"    {r['offre_nom']} : {int(r['n'])}")
    except Exception as e:
        print(f"  ❌ Erreur table historique_clics_comparateur : {e}")


def diag_trafic_reel(client_bq):
    section("5. TRAFIC RÉEL SUR LA PAGE (GSC — 01_raw.gsc_queries, 90 jours)")
    try:
        df = client_bq.query(f"""
            SELECT page, COUNT(DISTINCT query) AS nb_requetes,
                   SUM(clics) AS clics, SUM(impressions) AS impressions,
                   ROUND(AVG(position), 1) AS position_moy,
                   MIN(date) AS premiere_date, MAX(date) AS derniere_date
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE page LIKE '{PAGE_SLUG_LIKE}'
              AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
            GROUP BY page
            ORDER BY impressions DESC
        """).to_dataframe()
        if df.empty:
            print("  Aucune ligne GSC trouvée pour cette page sur 90 jours.")
        else:
            for _, r in df.iterrows():
                print(f"  {r['page']}")
                print(f"    requêtes distinctes={int(r['nb_requetes'])} clics={int(r['clics'])} "
                      f"impressions={int(r['impressions'])} position_moy={r['position_moy']} "
                      f"(du {r['premiere_date']} au {r['derniere_date']})")

        df_top = client_bq.query(f"""
            SELECT query, page, SUM(clics) AS clics, SUM(impressions) AS impressions, ROUND(AVG(position),1) AS position
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE page LIKE '{PAGE_SLUG_LIKE}'
              AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
            GROUP BY query, page
            ORDER BY impressions DESC
            LIMIT 10
        """).to_dataframe()
        if not df_top.empty:
            print("\n  Top requêtes (90j) :")
            for _, r in df_top.iterrows():
                print(f"    '{r['query']}' -> {r['page']} (clics={int(r['clics'])}, impr={int(r['impressions'])}, pos={r['position']})")
    except Exception as e:
        print(f"  ❌ Erreur GSC : {e}")

    section("6. TRAFIC RÉEL SUR LA PAGE (GA4 — 01_raw.ga4_pages, 90 jours)")
    try:
        df5 = client_bq.query(f"""
            SELECT page_path, SUM(sessions) AS sessions, SUM(vues) AS vues,
                   MIN(date) AS premiere_date, MAX(date) AS derniere_date
            FROM `{PROJECT_ID}.01_raw.ga4_pages`
            WHERE page_path LIKE '{PAGE_SLUG_LIKE}'
              AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
            GROUP BY page_path
            ORDER BY sessions DESC
        """).to_dataframe()
        if df5.empty:
            print("  Aucune ligne GA4 trouvée pour cette page sur 90 jours.")
        else:
            for _, r in df5.iterrows():
                print(f"  {r['page_path']} : sessions={int(r['sessions'])} vues={int(r['vues'])} "
                      f"(du {r['premiere_date']} au {r['derniere_date']})")
    except Exception as e:
        print(f"  ❌ Erreur GA4 (colonnes possiblement différentes) : {e}")


def main():
    diag_page_live()
    diag_fraicheur_code_source()
    client_bq = bigquery.Client(project=PROJECT_ID)
    diag_leads_et_clics(client_bq)
    diag_trafic_reel(client_bq)
    section("FIN DU DIAGNOSTIC")


if __name__ == "__main__":
    main()
