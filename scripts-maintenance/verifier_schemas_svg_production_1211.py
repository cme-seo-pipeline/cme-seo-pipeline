"""
CME — Verification VISUELLE (lecture seule) que le correctif des titres de
schemas SVG qui depassaient leur bloc (CLAUDE.md, "Schemas SVG — titres qui
depassent leur bloc", 11/11/2026) est bien applique sur de VRAIS articles
publies aujourd'hui (12/11/2026), pas seulement sur le cas synthetique
deja valide par diagnostiquer_overflow_schemas_svg.py.

Le sandbox Claude Code ne peut pas joindre le site WordPress live
directement (voir CLAUDE.md, "Contraintes de l'environnement Claude Code")
et ne peut pas non plus "voir" une image via le pont GitHub Actions (seul
un fichier TEXTE est committe par le workflow). Ce script contourne ca en
encodant les images reellement generees aujourd'hui en base64 directement
dans le log texte -- le sandbox peut ensuite les decoder et les afficher.

Demarche :
  1. Articles publies aujourd'hui (historique_publications).
  2. Pour chacun, contenu live (API REST publique, pas besoin d'auth pour
     un article deja publie) -> extraction des <img> dont le src contient
     _flowchart.png / _technique.png / _comparatif.png (voir
     nettoyer_et_generer_schemas(), pipeline.py -- pattern de nommage
     exact des schemas).
  3. Telecharge jusqu'a 3 images (une de chaque type si possible,
     priorite au premier article qui en a) et les encode en base64 dans
     le log, chacune delimitee par un marqueur clair.

LECTURE SEULE -- ne modifie rien.
"""
import sys
import os
import re
import base64

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"Import de pipeline/pipeline.py impossible : {e}")

TYPES_SCHEMA = ["flowchart", "technique", "comparatif"]
MAX_IMAGES = 3

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_USERNAME or not WP_APP_PASSWORD:
    sys.exit("❌ WP_USERNAME/WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")


def section(titre):
    print("\n" + "=" * 100)
    print(titre)
    print("=" * 100)


def main():
    client_bq = init_bigquery()

    section("1. Articles publies aujourd'hui (historique_publications)")
    df = client_bq.query(f"""
        SELECT post_id, url_wp, silo, titre
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE DATE(date_publication) = CURRENT_DATE()
        ORDER BY date_publication
    """).to_dataframe()
    if df.empty:
        print("  (0 article publie aujourd'hui -- rien a verifier visuellement pour l'instant)")
        return
    print(df[["post_id", "silo", "titre"]].to_string(index=False))

    section("2. Recherche de schemas SVG dans le contenu BRUT stocke (API REST, contourne le cache LiteSpeed "
            "qui ferait rater les images injectees APRES le premier passage de cache, voir CLAUDE.md)")
    trouves = {}  # type_schema -> (article_titre, image_url)
    for _, row in df.iterrows():
        if len(trouves) >= len(TYPES_SCHEMA):
            break
        post_id = row["post_id"]
        try:
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/posts/{post_id}?context=edit",
                auth=(WP_USERNAME, WP_APP_PASSWORD),
                timeout=20,
            )
        except Exception as e:
            print(f"  ⚠️ post_id={post_id} injoignable : {e}")
            continue
        if r.status_code != 200:
            print(f"  ⚠️ post_id={post_id} -> HTTP {r.status_code}")
            continue
        contenu_brut = r.json().get("content", {}).get("raw", "")
        soup = BeautifulSoup(contenu_brut, "html.parser")
        imgs = soup.find_all("img")
        srcs = [img.get("src", "") for img in imgs]
        if srcs:
            print(f"  📄 post_id={post_id} ({row['titre'][:40]}) -- {len(srcs)} <img> au total :")
            for s in srcs:
                print(f"      {s}")
        # Tolere un suffixe anti-collision WordPress (-1, -2...) ajoute par
        # WP quand plusieurs articles du meme silo le meme jour produisent
        # un nom de fichier identique (type_schema + index H2, sans post_id).
        for src in srcs:
            for t in TYPES_SCHEMA:
                if t in trouves:
                    continue
                if re.search(rf"_{t}(-\d+)?\.png", src, re.IGNORECASE):
                    trouves[t] = (row["titre"], src)
                    print(f"    ✅ {t} retenu -- {src}")

    if not trouves:
        print("  (aucun schema trouve dans les articles publies aujourd'hui -- rien a telecharger)")
        return

    section(f"3. Telechargement + encodage base64 ({len(trouves)} image(s))")
    for t, (titre_article, img_url) in trouves.items():
        try:
            r = requests.get(img_url, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"  ⚠️ Echec telechargement {img_url} : {e}")
            continue
        b64 = base64.b64encode(r.content).decode("ascii")
        print(f"\n--- DEBUT_IMAGE type={t} article={titre_article[:60]!r} taille_octets={len(r.content)} ---")
        # Imprime par blocs de 2000 caracteres pour rester lisible dans le log.
        for i in range(0, len(b64), 2000):
            print(b64[i:i + 2000])
        print(f"--- FIN_IMAGE type={t} ---")

    section("FIN")


if __name__ == "__main__":
    main()
