"""
CME — Cartographie des titres SEO et meta descriptions reellement en ligne,
pour en degager des metriques de "coherence" et de "promesse d'action" et
ajuster les prochaines generations (prompt partage dans generer_brief_silo()
de pipeline.py -- MEME prompt pour les 4 silos, Solaire inclus : seule
difference pour Solaire, l'angle transactionnel impose (angle_force), pas
le format/la longueur/la promesse d'action du titre_seo/meta_description,
qui sont des regles globales appliquees a tout le monde depuis avant son
ajout).

Pourquoi scraper le HTML rendu plutot que relire le brief ou la table
RankMath : le brief contient la PROPOSITION de l'IA au moment de la
redaction, pas forcement ce qui est reellement affiche dans les resultats
Google aujourd'hui (edition manuelle possible, troncature WordPress/theme,
etc). `04_pipeline_seo.rankmath_seo_data` necessite un acces SSH direct a
la base WordPress (cle O2SWITCH_SSH_PRIVATE_KEY, pas exposee a ce workflow
de maintenance) -- `agent_orcaas_seo_technique`/Cloud Run sont par ailleurs
a l'abandon cote usage (voir CLAUDE.md). Meme logique que
`auditer_liens_internes.py` : scraping direct HTTP depuis le runner GitHub
Actions (acces reseau complet, gratuit), lecture seule, rien n'est ecrit.

Verifications appliquees par page (chaque critere est un proxy objectif,
pas un jugement esthetique) :
  - titre_hors_longueur    : titre SERP hors de la cible 50-60 caracteres
                              imposee au moment de la generation
  - meta_hors_longueur     : meta hors de la cible 150-160 caracteres
  - pas_de_promesse_action : la meta ne commence ni par un des verbes
                              d'action imposes au prompt (Decouvrez,
                              Calculez, Comparez, Economisez, Profitez de,
                              Obtenez) ni par une accroche chiffree
                              (montant/pourcentage/delai) dans les ~40
                              premiers caracteres
    - titre_meta_redondants  : le titre et la meta se repetent (le meme
                              contenu redit deux fois n'apporte pas de
                              promesse supplementaire au clic)
  - mot_cle_absent_titre / mot_cle_absent_meta : le mot-cle principal
                              vise (historique_publications.mot_cle) n'
                              apparait nulle part dans le titre/la meta --
                              incoherence entre l'intention de ciblage et
                              ce que l'internaute voit reellement
  - titre_tronque / meta_tronque : signe de troncature (finit par "..."
                              ou "…")
  - titre_duplique_ailleurs : le meme titre SERP exact est utilise sur au
                              moins une autre page du site

Lecture seule -- aucune ecriture, aucun --apply necessaire.

USAGE :
  python3 cartographier_titres_metas.py                 # audit complet
  python3 cartographier_titres_metas.py --limite=30      # test sur 30 pages

Necessite GOOGLE_APPLICATION_CREDENTIALS (lecture BigQuery) dans
l'environnement. Pas besoin de WP_APP_PASSWORD -- on lit les pages
publiques, pas l'API authentifiee.
"""
import re
import sys
import time

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("❌ requests/beautifulsoup4 manquant")

PROJECT_ID = "seo-data-hub-cme"
DATASET_ID = "04_pipeline_seo"

VERBES_ACTION = [
    "decouvrez", "découvrez", "calculez", "comparez",
    "economisez", "économisez", "profitez de", "profitez", "obtenez",
]
# Suffixe theme/RankMath ajoute au <title> rendu, a retirer avant d'en
# mesurer la longueur ou chercher le mot-cle (sinon fausse tous les
# chiffres de la meme maniere pour toutes les pages).
SUFFIXES_TITRE = [
    r"\s*[-|–]\s*Comprendre Mon [EÉ]nergie\s*$",
    r"\s*[-|–]\s*comprendre-mon-energie\.fr\s*$",
]


def parse_args():
    limite = None
    for arg in sys.argv:
        if arg.startswith("--limite="):
            limite = int(arg.split("=", 1)[1])
    return limite


def nettoyer_titre_rendu(titre_brut):
    t = titre_brut or ""
    for pattern in SUFFIXES_TITRE:
        t = re.sub(pattern, "", t, flags=re.IGNORECASE)
    return t.strip()


def a_promesse_action(meta):
    debut = meta[:40].lower()
    if any(debut.startswith(v) or v in debut for v in VERBES_ACTION):
        return True
    # accroche chiffree concrete : un chiffre dans les 40 premiers caracteres
    return bool(re.search(r"\d", debut))


def tokens_significatifs(texte):
    return {m.lower() for m in re.findall(r"[a-zàâéèêëîïôûùüç]{4,}", (texte or "").lower())}


def redondance(titre, meta):
    t1, t2 = tokens_significatifs(titre), tokens_significatifs(meta)
    if not t1 or not t2:
        return False
    overlap = len(t1 & t2) / len(t1 | t2)
    return overlap >= 0.6


def main():
    limite = parse_args()
    client = bigquery.Client(project=PROJECT_ID)

    print("📥 Recuperation des articles publies (historique_publications)...")
    query_articles = f"""
        SELECT url_wp, silo, sous_silo_strategique, mot_cle
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE url_wp IS NOT NULL AND url_wp != ''
        ORDER BY date_publication DESC
    """
    df = client.query(query_articles).to_dataframe()
    if limite:
        df = df.head(limite)
    print(f"  ✅ {len(df)} pages a auditer\n")

    print("📥 Recuperation des impressions GSC (90 jours, pour prioriser)...")
    try:
        query_gsc = f"""
            SELECT page, SUM(impressions) AS impressions
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
            GROUP BY page
        """
        df_gsc = client.query(query_gsc).to_dataframe()
        impressions_par_page = dict(zip(df_gsc["page"], df_gsc["impressions"]))
    except Exception as e:
        print(f"  ⚠️ GSC indisponible, priorisation par impressions desactivee : {e}")
        impressions_par_page = {}

    print("🌐 Lecture des titres/meta reellement en ligne...\n")
    resultats = []
    for i, row in df.iterrows():
        url = row["url_wp"]
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                resultats.append({"url": url, "erreur": f"HTTP {resp.status_code}"})
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            titre_tag = soup.find("title")
            meta_tag = soup.find("meta", attrs={"name": "description"})
            titre_brut = titre_tag.get_text().strip() if titre_tag else ""
            meta = meta_tag.get("content", "").strip() if meta_tag else ""
            titre = nettoyer_titre_rendu(titre_brut)
        except Exception as e:
            resultats.append({"url": url, "erreur": str(e)[:150]})
            continue

        mot_cle = row["mot_cle"] or ""
        mc_tokens = tokens_significatifs(mot_cle)
        titre_tokens = tokens_significatifs(titre)
        meta_tokens = tokens_significatifs(meta)

        flags = []
        if not titre:
            flags.append("titre_vide")
        elif not (50 <= len(titre) <= 60):
            flags.append("titre_hors_longueur")
        if not meta:
            flags.append("meta_vide")
        elif not (150 <= len(meta) <= 160):
            flags.append("meta_hors_longueur")
        if meta and not a_promesse_action(meta):
            flags.append("pas_de_promesse_action")
        if titre and meta and redondance(titre, meta):
            flags.append("titre_meta_redondants")
        if mc_tokens and not (mc_tokens & titre_tokens):
            flags.append("mot_cle_absent_titre")
        if mc_tokens and not (mc_tokens & meta_tokens):
            flags.append("mot_cle_absent_meta")
        if titre.endswith("...") or titre.endswith("…"):
            flags.append("titre_tronque")
        if meta.endswith("...") or meta.endswith("…"):
            flags.append("meta_tronque")

        resultats.append({
            "url": url, "silo": row["silo"], "sous_silo": row["sous_silo_strategique"],
            "mot_cle": mot_cle, "titre": titre, "meta": meta,
            "titre_longueur": len(titre), "meta_longueur": len(meta),
            "flags": flags,
            "impressions": impressions_par_page.get(url, 0),
        })
        if (i + 1) % 50 == 0:
            print(f"  ... {i+1}/{len(df)} pages lues")
        time.sleep(0.15)

    ok = [r for r in resultats if "erreur" not in r]
    erreurs = [r for r in resultats if "erreur" in r]

    # Doublons de titre exact entre pages differentes
    compte_titres = {}
    for r in ok:
        compte_titres[r["titre"]] = compte_titres.get(r["titre"], 0) + 1
    for r in ok:
        if r["titre"] and compte_titres[r["titre"]] > 1:
            r["flags"].append("titre_duplique_ailleurs")

    print(f"\n{'='*72}")
    print(f"RAPPORT — CARTOGRAPHIE TITRES/META ({len(ok)} pages lues, {len(erreurs)} erreurs)")
    print(f"{'='*72}")

    # --- Metriques globales ---
    total = len(ok) or 1
    tous_flags = [f for r in ok for f in r["flags"]]
    print("\n📊 METRIQUES GLOBALES (part des pages concernees)")
    for flag in sorted(set(tous_flags)):
        n = sum(1 for r in ok if flag in r["flags"])
        print(f"  {flag:<28} : {n:>4}/{total} ({100*n/total:.1f}%)")

    # --- Metriques par silo ---
    print(f"\n📊 METRIQUES PAR SILO")
    silos = sorted(set(r["silo"] for r in ok))
    for silo in silos:
        sous_ensemble = [r for r in ok if r["silo"] == silo]
        n_total = len(sous_ensemble) or 1
        print(f"\n  — {silo} ({n_total} pages) —")
        for flag in sorted(set(tous_flags)):
            n = sum(1 for r in sous_ensemble if flag in r["flags"])
            if n:
                print(f"      {flag:<28} : {n:>4}/{n_total} ({100*n/n_total:.1f}%)")

    # --- Pires cas : classes par nb de failles, puis par impressions ---
    pires = sorted(ok, key=lambda r: (-len(r["flags"]), -r["impressions"]))
    pires = [r for r in pires if r["flags"]][:20]
    print(f"\n{'='*72}")
    print(f"TOP {len(pires)} PIRES CAS (le plus de failles, priorite aux pages a fort volume)")
    print(f"{'='*72}")
    for r in pires:
        print(f"\n  {r['url']}")
        print(f"     {r['silo']} / {r['sous_silo']} — impressions(90j)={int(r['impressions'])}")
        print(f"     titre ({r['titre_longueur']}c) : {r['titre']}")
        print(f"     meta  ({r['meta_longueur']}c) : {r['meta']}")
        print(f"     ⚠️ {', '.join(r['flags'])}")

    if erreurs:
        print(f"\n{'='*72}")
        print(f"ERREURS DE LECTURE ({len(erreurs)})")
        print(f"{'='*72}")
        for r in erreurs[:20]:
            print(f"  {r['url']} : {r['erreur']}")


if __name__ == "__main__":
    main()
