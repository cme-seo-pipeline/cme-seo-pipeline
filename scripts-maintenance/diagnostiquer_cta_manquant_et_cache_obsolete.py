"""
CME — Diagnostic (lecture seule) en 2 volets, suite a la demande operateur du
04/11/2026 ("on verifie et on ajoute ce qui manque" + "verifier les articles
qui ont l'ancienne version") :

VOLET 1 — pourquoi l'article attestation-de-contrat-delectricite (id=2218,
4461 mots selon inspecter_3_articles_cta_manquant.py -- largement au-dessus
de tous les seuils) ne montrerait pas le(s) formulaire(s) inline ?
  Hypotheses a trancher :
    a) Cache LiteSpeed obsolete (page HTML mise en cache AVANT l'ajout du
       mecanisme CTA ou avant le redesign du 04/11) -- verifiable en
       cherchant un evenement 'ancienne signature' dans interactions_contenu
       pour ce post_id precis.
    b) Structure HTML inhabituelle qui ferait echouer la recherche de bloc
       eligible (P/UL/OL/TABLE/FIGURE/BLOCKQUOTE) du JS cote client --
       verifiable en comptant ces balises dans le contenu brut.
  Pas de verification possible pour une 3e hypothese (JS desactive/bloque
  par un plugin de securite, etc.) depuis ce sandbox -- hors de portee.

VOLET 2 — plus largement, y a-t-il UN SEUL evenement aujourd'hui (04/11),
APRES le deploiement effectif du mu-plugin (~18:00 UTC), qui porte encore
la signature de l'ANCIENNE version (pre-04/11) du mecanisme ?
  Ancienne signature distinctive :
    - type_evenement='form_etape' avec etape purement numerique (ex. '0',
      '1', ...) -- dans la nouvelle version, form_etape n'a plus que
      etape='termine'.
    - type_evenement='form_abandon' avec etape != 'vu' -- dans la nouvelle
      version, form_abandon porte toujours etape='vu'.
  Toute ligne positive = page encore servie depuis un cache LiteSpeed
  obsolete pour ce post_id precis -- a purger cote operateur.

LECTURE SEULE -- aucune ecriture.

USAGE :
  python3 diagnostiquer_cta_manquant_et_cache_obsolete.py
"""
import os
import re
import sys

import requests
from bs4 import BeautifulSoup
from google.cloud import bigquery

SITE = "https://www.comprendre-mon-energie.fr"
PROJECT = "seo-data-hub-cme"
DATASET = "04_pipeline_seo"
TABLE = "interactions_contenu"
POST_ID_ATTESTATION = 2218
SEUIL_DEPLOIEMENT_UTC = "2026-11-04 18:00:00"

BALISES_ELIGIBLES = ["p", "ul", "ol", "table", "figure", "blockquote"]


def volet1():
    print("=" * 90)
    print("VOLET 1 — structure HTML de l'article attestation-de-contrat-delectricite (id=2218)")
    print("=" * 90)
    resp = requests.get(
        f"{SITE}/wp-json/wp/v2/posts/{POST_ID_ATTESTATION}",
        params={"_fields": "id,link,content"},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  ❌ HTTP {resp.status_code} : {resp.text[:200]}")
        return
    html = (resp.json().get("content") or {}).get("rendered", "")
    soup = BeautifulSoup(html, "html.parser")

    # On se limite a .entry-content si present (c'est la zone que le JS cible),
    # sinon on retombe sur tout le document.
    zone = soup.select_one(".entry-content") or soup
    print(f"  Zone ciblee        : {'.entry-content trouve' if soup.select_one('.entry-content') else 'NON TROUVE -- analyse sur tout le document'}")

    for tag in BALISES_ELIGIBLES:
        elements = zone.find_all(tag)
        # on ne garde que ceux avec au moins un peu de texte (pas des conteneurs vides)
        avec_texte = [e for e in elements if e.get_text(strip=True)]
        print(f"  <{tag}>" + " " * (10 - len(tag)) + f": {len(elements)} au total, {len(avec_texte)} avec du texte visible")

    # Structure generale : combien de <div> directement enfants, pour voir si le
    # contenu est majoritairement construit en div plutot qu'en balises de bloc classiques
    divs_directs = len(zone.find_all("div", recursive=False)) if zone.name else 0
    print(f"  <div> enfants directs de la zone ciblee : {divs_directs}")
    print()


def volet2():
    print("=" * 90)
    print("VOLET 2 — recherche de signature 'ancienne version' apres le deploiement (>= 18h00 UTC le 04/11)")
    print("=" * 90)
    client = bigquery.Client(project=PROJECT)

    query = f"""
        SELECT timestamp, source_post_id, type_evenement, etape, cible
        FROM `{PROJECT}.{DATASET}.{TABLE}`
        WHERE DATE(timestamp) = '2026-11-04'
          AND timestamp >= TIMESTAMP('{SEUIL_DEPLOIEMENT_UTC}')
          AND (
                (type_evenement = 'form_etape' AND REGEXP_CONTAINS(etape, r'^[0-9]+$'))
             OR (type_evenement = 'form_abandon' AND etape != 'vu')
          )
        ORDER BY timestamp
    """
    rows = list(client.query(query).result())
    if not rows:
        print("  ✅ Aucune signature 'ancienne version' trouvee apres le deploiement.")
        print("     -> Aucun indice de cache LiteSpeed obsolete sur les pages ayant genere du trafic trackE.")
    else:
        print(f"  ⚠️ {len(rows)} evenement(s) avec signature ancienne version trouve(s) :")
        for r in rows:
            print(f"    {r.timestamp} | post_id={r.source_post_id} | {r.type_evenement} | etape={r.etape!r} | cible={r.cible!r}")
        posts_concernes = sorted(set(r.source_post_id for r in rows))
        print(f"\n  Post_id(s) a purger en priorite (cache LiteSpeed) : {posts_concernes}")
    print()

    print("  --- Evenements (toutes signatures) pour l'article attestation-de-contrat-delectricite (id=2218) ---")
    query2 = f"""
        SELECT timestamp, type_evenement, etape, cible
        FROM `{PROJECT}.{DATASET}.{TABLE}`
        WHERE CAST(source_post_id AS STRING) = '{POST_ID_ATTESTATION}'
        ORDER BY timestamp DESC
        LIMIT 20
    """
    rows2 = list(client.query(query2).result())
    if not rows2:
        print("  (aucun evenement jamais enregistre pour cet article)")
    else:
        for r in rows2:
            print(f"    {r.timestamp} | {r.type_evenement} | etape={r.etape!r} | cible={r.cible!r}")


def main():
    volet1()
    volet2()


if __name__ == "__main__":
    main()
