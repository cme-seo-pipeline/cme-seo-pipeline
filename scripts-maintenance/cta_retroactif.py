"""
CME — Injection retroactive des CTA sur les articles deja publies
"""
import sys
import requests
from google.cloud import bigquery

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"

WP_CONFIG = {
    "url": "https://www.comprendre-mon-energie.fr",
    "username": "Ouss",
    "app_password": "6V3u GZyx LLg3 V8gG 5JCv fsVs"
}

CTA_MARKER = "cme-cta-tool-injected"

CTA_TOOLS = {
    "1. Gaz": {
        "url": "https://www.comprendre-mon-energie.fr/comparateur-energie-electricite-gaz/",
        "titre": "Comparez les offres Gaz au meilleur prix",
        "texte": "Trouvez l'offre la moins chere selon votre profil en 2 minutes, gratuitement.",
        "bouton": "Comparer les offres gaz",
        "couleur1": "#1e3a8a", "couleur2": "#3b82f6"
    },
    "5. Électricité": {
        "url": "https://www.comprendre-mon-energie.fr/comparateur-energie-electricite-gaz/",
        "titre": "Comparez les offres Electricite au meilleur prix",
        "texte": "Trouvez l'offre la moins chere selon votre profil en 2 minutes, gratuitement.",
        "bouton": "Comparer les offres electricite",
        "couleur1": "#1e3a8a", "couleur2": "#3b82f6"
    },
    "4. Solaire": {
        "url": "https://www.comprendre-mon-energie.fr/devis-panneau-solaire/",
        "titre": "Estimez votre installation solaire",
        "texte": "Rentabilite, nombre de panneaux et puissance kWc en 2 minutes, gratuitement.",
        "bouton": "Simuler mon projet solaire",
        "couleur1": "#052e16", "couleur2": "#16a34a"
    },
    "2. Rénovation Énergétique": {
        "url": "https://www.comprendre-mon-energie.fr/simulateur-aides-renovation-energetique/",
        "titre": "Calculez vos aides a la renovation",
        "texte": "MaPrimeRenov', CEE, Eco-PTZ : estimez vos aides en 2 minutes, gratuitement.",
        "bouton": "Simuler mes aides",
        "couleur1": "#78350f", "couleur2": "#f59e0b"
    },
    "3. Aide Énergétique": {
        "url": "https://www.comprendre-mon-energie.fr/simulateur-aides-renovation-energetique/",
        "titre": "Calculez vos aides a la renovation",
        "texte": "MaPrimeRenov', CEE, Eco-PTZ : estimez vos aides en 2 minutes, gratuitement.",
        "bouton": "Simuler mes aides",
        "couleur1": "#78350f", "couleur2": "#f59e0b"
    },
}


def generer_cta_html(silo_name):
    cfg = CTA_TOOLS.get(silo_name)
    if not cfg:
        return None
    return f'''
<div id="{CTA_MARKER}" style="background:linear-gradient(135deg,{cfg["couleur1"]},{cfg["couleur2"]});border-radius:16px;padding:1.75rem;text-align:center;margin:32px 0;">
  <h3 style="color:#fff;font-size:20px;font-weight:700;margin:0 0 8px">{cfg["titre"]}</h3>
  <p style="color:rgba(255,255,255,.9);font-size:14px;margin:0 0 18px;line-height:1.5">{cfg["texte"]}</p>
  <a href="{cfg["url"]}" style="display:inline-block;background:#fff;color:{cfg["couleur2"]};font-size:15px;font-weight:700;padding:14px 32px;border-radius:10px;text-decoration:none;">{cfg["bouton"]} &rarr;</a>
</div>
'''


def main():
    dry_run = "--dry-run" in sys.argv
    client = bigquery.Client(project=PROJECT_ID)
    rows = client.query(f"""
        SELECT DISTINCT post_id, silo, titre, url_wp
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE post_id IS NOT NULL
        ORDER BY post_id
    """).result()

    total, deja_ok, injectes, erreurs, sans_mapping = 0, 0, 0, 0, 0

    for row in rows:
        total += 1
        post_id = row.post_id
        silo = row.silo
        cta_html = generer_cta_html(silo)
        if cta_html is None:
            print(f"  ⏭️  post_id={post_id} silo='{silo}' — pas de mapping CTA, ignore")
            sans_mapping += 1
            continue
        try:
            r = requests.get(
                f"{WP_CONFIG['url']}/wp-json/wp/v2/posts/{post_id}",
                auth=(WP_CONFIG['username'], WP_CONFIG['app_password']),
                params={"context": "edit"}, timeout=15
            )
            if r.status_code != 200:
                print(f"  ❌ post_id={post_id} — HTTP {r.status_code}")
                erreurs += 1
                continue
            data = r.json()
            contenu_actuel = data.get('content', {}).get('raw', data.get('content', {}).get('rendered', ''))
        except Exception as e:
            print(f"  ❌ post_id={post_id} — erreur lecture : {e}")
            erreurs += 1
            continue

        if CTA_MARKER in contenu_actuel:
            deja_ok += 1
            continue

        nouveau_contenu = contenu_actuel + cta_html

        if dry_run:
            print(f"  🔍 [DRY-RUN] post_id={post_id} silo='{silo}' — CTA serait injecte")
            injectes += 1
            continue

        try:
            r2 = requests.post(
                f"{WP_CONFIG['url']}/wp-json/wp/v2/posts/{post_id}",
                json={"content": nouveau_contenu},
                auth=(WP_CONFIG['username'], WP_CONFIG['app_password']),
                timeout=30
            )
            if r2.status_code == 200:
                print(f"  ✅ post_id={post_id} silo='{silo}' — CTA injecte")
                injectes += 1
            else:
                print(f"  ❌ post_id={post_id} — echec mise a jour HTTP {r2.status_code}")
                erreurs += 1
        except Exception as e:
            print(f"  ❌ post_id={post_id} — erreur ecriture : {e}")
            erreurs += 1

    print(f"\n{'='*60}")
    print(f"Total articles      : {total}")
    print(f"Deja a jour         : {deja_ok}")
    print(f"CTA injectes        : {injectes}{' (DRY-RUN, rien ecrit)' if dry_run else ''}")
    print(f"Sans mapping silo   : {sans_mapping}")
    print(f"Erreurs             : {erreurs}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
