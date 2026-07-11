"""
CME — Injection CTA sur TOUS les articles WordPress (y compris pre-pipeline)
"""
import sys
import requests

WP_CONFIG = {
    "url": "https://www.comprendre-mon-energie.fr",
    "username": "Ouss",
    "app_password": "6V3u GZyx LLg3 V8gG 5JCv fsVs"
}

CTA_MARKER = "cme-cta-tool-injected"

CTA_TOOLS = {
    "gaz": {
        "url": "https://www.comprendre-mon-energie.fr/comparateur-energie-electricite-gaz/",
        "titre": "Comparez les offres Gaz au meilleur prix",
        "texte": "Trouvez l'offre la moins chere selon votre profil en 2 minutes, gratuitement.",
        "bouton": "Comparer les offres gaz",
        "couleur1": "#1e3a8a", "couleur2": "#3b82f6"
    },
    "electricite": {
        "url": "https://www.comprendre-mon-energie.fr/comparateur-energie-electricite-gaz/",
        "titre": "Comparez les offres Electricite au meilleur prix",
        "texte": "Trouvez l'offre la moins chere selon votre profil en 2 minutes, gratuitement.",
        "bouton": "Comparer les offres electricite",
        "couleur1": "#1e3a8a", "couleur2": "#3b82f6"
    },
    "solaire": {
        "url": "https://www.comprendre-mon-energie.fr/devis-panneau-solaire/",
        "titre": "Estimez votre installation solaire",
        "texte": "Rentabilite, nombre de panneaux et puissance kWc en 2 minutes, gratuitement.",
        "bouton": "Simuler mon projet solaire",
        "couleur1": "#052e16", "couleur2": "#16a34a"
    },
    "renovation-energetique": {
        "url": "https://www.comprendre-mon-energie.fr/simulateur-aides-renovation-energetique/",
        "titre": "Calculez vos aides a la renovation",
        "texte": "MaPrimeRenov', CEE, Eco-PTZ : estimez vos aides en 2 minutes, gratuitement.",
        "bouton": "Simuler mes aides",
        "couleur1": "#78350f", "couleur2": "#f59e0b"
    },
    "aide-energetique": {
        "url": "https://www.comprendre-mon-energie.fr/simulateur-aides-renovation-energetique/",
        "titre": "Calculez vos aides a la renovation",
        "texte": "MaPrimeRenov', CEE, Eco-PTZ : estimez vos aides en 2 minutes, gratuitement.",
        "bouton": "Simuler mes aides",
        "couleur1": "#78350f", "couleur2": "#f59e0b"
    },
}


def detecter_silo(link):
    path = link.replace(WP_CONFIG["url"], "").strip("/")
    segment = path.split("/")[0] if path else ""
    return segment if segment in CTA_TOOLS else None


def generer_cta_html(silo_key):
    cfg = CTA_TOOLS[silo_key]
    return f'''
<div id="{CTA_MARKER}" style="background:linear-gradient(135deg,{cfg["couleur1"]},{cfg["couleur2"]});border-radius:16px;padding:1.75rem;text-align:center;margin:32px 0;">
  <h3 style="color:#fff;font-size:20px;font-weight:700;margin:0 0 8px">{cfg["titre"]}</h3>
  <p style="color:rgba(255,255,255,.9);font-size:14px;margin:0 0 18px;line-height:1.5">{cfg["texte"]}</p>
  <a href="{cfg["url"]}" style="display:inline-block;background:#fff;color:{cfg["couleur2"]};font-size:15px;font-weight:700;padding:14px 32px;border-radius:10px;text-decoration:none;">{cfg["bouton"]} &rarr;</a>
</div>
'''


def lister_tous_les_posts():
    auth = (WP_CONFIG["username"], WP_CONFIG["app_password"])
    posts = []
    page = 1
    while True:
        r = requests.get(
            f"{WP_CONFIG['url']}/wp-json/wp/v2/posts",
            auth=auth,
            params={"per_page": 100, "page": page, "status": "publish", "context": "edit"},
            timeout=30
        )
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
    return posts


def main():
    dry_run = "--dry-run" in sys.argv
    auth = (WP_CONFIG["username"], WP_CONFIG["app_password"])

    print("📥 Recuperation de tous les articles WordPress...")
    posts = lister_tous_les_posts()
    print(f"   {len(posts)} articles trouves\n")

    total, deja_ok, injectes, erreurs, sans_mapping = 0, 0, 0, 0, 0

    for post in posts:
        total += 1
        post_id = post["id"]
        link = post["link"]
        titre = post.get("title", {}).get("rendered", "")

        silo_key = detecter_silo(link)
        if not silo_key:
            sans_mapping += 1
            continue

        contenu_actuel = post.get("content", {}).get("raw", post.get("content", {}).get("rendered", ""))

        if CTA_MARKER in contenu_actuel:
            deja_ok += 1
            continue

        cta_html = generer_cta_html(silo_key)
        nouveau_contenu = contenu_actuel + cta_html

        if dry_run:
            print(f"  🔍 [DRY-RUN] post_id={post_id} silo='{silo_key}' — {titre[:50]}")
            injectes += 1
            continue

        try:
            r2 = requests.post(
                f"{WP_CONFIG['url']}/wp-json/wp/v2/posts/{post_id}",
                json={"content": nouveau_contenu},
                auth=auth, timeout=30
            )
            if r2.status_code == 200:
                print(f"  ✅ post_id={post_id} silo='{silo_key}' — {titre[:50]}")
                injectes += 1
            else:
                print(f"  ❌ post_id={post_id} — HTTP {r2.status_code}")
                erreurs += 1
        except Exception as e:
            print(f"  ❌ post_id={post_id} — erreur : {e}")
            erreurs += 1

    print(f"\n{'='*60}")
    print(f"Total articles WordPress : {total}")
    print(f"Deja a jour               : {deja_ok}")
    print(f"CTA injectes              : {injectes}{' (DRY-RUN)' if dry_run else ''}")
    print(f"Hors silos (ignores)      : {sans_mapping}")
    print(f"Erreurs                   : {erreurs}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
