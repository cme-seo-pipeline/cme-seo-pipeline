"""
CME — Analyse des clusters d'articles quasi-dupliques et plan d'enrichissement
editorial (reponse a la demande explicite de l'operateur : "amelioration et
richesse editoriale SEO sur les articles dupliques", plutot qu'une simple
fusion/redirection mecanique).

ETAPE 1 (ce script) : detection + plan. Groupe les articles publies dont le
titre a la meme "forme" (meme structure une fois les nombres/dates/pourcentages
effaces) dans le meme silo/sous-silo, puis demande a Claude, pour chaque
cluster d'au moins 2 articles, un avis editorial : fusionner (avec un plan
d'enrichissement qui combine la valeur unique de chaque variante) ou
differencier (si les angles sont en realite distincts). LECTURE SEULE --
n'ecrit rien sur WordPress ni sur BigQuery. Les corrections (fusion de
contenu, redirection 301) seront une ETAPE 2 separee, apres relecture
humaine de ce plan -- on ne touche jamais a du contenu deja publie et
indexe sans validation prealable.

USAGE :
  python3 analyser_duplication_editoriale.py                 # tous les clusters trouves
  python3 analyser_duplication_editoriale.py --limite=5       # teste sur 5 clusters seulement

Necessite GOOGLE_APPLICATION_CREDENTIALS et ANTHROPIC_API_KEY dans
l'environnement.
"""
import os
import re
import sys
import json
import unicodedata

import requests

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    sys.exit("❌ ANTHROPIC_API_KEY manquant dans l'environnement")

MODEL = "claude-sonnet-4-5-20250929"


def normaliser_forme(titre):
    """Reduit un titre a sa 'forme' structurelle : minuscules, accents
    retires, tout nombre (pourcentage, annee, date, suffixe -0810-2...)
    efface, ponctuation reduite -- pour regrouper des titres qui ne
    different que par une valeur variable."""
    t = unicodedata.normalize('NFKD', titre or '').encode('ascii', 'ignore').decode('ascii')
    t = t.lower()
    t = re.sub(r'\d+([.,]\d+)?\s*%?', ' ', t)   # nombres, pourcentages
    t = re.sub(r'[^a-z ]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def colonne(df, *candidats):
    for c in candidats:
        if c in df.columns:
            return c
    return None


def appeler_claude(prompt):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": 600, "messages": [{"role": "user", "content": prompt}]},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['content'][0]['text']


def main():
    limite = None
    for arg in sys.argv:
        if arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])

    client = bigquery.Client(project=PROJECT_ID)
    print("📥 Lecture de historique_publications...")
    df = client.query(f"SELECT * FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`").to_dataframe()

    col_titre = colonne(df, "titre", "title")
    col_post = colonne(df, "post_id", "id")
    col_url = colonne(df, "url_wp", "url")
    col_silo = colonne(df, "silo")
    col_sous_silo = colonne(df, "sous_silo_strategique", "sous_silo")
    col_date = colonne(df, "date_publication", "date", "publie_le")

    manquantes = [n for n, c in [("titre", col_titre), ("post_id", col_post), ("silo", col_silo)] if not c]
    if manquantes:
        sys.exit(f"❌ Colonnes introuvables : {manquantes} -- colonnes reelles : {list(df.columns)}")

    print(f"   {len(df)} articles charges — colonnes utilisees : titre={col_titre}, post_id={col_post}, "
          f"url={col_url}, silo={col_silo}, sous_silo={col_sous_silo}, date={col_date}\n")

    df['_forme'] = df[col_titre].apply(normaliser_forme)
    cle_groupe = [col_silo] + ([col_sous_silo] if col_sous_silo else []) + ['_forme']
    groupes = df[df['_forme'].str.len() > 0].groupby(cle_groupe)

    clusters = [g for _, g in groupes if len(g) >= 2]
    clusters.sort(key=len, reverse=True)
    print(f"🔎 {len(clusters)} cluster(s) d'articles quasi-dupliques trouve(s) (meme forme de titre, meme silo)\n")

    if limite:
        clusters = clusters[:limite]
        print(f"   (limite de test : {limite} cluster(s))\n")

    for i, cluster in enumerate(clusters, 1):
        print(f"\n{'='*70}")
        print(f"CLUSTER {i}/{len(clusters)} — {len(cluster)} articles — silo : {cluster.iloc[0][col_silo]}"
              + (f" / {cluster.iloc[0][col_sous_silo]}" if col_sous_silo else ""))
        print(f"{'='*70}")

        lignes_titres = []
        for _, row in cluster.iterrows():
            date_txt = f" ({row[col_date]})" if col_date else ""
            url_txt = f" — {row[col_url]}" if col_url else ""
            print(f"  - post_id={row[col_post]} : \"{row[col_titre]}\"{date_txt}{url_txt}")
            lignes_titres.append(f"- (post_id={row[col_post]}) {row[col_titre]}")

        prompt = (
            "Voici un groupe d'articles publies sur un meme site SEO, dont les titres se ressemblent "
            "fortement (meme structure, ne differant que par une valeur comme un pourcentage ou une date) :\n\n"
            + "\n".join(lignes_titres) +
            "\n\nDonne un avis editorial court et actionnable, EXACTEMENT dans ce format :\n"
            "===VERDICT===\n"
            "(fusionner | differencier)\n"
            "===POST_ID_A_GARDER===\n"
            "(le post_id a garder comme article principal si fusion, sinon vide)\n"
            "===PLAN===\n"
            "(si fusion : 3-5 points sur ce qu'il faut integrer de chaque variante dans l'article garde, pour "
            "le rendre plus riche et plus complet qu'aucune des variantes seules. si differenciation : "
            "l'angle distinct propose pour chaque article, pour qu'ils cessent de se faire concurrence sur "
            "la meme requete.)\n"
            "===FIN==="
        )
        try:
            texte = appeler_claude(prompt)
            print(f"\n{texte.strip()}")
        except Exception as e:
            print(f"\n⚠️ Erreur appel Claude : {e}")


if __name__ == "__main__":
    main()
