"""
CME -- Diagnostic (lecture seule) : existe-t-il un signal reel de demande
"professionnel/entreprise" pour comprendre-mon-energie.fr, et avons-nous
deja une quelconque categorie/contenu "pro" ?

Demande operateur (17/11/2026) : etudier l'idee d'ajouter des sous-silos
"pro" (ex: compteur-gaz-pro) ou tout un silo dedie aux professionnels --
AUCUNE decision ni action ici, uniquement reunir des faits pour raisonner
plutot que deviner.

Deux sources, toutes lecture seule :
1. 01_raw.gsc_queries -- requetes contenant un marqueur B2B
   (professionnel/pro/entreprise/societe/siret/commercant/b2b), avec
   impressions/clics/position -- montre si Google voit deja une demande
   meme sur des pages qui n'existent pas ou mal positionnees.
2. Categories WordPress (API REST /wp/v2/categories) -- recherche de toute
   categorie existante dont le nom/slug contient "pro"/"professionnel"
   (hors faux positifs comme "proteger"), pour eviter de dupliquer un
   sous-silo qui existerait deja.
"""
import os
import sys
import requests

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")
AUTH = (WP_USERNAME, WP_APP_PASSWORD)

MARQUEURS_PRO = [
    "professionnel", "professionnelle", "entreprise", "societe",
    "siret", "commercant", "commerçant", "b2b", "local commercial",
    "copropriete", "copropriété",
]


def main():
    client = bigquery.Client(project=PROJECT_ID)

    print("📥 1/ Requetes GSC (90 derniers jours) contenant un marqueur B2B...\n")
    conditions = " OR ".join([f"LOWER(query) LIKE '%{m}%'" for m in MARQUEURS_PRO])
    df = client.query(f"""
        SELECT query, silo, sous_silo,
               SUM(clics) AS clics_total,
               SUM(impressions) AS impressions_total,
               ROUND(AVG(position), 1) AS position_moyenne
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
          AND ({conditions})
        GROUP BY query, silo, sous_silo
        ORDER BY impressions_total DESC
        LIMIT 60
    """).to_dataframe()

    if df.empty:
        print("  ⚠️ Aucune requete B2B trouvee sur 90 jours (marqueurs : professionnel/entreprise/societe/siret/commercant/b2b/copropriete).")
    else:
        print(f"  {len(df)} requete(s) distincte(s) trouvee(s) :\n")
        total_impressions = 0
        total_clics = 0
        for _, row in df.iterrows():
            print(f"  '{row['query']}'  silo={row['silo']!r}  sous_silo={row['sous_silo']!r}  "
                  f"clics={row['clics_total']}  impressions={row['impressions_total']}  position={row['position_moyenne']}")
            total_impressions += row['impressions_total']
            total_clics += row['clics_total']
        print(f"\n  TOTAL (toutes requetes B2B confondues, 90j) : {total_clics} clics / {total_impressions} impressions")

    print("\n" + "=" * 100)
    print("📥 2/ Comparaison -- volume total du site sur la meme fenetre (pour situer l'ordre de grandeur)...\n")
    df_total = client.query(f"""
        SELECT SUM(clics) AS clics_total, SUM(impressions) AS impressions_total
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    """).to_dataframe()
    if not df_total.empty:
        print(f"  Site entier (90j) : {df_total.iloc[0]['clics_total']} clics / {df_total.iloc[0]['impressions_total']} impressions")

    print("\n" + "=" * 100)
    print("📥 3/ Categories WordPress existantes contenant 'pro' (hors faux positifs)...\n")
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories",
        auth=AUTH,
        params={"per_page": 100},
        timeout=30,
    )
    r.raise_for_status()
    cats = r.json()
    print(f"  {len(cats)} categorie(s) au total sur le site.\n")
    trouve = False
    for c in cats:
        nom = c["name"].lower()
        slug = c["slug"].lower()
        if ("pro" in nom or "pro" in slug) and "proteg" not in nom and "proteg" not in slug and "propane" not in nom and "propane" not in slug:
            trouve = True
            print(f"  id={c['id']}  name={c['name']!r}  slug={c['slug']!r}  parent={c['parent']}  count={c['count']}")
    if not trouve:
        print("  (aucune categorie 'pro'/'professionnel' existante -- terrain vierge)")


if __name__ == "__main__":
    main()
