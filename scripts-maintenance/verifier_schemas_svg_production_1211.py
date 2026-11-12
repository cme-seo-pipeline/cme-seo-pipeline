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

    section("2. Recherche de schemas SVG (image <img> _flowchart/_technique/_comparatif) dans ces articles")
    trouves = {}  # type_schema -> (article_titre, image_url)
    for _, row in df.iterrows():
        if len(trouves) >= len(TYPES_SCHEMA):
            break
        url = row["url_wp"]
        try:
            r = requests.get(url, timeout=20)
        except Exception as e:
            print(f"  ⚠️ {url} injoignable : {e}")
            continue
        if r.status_code != 200:
            print(f"  ⚠️ {url} -> HTTP {r.status_code}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for img in soup.find_all("img"):
            src = img.get("src", "")
            for t in TYPES_SCHEMA:
                if t in trouves:
                    continue
                if f"_{t}.png" in src:
                    trouves[t] = (row["titre"], src)
                    print(f"  ✅ {t} trouve -- article {row['post_id']!r} ({row['titre'][:50]}) -- {src}")

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
