#!/usr/bin/env python3
import time
# ============================================================
# CME SEO AI PIPELINE — pipeline.py
# Version Cloud Run
# ============================================================

import os
import re
import json
import html
import base64
import requests
import pandas as pd
from datetime import datetime, timedelta
from collections import Counter
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from google.cloud import bigquery
from google.auth import default

# ============================================================
# CONFIGURATION GLOBALE
# ============================================================
PROJECT_ID = 'seo-data-hub-cme'
DATASET_ID = '04_pipeline_seo'

CONFIG = {
    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
    "MODEL": "claude-haiku-4-5-20251001",
    "MAX_TOKENS": 1000,
    "MAX_CHARS_PAR_URL": 3000,
    "JOURS_PUBLICATION": [0, 1, 2, 3, 4, 5, 6],  # 7j/7
    "heure_publication": 8,
    "nb_articles_par_run": 9,  # 3 silos industrialises x 3 articles, 7j/7
    "fenetre_anti_doublon_jours": 90,
    # Desactive temporairement le temps que la verification du compte
    # developpeur Meta aboutisse (app bloquee cote Meta depuis debut aout).
    # Allege aussi la duree du run, qui compte desormais reellement vu que
    # /run-sync est plafonne a 30 min cote Cloud Scheduler.
    "FACEBOOK_INSTAGRAM_ACTIF": False,
}

WP_CONFIG = {
    "url": "https://www.comprendre-mon-energie.fr",
    "username": os.environ.get("WP_USERNAME", "Ouss"),
    "app_password": os.environ.get("WP_APP_PASSWORD", ""),
}

OPENAI_CONFIG = {
    "api_key": os.environ.get("OPENAI_API_KEY", ""),
    "model": "gpt-image-1",
    "size": "1536x1024",
    "quality": "medium",
}

SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")
CLARITY_API_TOKEN = os.environ.get("CLARITY_API_TOKEN", "")
FACEBOOK_CONFIG = {
    "page_id": os.environ.get("FACEBOOK_PAGE_ID", ""),
    "access_token": os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", ""),
}
CLIENT_API_URL = os.environ.get("CLIENT_API_URL", "https://cme-client-api-217943559750.europe-west1.run.app")
BROADCAST_API_KEY = os.environ.get("BROADCAST_API_KEY", "")
INSTAGRAM_CONFIG = {
    "business_account_id": os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", ""),
    "access_token": os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", ""),
}

BLACKLIST_DOMAINS = [
    'gouv.fr', 'energie-info', 'grdf', 'service-public.fr',
    'instagram', 'ademe.fr', 'wikipedia.org', 'lemonde.fr',
    'lefigaro.fr', 'youtube', 'facebook'
]
NEGATIVE_WORDS = ['voiture', 'gpl', 'véhicule', 'auto', 'occasion', 'emploi']

MAPPING_CATEGORIES_WP = {
    'Gaz': 'gaz',
    'Chauffage Gaz': 'chauffage-gaz',
    'Comparatifs Fournisseurs Gaz': 'comparatifs-fournisseurs-gaz',
    'Contrat Gaz': 'contrat-gaz',
    'Facture Gaz': 'facture-gaz',
    'Bouteilles': 'bouteilles',
    'Rénovation Énergétique': 'renovation-energetique',
    'Pompe à chaleur': 'pompe-a-chaleur',
    'Isolation': 'isolation',
    'Rénovation globale': 'renovation-globale',
    'Chaudière': 'chaudiere',
    'Poêle': 'poele',
    'Chauffe-eau thermodynamique': 'chauffe-eau-thermodynamique',
    'Audit énergétique': 'audit-energetique',
    'Bilan énergétique': 'bilan-energetique',
    'Aide Énergétique': 'aide-energetique',
    'Prime Énergie': 'prime-energie',
    'Prime énergie': 'prime-energie',
    'Aides chaudière': 'aides-chaudiere',
    'Aides combles perdus': 'aides-combles-perdus',
    'Aides rénovation toiture': 'aides-renovation-toiture',
    'Aides chauffe-eau thermodynamique': 'aides-chauffe-eau-thermodynamique',
    'Eco-prêt à taux zéro': 'eco-pret-a-taux-zero',
    "MaPrimeRénov'": 'maprimerenov',
    'TVA Réduite': 'tva-reduite',
    'Chèque énergie': 'cheque-energie',
    'Solaire': 'solaire',
    'Panneaux solaires': 'panneaux-solaires',
    'Batterie panneaux solaires': 'batterie-panneaux-solaires',
    'Système solaire combiné': 'systeme-solaire-combine',
    'Chauffe-eau solaire': 'chauffe-eau-solaire',
    'Kit solaire': 'kit-solaire',
    'Électricité': 'electricite',
    'Chauffage Électricité': 'chauffage-electricite',
    'Comparatifs Fournisseurs Électricité': 'comparatifs-fournisseurs-electricite',
    'Contrat Électricité': 'contrat-electricite',
    'Facture Électricité': 'facture-electricite',
    'Déménagement': 'demenagement',
    'Heures Pleines/Creuses': 'heures-pleines-creuses',
    'Compteur': 'compteur',
}

COULEURS_SILO = {
    'gaz': '#FF6D00',
    'rénovation': '#34A853',
    'renovation': '#34A853',
    'aide': '#9C27B0',
    'solaire': '#FBBC04',
    'electricite': '#1A73E8',
    'électricité': '#1A73E8',
}

STOPWORDS = set([
    "de","le","la","les","un","une","des","du","en","et","au","aux",
    "ce","se","sa","son","ses","sur","par","pour","dans","avec","qui",
    "que","quoi","dont","où","ou","si","ni","car","or","mais","donc",
    "à","y","il","ils","elle","elles","nous","vous","je","tu","on",
    "mon","ton","votre","notre","mes","tes","vos","nos","leur","leurs",
    "quand","comme","plus","tout","très","bien","aussi","même","autres",
    "est","pas","peut","sans","lors","ainsi","this","that","the","and",
    "for","with","your","you","our","are","has","have","was","not","its",
])

CHAMPS_LEXICAUX_ENERGIE = {
    "Travaux & Installation": [
        "installation","travaux","chantier","pose","rénovation","isolation",
        "chauffage","pompe","chaleur","fenêtres","toiture","combles","ventilation",
        "climatisation","ballon","thermique","thermodynamique","plancher","radiateur",
    ],
    "Aides & Financement": [
        "maprimerenov","anah","prime","aide","subvention","crédit","prêt","avance",
        "remboursement","cee","certificat","tva","réduite","financement","eligible",
    ],
    "Performance & DPE": [
        "dpe","diagnostic","étiquette","classe","performance","énergétique","bilan",
        "audit","consommation","kwh","facteur","réduction","gain","économies",
    ],
    "Énergie & Réseau": [
        "électricité","gaz","fioul","bois","granulés","solaire","photovoltaïque",
        "réseau","raccordement","compteur","linky","fournisseur","contrat","tarif",
    ],
    "Confort & Habitat": [
        "logement","maison","appartement","habitat","bâtiment","propriétaire",
        "locataire","copropriété","surface","m2","façade","mur","plancher",
    ],
    "Professionnels RGE": [
        "artisan","entreprise","rge","qualibat","qualitenr","reconnu","garant",
        "environnement","certifié","agréé","installateur","prestataire",
    ],
}

TOUS_MOTS_ENERGIE = set(
    mot for mots in CHAMPS_LEXICAUX_ENERGIE.values() for mot in mots
)

MAPPING_REQUETES = {
    'comparatifs fournisseurs': "meilleur fournisseur gaz naturel comparatif 2026",
    'chauffage': "chauffage gaz maison guide complet 2026",
    'bouteilles': "bouteille gaz butane propane prix comparatif",
    'contrat': "contrat gaz naturel offre particulier 2026",
    'facture': "comprendre facture gaz réduire consommation",
    'renovation globale': "rénovation globale maison aides financement 2026",
    'rénovation globale': "rénovation globale maison aides financement 2026",
    'isolation': "isolation maison travaux aides maprimerenov 2026",
    'pompe a chaleur': "pompe à chaleur prix installation aides 2026",
    'poele': "poêle à bois granulés prix installation aides",
    'chaudiere': "chaudière condensation prix installation remplacement",
    'chauffe eau thermodynamique': "chauffe-eau thermodynamique prix aides installation",
    'audit energetique': "audit énergétique obligatoire prix comment faire",
    'prime energie': "prime énergie CEE montant conditions 2026",
    'aides chaudiere': "aides remplacement chaudière maprimerenov CEE 2026",
    'aides combles perdus': "isolation combles perdus aide financement gratuit",
    'aides renovation toiture': "aide isolation toiture maprimerenov montant 2026",
    'eco-pret a taux zero': "éco-prêt taux zéro conditions montant travaux",
    'maprimerenov': "MaPrimeRénov 2026 montant conditions éligibilité",
    'tva reduite': "TVA réduite 5.5% travaux rénovation conditions",
    'cheque energie': "chèque énergie 2026 montant conditions bénéficiaires",
    'panneaux solaires': "panneaux solaires photovoltaïques prix installation 2026",
    'batterie panneaux solaires': "batterie stockage solaire prix rentabilité 2026",
    'systeme solaire combine': "système solaire combiné SSC prix installation",
    'chauffe-eau solaire': "chauffe-eau solaire prix installation aides",
    'kit solaire': "kit solaire plug and play balcon prix 2026",
    'comparatifs fournisseurs electricite': "comparateur fournisseur électricité moins cher 2026",
    'contrat electricite': "contrat électricité offre particulier choisir 2026",
    'facture electricite': "comprendre facture électricité réduire consommation",
    'chauffage electricite': "chauffage électrique économique radiateur 2026",
    'demenagement': "déménagement électricité démarches résiliation 2026",
    'heures pleines creuses': "heures creuses heures pleines avantages simulateur",
    'compteur': "compteur Linky fonctionnement consommation optimisation",
}


# ============================================================
# INITIALISATION
# ============================================================
def init_bigquery():
    """Initialise le client BigQuery avec Workload Identity (Cloud Run)"""
    credentials, project = default()
    return bigquery.Client(project=PROJECT_ID, credentials=credentials)


# ============================================================
# CELLULE 3B — ORCHESTRATEUR
# ============================================================
def est_jour_publication(config):
    jour_actuel = datetime.now().weekday()
    return jour_actuel in config.get('JOURS_PUBLICATION', [1, 3, 5])


def verifier_doublons(titre, mot_cle, client_bq, config):
    """Vérifie si le sous-silo a déjà été traité dans la fenêtre anti-doublon.
    Vérifie dans historique_publications (source de vérité) ET briefs_editoriaux.
    """
    date_limite = (datetime.now() - timedelta(
        days=config['fenetre_anti_doublon_jours']
    )).strftime('%Y-%m-%d')
    # Vérification principale : historique_publications
    titre_safe = titre[:20].replace("'", "\'")
    mot_cle_safe = mot_cle.replace("'", "\'")
    query_hist = f"""
    SELECT COUNT(*) as nb
    FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
    WHERE (
        LOWER(titre) LIKE LOWER('%{titre_safe}%')
        OR LOWER(mot_cle) = LOWER('{mot_cle_safe}')
        OR LOWER(IFNULL(sous_silo_strategique,'')) LIKE LOWER('%{titre_safe}%')
    )
    AND date_publication >= '{date_limite}'
    """
    # Vérification secondaire : briefs_editoriaux
    query_brief = f"""
    SELECT COUNT(*) as nb
    FROM `{PROJECT_ID}.{DATASET_ID}.briefs_editoriaux`
    WHERE (
        LOWER(titre_seo) LIKE LOWER('%{titre_safe}%')
        OR LOWER(mot_cle_principal) = LOWER('{mot_cle_safe}')
    )
    AND date_run >= '{date_limite}'
    """
    try:
        r1 = client_bq.query(query_hist).to_dataframe()
        if r1['nb'].iloc[0] > 0:
            return True
        r2 = client_bq.query(query_brief).to_dataframe()
        return r2['nb'].iloc[0] > 0
    except Exception as e:
        print(f"  ⚠️ verifier_doublons erreur: {e}")
        return False


def creer_table_historique(client_bq):
    schema = [
        bigquery.SchemaField("date_publication", "TIMESTAMP"),
        bigquery.SchemaField("post_id", "INTEGER"),
        bigquery.SchemaField("silo", "STRING"),
        bigquery.SchemaField("titre", "STRING"),
        bigquery.SchemaField("mot_cle", "STRING"),
        bigquery.SchemaField("url_wp", "STRING"),
        bigquery.SchemaField("run_id", "STRING"),
        bigquery.SchemaField("sous_silo_strategique", "STRING"),
        bigquery.SchemaField("image_id", "STRING"),
    ]
    table_id = f"{PROJECT_ID}.{DATASET_ID}.historique_publications"
    try:
        client_bq.get_table(table_id)
        print("✅ Table historique existante")
    except:
        table = bigquery.Table(table_id, schema=schema)
        client_bq.create_table(table)
        print("✅ Table historique créée")


def selectionner_silos_a_traiter(client_bq, config):
    """
    LOGIQUE INDUSTRIALISEE (post-analyse performance BigQuery/GSC/GA4) :
    seuls les 3 silos les plus performants sont traites (Electricite, Gaz,
    Aide Energetique — Solaire et Renovation Energetique abandonnes faute
    de resultats), avec 3 articles chacun par run au lieu d'1 seul.
    Utilise seo_opportunities (GSC+GA4) en priorite, fallback anciennete
    pour completer les slots restants si besoin.
    """
    tous_silos = ["5. Électricité", "1. Gaz", "3. Aide Énergétique"]
    ARTICLES_PAR_SILO = 3
    print(f"📅 Run industrialise → {len(tous_silos)} silos x {ARTICLES_PAR_SILO} articles : {', '.join(tous_silos)}")
    resultats = []

    for silo_du_jour in tous_silos:
        silo_safe = silo_du_jour.replace("'", "''")
        nb_trouves = 0
        sous_silos_deja_vus = []

        try:
            df_opp = client_bq.query(f"""
            SELECT
                '{silo_du_jour}' AS silo,
                COALESCE(NULLIF(sous_silo, ''), 'general') AS sous_silo,
                query AS mot_cle,
                score_opportunite,
                ROUND(position, 1) AS position,
                impressions,
                jours_depuis_pub
            FROM `{PROJECT_ID}.03_final.seo_opportunities`
            WHERE silo = '{silo_safe}'
              AND jours_depuis_pub >= 30
              AND sous_silo IS NOT NULL
            ORDER BY score_opportunite DESC
            LIMIT {ARTICLES_PAR_SILO}
            """).to_dataframe()

            for idx in range(len(df_opp)):
                df_ligne = df_opp.iloc[[idx]].copy()
                df_ligne['priorite'] = 1
                row = df_ligne.iloc[0]

                # 'general' est un placeholder technique — jamais un vrai sous-silo
                # WordPress. On le remplace par le sous-silo strategique le moins
                # recemment publie, en gardant le mot-cle GSC reel pour le contenu.
                if row['sous_silo'] == 'general':
                    try:
                        df_strat_fix = client_bq.query(f"""
                        SELECT s.sous_silo, MAX(h.date_publication) AS derniere_pub
                        FROM `{PROJECT_ID}.{DATASET_ID}.sous_silos_strategiques` s
                        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.historique_publications` h
                          ON h.silo = '{silo_safe}' AND h.sous_silo_strategique = s.sous_silo
                        WHERE s.silo = '{silo_safe}'
                        GROUP BY s.sous_silo
                        ORDER BY derniere_pub ASC NULLS FIRST
                        LIMIT 1
                        """).to_dataframe()
                        if not df_strat_fix.empty:
                            vrai_sous_silo = df_strat_fix.iloc[0]['sous_silo']
                            print(f"   🔀 'general' remplace par sous-silo reel : {vrai_sous_silo}")
                            df_ligne.loc[df_ligne.index[0], 'sous_silo'] = vrai_sous_silo
                            row = df_ligne.iloc[0]
                    except Exception as e_gen:
                        print(f"   ⚠️ Impossible de remplacer 'general' : {e_gen}")

                # Anti-collision : si ce sous-silo a deja ete pris pour un
                # AUTRE sujet de ce meme silo dans ce run, on le rend unique
                # avec un suffixe ' (2)', ' (3)'... Sans ca, generer_tous_briefs
                # (qui groupe par Silo+Sous-Silo) fusionnerait ces sujets
                # pourtant distincts en un seul brief. Le suffixe est retire
                # juste avant la vraie categorisation WordPress/BigQuery,
                # dans rediger_et_publier.
                sous_silo_base = row['sous_silo']
                if sous_silo_base in sous_silos_deja_vus:
                    occurrence = sous_silos_deja_vus.count(sous_silo_base) + 1
                    sous_silo_unique = f"{sous_silo_base} ({occurrence})"
                    df_ligne.loc[df_ligne.index[0], 'sous_silo'] = sous_silo_unique
                    row = df_ligne.iloc[0]
                sous_silos_deja_vus.append(sous_silo_base)

                print(f"   ✅ {row['silo']} | {row['sous_silo']} — "
                      f"'{row['mot_cle']}' (pos {row['position']}, "
                      f"score {row['score_opportunite']:.0f})")
                resultats.append(df_ligne[['silo', 'sous_silo', 'priorite', 'mot_cle']])
                nb_trouves += 1
        except Exception as e_opp:
            print(f"   ⚠️ {silo_du_jour} : seo_opportunities indisponible ({e_opp}) — fallback")

        nb_manquants = ARTICLES_PAR_SILO - nb_trouves
        if nb_manquants <= 0:
            continue

        if nb_trouves == 0:
            print(f"   ⚠️ {silo_du_jour} : seo_opportunities vide — fallback anciennete")
        else:
            print(f"   ℹ️ {silo_du_jour} : {nb_trouves}/{ARTICLES_PAR_SILO} trouves via SEO, {nb_manquants} en fallback anciennete")

        # ── FALLBACK par silo : ancienneté (pour les slots restants) ────
        try:
            df_strategie = client_bq.query(f"""
            SELECT silo, sous_silo, priorite
            FROM `{PROJECT_ID}.{DATASET_ID}.sous_silos_strategiques`
            WHERE silo = '{silo_safe}'
            ORDER BY priorite ASC
            """).to_dataframe()

            if df_strategie.empty:
                print(f"   ❌ Aucun sous-silo trouve pour {silo_du_jour}")
                continue

            df_hist = client_bq.query(f"""
            SELECT sous_silo_strategique,
                   MAX(date_publication) AS derniere_pub,
                   COUNT(*) AS nb_articles
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE silo = '{silo_safe}'
              AND sous_silo_strategique IS NOT NULL
            GROUP BY sous_silo_strategique
            """).to_dataframe()

            df_merge = df_strategie.merge(
                df_hist, left_on='sous_silo',
                right_on='sous_silo_strategique', how='left'
            )
            df_merge['derniere_pub'] = df_merge['derniere_pub'].fillna(
                pd.Timestamp('2000-01-01', tz='UTC')
            )
            df_merge['nb_articles'] = df_merge['nb_articles'].fillna(0)
            # Exclut les sous-silos deja pris via SEO opportunities pour ce
            # meme silo dans ce run : sans ca, le repli anciennete pouvait
            # re-choisir le meme sous-silo qu'un sujet SEO deja selectionne,
            # recreant la collision que le suffixe d'unicite est cense eviter.
            df_merge = df_merge[~df_merge['sous_silo'].isin(sous_silos_deja_vus)]
            df_merge = df_merge.sort_values(
                by=['nb_articles', 'derniere_pub'],
                ascending=[True, True]
            )
            df_final = df_merge.head(nb_manquants)[['silo', 'sous_silo', 'priorite']].copy()
            df_final['mot_cle'] = ''
            for _, r in df_final.iterrows():
                print(f"   ✅ {silo_du_jour} | {r['sous_silo']} (fallback anciennete)")
            resultats.append(df_final)
        except Exception as e_fb:
            print(f"   ❌ {silo_du_jour} : fallback echoue aussi ({e_fb})")

    if not resultats:
        print("❌ Aucun silo n'a pu etre traite")
        return None

    df_tous = pd.concat(resultats, ignore_index=True)
    print(f"\n✅ TOTAL : {len(df_tous)} sujets selectionnes sur {len(tous_silos)} silos")
    return df_tous


def generate_niche_query(silo, subcat):
    clean_silo = silo.split('. ')[-1] if '. ' in silo else silo
    clean_subcat = str(subcat).strip() if subcat and str(subcat) not in ['', 'nan'] else ''

    if clean_subcat:
        clean_subcat_human = clean_subcat.replace('-', ' ').lower()
        for key, requete in MAPPING_REQUETES.items():
            if key.lower() in clean_subcat_human or clean_subcat_human in key.lower():
                return requete
        return f"{clean_subcat_human} guide complet prix aides 2026"

    silo_lower = clean_silo.lower()
    if 'gaz' in silo_lower:
        return "fournisseur gaz naturel offre particulier comparatif 2026"
    elif 'électricité' in silo_lower or 'electricite' in silo_lower:
        return "comparateur fournisseur électricité offre moins chère 2026"
    elif 'rénovation' in silo_lower or 'renovation' in silo_lower:
        return "rénovation énergétique aides maprimerenov travaux 2026"
    elif 'aide' in silo_lower or 'prime' in silo_lower:
        return "aides énergie état financement travaux éligibilité 2026"
    elif 'solaire' in silo_lower:
        return "panneaux solaires installation prix aides état 2026"
    else:
        return f"{clean_silo} guide complet 2026"


def scraper_concurrents(silos_a_traiter, search_api_key):
    all_market_data = []
    print("🚀 SCRAPING CONCURRENTS...")

    for _, row in silos_a_traiter.iterrows():
        silo = row['silo']
        subcat = row['sous_silo']
        search_query = generate_niche_query(silo, subcat)
        print(f"🔎 {search_query}")

        params = {
            "engine": "google",
            "q": search_query,
            "location": "France",
            "api_key": search_api_key
        }
        organic_results = []
        for tentative in range(3):
            try:
                response = requests.get(
                    "https://www.searchapi.io/api/v1/search",
                    params=params, timeout=45
                )
                organic_results = response.json().get("organic_results", [])
                break
            except Exception as e:
                if tentative < 2:
                    attente = 5 * (tentative + 1)
                    print(f"⚠️ Scraping échoué (tentative {tentative+1}/3) : {e} — retry dans {attente}s")
                    time.sleep(attente)
                else:
                    print(f"❌ Scraping abandonné après 3 tentatives pour '{search_query}' : {e}")

        count = 0
        for r in organic_results:
            if count >= 5:
                break
            link = r.get("link", "")
            title = r.get("title", "").lower()
            if not any(d in link for d in BLACKLIST_DOMAINS) \
               and not any(w in title for w in NEGATIVE_WORDS):
                all_market_data.append({
                    "Requête_Niche": search_query,
                    "Silo": silo,
                    "Sous-Silo": subcat,
                    "Position": r.get("position"),
                    "Concurrent": r.get("title"),
                    "URL": link
                })
                count += 1

    df_market = pd.DataFrame(all_market_data)
    if df_market.empty:
        print("⚠️ Aucun resultat de scraping retenu (filtrage liste noire trop restrictif ou requetes sans resultats) — DataFrame vide retournee, le run continue sans donnees concurrentes pour ce lot")
        return pd.DataFrame(columns=['Requête_Niche', 'Silo', 'Sous-Silo', 'Position', 'Concurrent', 'URL'])
    df_market = df_market.groupby(['Silo', 'Sous-Silo']).head(5)
    return df_market


# ============================================================
# CELLULE 5 — EXTRACTION STRUCTURE HTML
# ============================================================
def extract_editorial_skeleton(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code in [404, 410]:
            return None, f"Page introuvable ({response.status_code})"
        if response.status_code == 403:
            return None, "Site bloqué (403)"
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        structure = []
        for tag in soup.find_all(['h1', 'h2', 'h3']):
            texte = tag.text.strip()
            if len(texte) > 10:
                structure.append({"Niveau": tag.name.upper(), "Texte": texte})
        return structure if structure else None, None
    except Exception as e:
        return None, str(e)


# ============================================================
# CELLULE 6 — NETTOYAGE & ENRICHISSEMENT
# ============================================================
def extraire_mots_cles_energie(mots_filtres):
    compteur = Counter(mots_filtres)
    mots_valeur = {mot: count for mot, count in compteur.items() if mot in TOUS_MOTS_ENERGIE}
    par_theme = {}
    for theme, mots_theme in CHAMPS_LEXICAUX_ENERGIE.items():
        mots_presents = {mot: mots_valeur[mot] for mot in mots_theme if mot in mots_valeur}
        if mots_presents:
            par_theme[theme] = sorted(mots_presents.items(), key=lambda x: x[1], reverse=True)
    return mots_valeur, par_theme


def extract_full_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code in [404, 410]:
            return None, f"Page introuvable ({response.status_code})"
        if response.status_code == 403:
            return None, "Site bloqué (403)"
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for tag in soup.find_all(['header', 'footer', 'nav', 'script', 'style', 'aside']):
            tag.decompose()

        paragraphes = []
        for p in soup.find_all('p'):
            texte = re.sub(r'\s+', ' ', p.get_text(separator=' ', strip=True))
            if len(texte.split()) > 8:
                paragraphes.append(texte)

        texte_global = ' '.join(paragraphes)
        mots_bruts = re.findall(r'\b[a-zàâäéèêëîïôùûüç]{3,}\b', texte_global.lower())
        mots_filtres = [m for m in mots_bruts if m not in STOPWORDS]

        return {
            "texte_global": texte_global,
            "mots_filtres": mots_filtres,
            "paragraphes": paragraphes,
            "volume_global": len(mots_bruts),
            "volume_moyen_par_paragraphe": round(
                sum(len(p.split()) for p in paragraphes) / len(paragraphes), 1
            ) if paragraphes else 0,
            "nb_paragraphes": len(paragraphes),
        }, None
    except Exception as e:
        return None, str(e)


def scraper_contenu_concurrents(df_market):
    all_contenus = []
    print("🧹 NETTOYAGE & ENRICHISSEMENT...")
    for _, row in df_market.iterrows():
        url = row['URL']
        silo = row['Silo']
        sous_silo = row['Sous-Silo']
        print(f"📂 {silo} | {sous_silo} | {url[:50]}")
        contenu, erreur = extract_full_content(url)
        if erreur:
            print(f"  {erreur}")
            continue
        mots_valeur, par_theme = extraire_mots_cles_energie(contenu['mots_filtres'])
        all_contenus.append({
            "Silo": silo, "Sous-Silo": sous_silo, "URL": url,
            "volume_global": contenu['volume_global'],
            "nb_paragraphes": contenu['nb_paragraphes'],
            "volume_moyen_par_paragraphe": contenu['volume_moyen_par_paragraphe'],
            "mots_cles_energie": mots_valeur,
            "richesse_par_theme": par_theme,
            "mots_filtres": contenu['mots_filtres'],
            "paragraphes": contenu['paragraphes'],
            "texte_global": contenu['texte_global'],
        })
    return pd.DataFrame(all_contenus)


# ============================================================
# CELLULE 7B — ANALYSE FAQ + STYLE CLAUDE
# ============================================================
def extraire_mot_cle_url(url):
    try:
        path = urlparse(url).path
        segments = [s for s in path.split('/') if s]
        if not segments:
            return None
        slug = segments[-1]
        slug = re.sub(r'\.(html|php|aspx|htm)$', '', slug)
        slug = slug.replace('-', ' ').replace('_', ' ')
        slug = re.sub(r'\?.*$', '', slug)
        slug = re.sub(r'\b\d+\b', '', slug)
        slug = re.sub(r'\s+', ' ', slug).strip()
        return slug if len(slug) > 3 else None
    except:
        return None


def extraire_mot_cle_principal(mots_cles_energie, url=None):
    if url:
        mot = extraire_mot_cle_url(url)
        if mot:
            return mot, "url"
    if mots_cles_energie:
        mot = max(mots_cles_energie, key=mots_cles_energie.get)
        return mot, "frequence"
    return "Non détecté", "aucun"


def extraire_faq(paragraphes):
    faq = []
    for p in paragraphes:
        for phrase in p.split('.'):
            phrase = phrase.strip()
            if phrase.endswith('?') and len(phrase.split()) > 4:
                faq.append(phrase)
    return faq[:10]


def analyser_style_claude(texte, silo, config, sous_silo=""):
    texte_tronque = texte[:config['MAX_CHARS_PAR_URL']]
    contexte_ss = f" sur le sous-thème '{sous_silo}'" if sous_silo else ""
    prompt = f"""Tu es un expert en analyse éditoriale SEO.
Analyse ce texte d'un concurrent sur "{silo}"{contexte_ss}.
Retourne UNIQUEMENT ce JSON :
{{
  "ton": "commercial | pédagogique | informatif | mixte",
  "niveau_lecture": "grand public | intermédiaire | expert",
  "longueur_moyenne_phrase": 15,
  "patterns_rhetoriques": ["liste", "questions"],
  "angle_editorial": "description courte de l'angle",
  "points_forts": ["point 1", "point 2"],
  "recommandation_redaction": "conseil en 1 phrase"
}}
Texte : {texte_tronque}"""

    headers = {
        "x-api-key": config['ANTHROPIC_API_KEY'],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {
        "model": config['MODEL'],
        "max_tokens": config['MAX_TOKENS'],
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
                         headers=headers, json=body, timeout=30)
        r.raise_for_status()
        contenu = r.json()['content'][0]['text'].strip()
        contenu = contenu.replace("```json", "").replace("```", "").strip()
        return json.loads(contenu), None
    except json.JSONDecodeError:
        return None, "⚠️ Réponse non parseable"
    except Exception as e:
        return None, f"❌ Erreur API : {e}"


def analyser_contenus(df_contenus, config):
    all_analyses = []
    print("🧠 ANALYSE ÉDITORIALE...")
    for _, row in df_contenus.iterrows():
        silo = row['Silo']
        sous_silo = row['Sous-Silo']
        url = row['URL']
        faq = extraire_faq(row['paragraphes'])
        mot_cle_principal, source_mk = extraire_mot_cle_principal(
            row['mots_cles_energie'], url
        )
        style, _ = analyser_style_claude(row['texte_global'], silo, config, sous_silo)
        all_analyses.append({
            "Silo": silo, "Sous-Silo": sous_silo, "URL": url,
            "mot_cle_principal": mot_cle_principal,
            "source_mot_cle": source_mk,
            "faq": faq, "style": style,
            "volume_global": row['volume_global'],
            "nb_paragraphes": row['nb_paragraphes'],
            "volume_moyen_par_paragraphe": row['volume_moyen_par_paragraphe'],
            "richesse_par_theme": row['richesse_par_theme'],
        })
    return pd.DataFrame(all_analyses)


# ============================================================
# CELLULE 8 — CONSOLIDATION + MAILLAGE
# ============================================================
def extraire_maillage_interne(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, 'html.parser')
        domaine_base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        liens = []
        vus = set()
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            texte = a.get_text(strip=True)
            url_complete = urljoin(domaine_base, href)
            if (urlparse(url_complete).netloc == urlparse(url).netloc
                    and len(texte) > 3
                    and not href.startswith('#')
                    and not href.startswith('mailto')
                    and url_complete != url
                    and url_complete not in vus):
                vus.add(url_complete)
                liens.append({"ancre": texte[:80], "url_cible": url_complete})
        return liens[:20]
    except:
        return []


def consolider_briefs(df_analyses, df_contenus):
    all_briefs = []
    print("🔗 CONSOLIDATION + MAILLAGE...")
    for _, row_analyse in df_analyses.iterrows():
        match = df_contenus[df_contenus['URL'] == row_analyse['URL']]
        if match.empty:
            continue
        row_contenu = match.iloc[0]
        style = row_analyse.get('style') or {}
        brief = {
            "Silo": row_analyse['Silo'],
            "Sous-Silo": row_analyse['Sous-Silo'],
            "URL_source": row_analyse['URL'],
            "mot_cle_principal": row_analyse['mot_cle_principal'],
            "source_mot_cle": row_analyse.get('source_mot_cle', 'N/A'),
            "volume_mots": row_contenu['volume_global'],
            "nb_paragraphes": row_contenu['nb_paragraphes'],
            "mots_par_paragraphe": row_contenu['volume_moyen_par_paragraphe'],
            "richesse_semantique": row_contenu['richesse_par_theme'],
            "faq": row_analyse['faq'],
            "nb_questions_faq": len(row_analyse['faq']) if row_analyse['faq'] else 0,
            "ton": style.get('ton', 'N/A'),
            "niveau_lecture": style.get('niveau_lecture', 'N/A'),
            "angle_editorial": style.get('angle_editorial', 'N/A'),
            "patterns_rhetoriques": style.get('patterns_rhetoriques', []),
            "points_forts": style.get('points_forts', []),
            "recommandation_redaction": style.get('recommandation_redaction', 'N/A'),
            "maillage_interne": extraire_maillage_interne(row_analyse['URL']),
            "nb_liens_internes": 0,
        }
        brief['nb_liens_internes'] = len(brief['maillage_interne'])
        all_briefs.append(brief)
    return pd.DataFrame(all_briefs)


# ============================================================
# CELLULE 9 — GÉNÉRATION BRIEFS ÉDITORIAUX
# ============================================================
def to_slug(texte):
    texte = texte.lower()
    for a, b in [('à','a'),('â','a'),('é','e'),('è','e'),('ê','e'),
                 ('î','i'),('ô','o'),('ù','u'),('û','u'),('ç','c'),
                 ("'",""),("'","")]:
        texte = texte.replace(a, b)
    texte = re.sub(r'[^a-z0-9-]', '-', texte)
    texte = re.sub(r'-+', '-', texte).strip('-')
    return texte


def preparer_contexte_silo(df_silo, silo_name):
    sous_silo = ''
    if 'Sous-Silo' in df_silo.columns:
        sous_silos = df_silo['Sous-Silo'].dropna().unique()
        if len(sous_silos) > 0:
            sous_silo = str(sous_silos[0]).strip()
    contexte = {
        "silo": silo_name,
        "sous_silo": sous_silo,
        "nb_concurrents": len(df_silo),
        "concurrents": []
    }
    for _, row in df_silo.iterrows():
        contexte['concurrents'].append({
            "url": row['URL_source'],
            "mot_cle": row['mot_cle_principal'],
            "volume_mots": row['volume_mots'],
            "nb_paragraphes": row['nb_paragraphes'],
            "mots_par_paragraphe": row['mots_par_paragraphe'],
            "ton": row['ton'],
            "niveau_lecture": row['niveau_lecture'],
            "angle_editorial": row['angle_editorial'],
            "patterns_rhetoriques": row['patterns_rhetoriques'],
            "points_forts": row['points_forts'],
            "recommandation": row['recommandation_redaction'],
            "faq": row['faq'][:5] if row['faq'] else [],
            "richesse_semantique": {
                theme: [m[0] for m in mots[:6]]
                for theme, mots in (row['richesse_semantique'] or {}).items()
            },
            "maillage_interne": [
                l['ancre'] for l in (row['maillage_interne'] or [])[:8]
            ]
        })
    return contexte


def recuperer_titres_existants(silo_name, client_bq):
    query = f"""
    SELECT titre, mot_cle
    FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
    WHERE silo = '{silo_name}'
    GROUP BY titre, mot_cle
    ORDER BY MAX(date_publication) DESC
    LIMIT 10
    """
    try:
        return client_bq.query(query).to_dataframe().to_dict('records')
    except:
        return []


def nettoyer_texte_ia(texte, annee_courante=None):
    """Filet de securite applique en plus des instructions de prompt (qui
    seules ne suffisent pas toujours) :
    - Corrige les entites HTML d'apostrophe mal rendues (&rsquo; etc.) en
      apostrophe droite simple.
    - Remplace toute annee obsolete (2020 a annee_courante-1, frequemment
      recopiee du contexte concurrent scrape) par l'annee en cours.
    """
    if not texte:
        return texte
    texte = re.sub(r'&[lr]squo;?', "'", texte)
    texte = re.sub(r'&#821[67];?', "'", texte)
    if annee_courante:
        for annee in range(2020, annee_courante):
            texte = re.sub(rf'\b{annee}\b', str(annee_courante), texte)
    return texte


def generer_brief_silo(contexte, config, titres_existants=None):
    silo = contexte.get('silo', '')
    sous_silo = contexte.get('sous_silo', '')
    silo_propre = silo.split('. ')[-1] if '. ' in silo else silo
    slug_silo = to_slug(silo_propre)
    slug_sous_silo = to_slug(sous_silo)
    annee_courante = datetime.now().year

    titres_str = ""
    if titres_existants:
        titres_str = "\n\nARTICLES DÉJÀ PUBLIÉS (À NE PAS RÉPÉTER) :\n"
        for t in titres_existants:
            titres_str += f"- \"{t['titre']}\" (mot-clé : {t['mot_cle']})\n"
        titres_str += "\nIMPORTANT : angle COMPLÈTEMENT DIFFÉRENT."

    prompt = f"""Tu es un expert SEO éditorial senior spécialisé dans l'énergie en France.
⚠️ CONTRAINTE ABSOLUE : brief EXCLUSIVEMENT sur :
→ SILO : {silo}
→ SOUS-SILO : {sous_silo}

STRUCTURE URL : /{slug_silo}/{slug_sous_silo}/[slug-article]/
{titres_str}

Génère un brief en JSON STRICT :
{{
  "silo": "{silo}",
  "sous_silo": "{sous_silo}",
  "angle_choisi": "prix | installation | comparatif | aides | fonctionnement | guide",
  "titre_seo": "titre SEO percutant, ENTRE 50 ET 60 CARACTERES pile (jamais plus, jamais moins de 50), phrase ou expression complete, ne JAMAIS couper un mot en cours de generation",
  "meta_description": "Meta description ORIENTEE ACTION pour maximiser le taux de clic. Commence par un verbe d'action a l'imperatif (Decouvrez, Calculez, Comparez, Economisez, Profitez de, Obtenez...) ou une accroche chiffree concrete (montant, pourcentage, delai). Inclut un benefice clair et tangible pour le lecteur, pas une simple description du contenu. ENTRE 150 ET 160 CARACTERES pile (jamais plus, jamais moins de 150), phrase complete se terminant par un point, ne JAMAIS couper un mot en cours de generation. Exemples de structure (a adapter, ne jamais copier tel quel) : 'Decouvrez [benefice concret] en [nombre] etapes simples.' ou 'Economisez jusqu'a [X] sur [sujet] : [benefice].'",
  "slug_article": "slug-article-uniquement",
  "slug_complet": "/{slug_silo}/{slug_sous_silo}/[slug-article]/",
  "mot_cle_principal": "mot-clé principal",
  "mots_cles_secondaires": ["mc1","mc2","mc3","mc4","mc5"],
  "volume_recommande": 2000,
  "ton_recommande": "ton recommandé",
  "angle_differentiant": "angle unique en 1 phrase",
  "structure": [
    {{"niveau":"H1","texte":"...","conseil":"..."}},
    {{"niveau":"H2","texte":"...","conseil":"..."}},
    {{"niveau":"H2","texte":"...","conseil":"..."}},
    {{"niveau":"H2","texte":"...","conseil":"..."}},
    {{"niveau":"H2","texte":"...","conseil":"..."}}
  ],
  "champ_semantique": {{
    "indispensables": ["mot1","mot2","mot3","mot4","mot5"],
    "enrichissement": ["mot1","mot2","mot3","mot4","mot5"],
    "a_eviter": ["mot1","mot2","mot3"]
  }},
  "faq_recommandee": [
    {{"question":"...","intention":"informationnelle"}},
    {{"question":"...","intention":"transactionnelle"}},
    {{"question":"...","intention":"informationnelle"}}
  ],
  "maillage_suggere": [
    {{"ancre":"...","theme_cible":"..."}}
  ],
  "conseil_redacteur": "conseil en 1 phrase"
}}
RÈGLES SUPPLÉMENTAIRES :
- Dates : n'utilise JAMAIS d'année dans titre_seo ou meta_description sauf {annee_courante} ou {annee_courante + 1}. INTERDIT toute année antérieure, même si le contexte concurrent scrapé en mentionne une.
- Apostrophes : utilise uniquement l'apostrophe droite simple (') — jamais d'entité HTML (&rsquo; interdit).
JSON uniquement."""

    headers = {
        "x-api-key": config['ANTHROPIC_API_KEY'],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {
        "model": config['MODEL'],
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
                         headers=headers, json=body, timeout=60)
        r.raise_for_status()
        contenu = r.json()['content'][0]['text'].strip()
        for prefix in ["```json", "```"]:
            if contenu.startswith(prefix):
                contenu = contenu[len(prefix):]
        if contenu.endswith("```"):
            contenu = contenu[:-3]
        return json.loads(contenu.strip()), None
    except Exception as e:
        return None, f"❌ Erreur : {e}"


def generer_tous_briefs(df_final, client_bq, config):
    all_briefs_finaux = {}
    print("✍️ GÉNÉRATION DES BRIEFS...")
    # Groupby standard par (Silo, Sous-Silo). L'unicite entre plusieurs
    # articles industrialises partageant le meme sous-silo est desormais
    # garantie EN AMONT, a la selection (suffixe ' (2)', ' (3)' ajoute
    # dans selectionner_silos_a_traiter) — pas ici via mot_cle_principal,
    # qui est extrait independamment par concurrent scrape et n'est pas
    # stable pour un meme sujet (cause d'une sur-fragmentation constatee).
    for (silo_name, sous_silo_name), df_silo in df_final.groupby(['Silo', 'Sous-Silo']):
        df_silo_clean = df_silo[df_silo['volume_mots'] > 0]
        if df_silo_clean.empty:
            continue
        contexte = preparer_contexte_silo(df_silo_clean, silo_name)
        titres_existants = recuperer_titres_existants(silo_name, client_bq)
        brief, erreur = generer_brief_silo(contexte, config, titres_existants)
        if erreur:
            print(f"  ❌ {silo_name} : {erreur}")
        else:
            annee_courante = datetime.now().year
            brief['titre_seo'] = nettoyer_texte_ia(brief.get('titre_seo', ''), annee_courante)
            brief['meta_description'] = nettoyer_texte_ia(brief.get('meta_description', ''), annee_courante)
            # 3e segment (mot-cle) ajoute pour garantir l'unicite de la
            # cle meme quand plusieurs sujets partagent le meme sous-silo.
            all_briefs_finaux[f"{silo_name}||{sous_silo_name}"] = brief
            print(f"  ✅ {silo_name} | {brief.get('sous_silo')} — {brief.get('titre_seo')}")
    return all_briefs_finaux


# ============================================================
# CELLULE 10 — EXPORT BIGQUERY
# ============================================================
def exporter_bigquery(df_final, all_briefs_finaux, client_bq):
    date_run = datetime.now().strftime("%Y-%m-%d")
    run_id = datetime.now().strftime("%Y%m%d_%H%M")

    # Export analyse_concurrents
    df_export = df_final.copy()
    df_export['run_id'] = run_id
    df_export['date_run'] = date_run
    cols_json = ['richesse_semantique', 'faq', 'patterns_rhetoriques',
                 'points_forts', 'maillage_interne']
    for col in cols_json:
        if col in df_export.columns:
            df_export[col] = df_export[col].apply(
                lambda x: json.dumps(x, ensure_ascii=False) if x else '[]'
            )
    df_export.columns = [
        c.lower().replace('-', '_').replace(' ', '_')
        for c in df_export.columns
    ]
    job = client_bq.load_table_from_dataframe(
        df_export,
        f"{PROJECT_ID}.{DATASET_ID}.analyse_concurrents",
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_APPEND", autodetect=True)
    )
    job.result()
    print(f"✅ analyse_concurrents : {len(df_export)} lignes")

    # Export briefs_editoriaux
    rows = []
    for _cle, brief in all_briefs_finaux.items():
        # split('||') sans limite : la cle contient maintenant 3 segments
        # (silo||sous_silo||mot_cle) depuis le correctif anti-collision.
        # parts[2:] (le mot-cle) est ignore ici, seul silo/sous_silo compte.
        parts = _cle.split('||')
        silo_name = parts[0]
        sous_silo_override = parts[1] if len(parts) > 1 else ''

        rows.append({
            "run_id": run_id, "date_run": date_run, "silo": silo_name,
            "titre_seo": brief.get('titre_seo', ''),
            "meta_description": brief.get('meta_description', ''),
            "mot_cle_principal": brief.get('mot_cle_principal', ''),
            "mots_cles_secondaires": json.dumps(brief.get('mots_cles_secondaires', []), ensure_ascii=False),
            "volume_recommande": brief.get('volume_recommande', 0),
            "ton_recommande": brief.get('ton_recommande', ''),
            "angle_differentiant": brief.get('angle_differentiant', ''),
            "structure": json.dumps(brief.get('structure', []), ensure_ascii=False),
            "champ_semantique": json.dumps(brief.get('champ_semantique', {}), ensure_ascii=False),
            "faq_recommandee": json.dumps(brief.get('faq_recommandee', []), ensure_ascii=False),
            "conseil_redacteur": brief.get('conseil_redacteur', ''),
            "brief_complet": json.dumps(brief, ensure_ascii=False),
        })
    job = client_bq.load_table_from_dataframe(
        pd.DataFrame(rows),
        f"{PROJECT_ID}.{DATASET_ID}.briefs_editoriaux",
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_APPEND", autodetect=True)
    )
    job.result()
    print(f"✅ briefs_editoriaux : {len(rows)} briefs")
    return run_id


# ============================================================
# CELLULE 11 — RÉDACTION + PUBLICATION WORDPRESS
# ============================================================
def auditer_article(post_id, titre, indicateur, valeur_actuelle, unite, config):
    """CHANTIER MISE A JOUR DES ARTICLES : verifie si un article cite une
    valeur reglementaire precise comme un fait actuel (pas un exemple
    fictif), et si elle est devenue obsolete, genere directement le
    passage corrige. Un seul appel IA combine verification + correction
    pour limiter la latence."""
    try:
        r_article = requests.get(
            f"https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts/{post_id}",
            timeout=20
        )
        if r_article.status_code != 200:
            return {"post_id": post_id, "statut": "erreur", "detail": "article introuvable"}
        contenu_html = r_article.json()['content']['rendered']
    except Exception as e:
        return {"post_id": post_id, "statut": "erreur", "detail": str(e)}

    prompt = f"""Tu es un auditeur de contenu factuel, rigoureux et prudent.

ARTICLE (titre) : {titre}

CONTENU HTML DE L'ARTICLE :
{contenu_html[:6000]}

DONNEE OFFICIELLE ACTUELLE A VERIFIER :
- Indicateur : {indicateur}
- Valeur actuelle en vigueur : {valeur_actuelle} {unite}

TACHE :
1. Determine si cet article presente une valeur CHIFFREE PRECISE pour "{indicateur}" comme un FAIT REGLEMENTAIRE ACTUEL (pas un exemple fictif, pas une simulation avec "imaginons"/"exemple"/"prenons le cas").
2. Si oui ET que cette valeur differe de la valeur actuelle ci-dessus, propose une correction MINIMALE : reprends EXACTEMENT le meme passage HTML mais avec la valeur mise a jour, sans rien changer d'autre au style, a la structure ou au reste du texte. Arrondis a 2 decimales maximum.

Reponds UNIQUEMENT en JSON strict, sans texte autour :
{{
  "cite_donnee_reelle": true ou false,
  "valeur_obsolete": true ou false,
  "passage_exact_html": "le passage HTML exact copie mot pour mot si cite_donnee_reelle=true, sinon chaine vide",
  "passage_corrige_html": "le meme passage avec la valeur mise a jour si valeur_obsolete=true, sinon chaine vide",
  "justification": "1 phrase expliquant ta decision"
}}"""
    headers = {
        "x-api-key": config['ANTHROPIC_API_KEY'],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {"model": config['MODEL'], "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]}
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=60)
        texte = r.json()['content'][0]['text'].strip()
        texte = re.sub(r'^```json\s*|```\s*$', '', texte, flags=re.IGNORECASE)
        verdict = json.loads(texte)
        verdict['post_id'] = post_id
        verdict['contenu_html_actuel'] = contenu_html
        verdict['statut'] = 'ok'
        return verdict
    except Exception as e:
        return {"post_id": post_id, "statut": "erreur", "detail": str(e)}


def appliquer_correction_article(verdict, wp_config, client_bq):
    """Applique la correction d'un article via l'API REST WordPress, avec
    verification de securite que le passage exact existe bien avant de le
    remplacer (annule silencieusement sinon, plutot que de risquer une
    modification incorrecte). Journalise chaque correction pour tracabilite,
    meme en l'absence de validation humaine."""
    post_id = verdict['post_id']
    passage_avant = verdict['passage_exact_html']
    passage_apres = verdict['passage_corrige_html']
    contenu_actuel = verdict['contenu_html_actuel']

    if not passage_avant or passage_avant not in contenu_actuel:
        print(f"  ⚠️ Post {post_id} : passage exact non retrouve, correction annulee par securite")
        return False

    nouveau_contenu = contenu_actuel.replace(passage_avant, passage_apres, 1)

    try:
        r = requests.post(
            f"https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts/{post_id}",
            auth=(wp_config['USER'], wp_config['APP_PASSWORD']),
            json={"content": nouveau_contenu},
            timeout=30
        )
        if r.status_code != 200:
            print(f"  ❌ Post {post_id} : echec MAJ WordPress ({r.status_code})")
            return False
    except Exception as e:
        print(f"  ❌ Post {post_id} : erreur MAJ WordPress ({e})")
        return False

    try:
        client_bq.insert_rows_json(f"{PROJECT_ID}.{DATASET_ID}.corrections_articles_auto", [{
            "post_id": post_id,
            "titre": verdict.get('titre', ''),
            "indicateur": verdict.get('indicateur', ''),
            "passage_avant": passage_avant,
            "passage_apres": passage_apres,
            "date_correction": datetime.now().isoformat(),
            "url_wp": verdict.get('url_wp', ''),
        }])
    except Exception as e:
        print(f"  ⚠️ Post {post_id} : correction appliquee mais log echoue ({e})")

    print(f"  ✅ Post {post_id} corrige automatiquement")
    return True


def auditer_et_corriger_articles(client_bq, config, wp_config):
    """CHANTIER MISE A JOUR DES ARTICLES PUBLIES : audite tous les candidats
    en pertinence directe (mapping_indicateur_sous_silo) et corrige
    automatiquement, sans validation humaine, toute citation reelle
    devenue obsolete. Concu pour tourner periodiquement (mensuel) via
    Cloud Scheduler."""
    print("🔍 AUDIT ARTICLES — recherche de citations obsoletes...")
    try:
        df_candidats = client_bq.query(f"""
        SELECT DISTINCT m.indicateur, h.post_id, h.titre, h.url_wp
        FROM `{PROJECT_ID}.{DATASET_ID}.mapping_indicateur_sous_silo` m
        JOIN `{PROJECT_ID}.{DATASET_ID}.historique_publications` h
            ON h.silo = m.silo AND h.sous_silo_strategique = m.sous_silo_strategique
        WHERE m.pertinence = 'directe'
        """).to_dataframe()
        df_valeurs = client_bq.query(f"""
        SELECT indicateur, valeur, unite,
          ROW_NUMBER() OVER (PARTITION BY indicateur ORDER BY date_verification DESC) as rang
        FROM `{PROJECT_ID}.{DATASET_ID}.indicateurs_reglementaires`
        QUALIFY rang = 1
        """).to_dataframe()
    except Exception as e:
        print(f"  ⚠️ Erreur chargement candidats : {e}")
        return {"audites": 0, "corriges": 0}

    valeurs = {r['indicateur']: (r['valeur'], r['unite']) for _, r in df_valeurs.iterrows()}
    nb_audites = 0
    nb_corriges = 0
    for _, row in df_candidats.iterrows():
        if row['indicateur'] not in valeurs:
            continue
        valeur, unite = valeurs[row['indicateur']]
        verdict = auditer_article(row['post_id'], row['titre'], row['indicateur'], valeur, unite, config)
        nb_audites += 1
        if verdict.get('statut') != 'ok':
            continue
        if verdict.get('cite_donnee_reelle') and verdict.get('valeur_obsolete'):
            verdict['titre'] = row['titre']
            verdict['url_wp'] = row['url_wp']
            verdict['indicateur'] = row['indicateur']
            if appliquer_correction_article(verdict, wp_config, client_bq):
                nb_corriges += 1
    print(f"🔍 AUDIT TERMINE : {nb_audites} article(s) audite(s), {nb_corriges} corrige(s)")
    return {"audites": nb_audites, "corriges": nb_corriges}


def normaliser_url(url):
    """Normalise une URL pour comparaison stable : protocole et www retires,
    slash final retire, minuscules. Doit rester identique a la logique
    utilisee cote SQL dans la vue seo_opportunities."""
    import re as re_mod
    if not url:
        return ""
    u = re_mod.sub(r'^https?://(www\.)?', '', url.strip().lower())
    u = re_mod.sub(r'/$', '', u)
    return u


def rafraichir_wp_url_mapping(client_bq):
    """CHANTIER GROWTH ENGINEERING : reconstruit la table de correspondance
    URL -> post_id WordPress, source de verite pour toute jointure future
    (au lieu de comparer des URLs brutes, fragiles face aux restructurations
    de site). Interroge directement l'API WordPress (etat reel actuel),
    pagine sur tous les articles publies, puis remplace entierement la
    table (WRITE_TRUNCATE — cette table reflete l'etat actuel, pas un
    historique)."""
    print("🔗 RAFRAICHISSEMENT MAPPING URL → POST_ID...")
    lignes = []
    # CHANTIER G.3 (correctif decouvert lors de l'audit technique) : les
    # pages WordPress statiques (accueil, outils comparateur/aides/solaire,
    # demande-confirmee...) sont un TYPE DE CONTENU DIFFERENT des articles
    # de blog dans l'API REST WordPress (endpoint /pages, pas /posts).
    # Elles etaient absentes du mapping, cassant silencieusement la
    # resolution des leads generes directement depuis les pages outils.
    for type_contenu in ("posts", "pages"):
        page_num = 1
        try:
            while True:
                r = requests.get(
                    f"https://www.comprendre-mon-energie.fr/wp-json/wp/v2/{type_contenu}",
                    params={"per_page": 100, "page": page_num, "status": "publish", "_fields": "id,link"},
                    timeout=30
                )
                if r.status_code != 200:
                    break
                data = r.json()
                if not data:
                    break
                for post in data:
                    url = post.get('link', '')
                    lignes.append({
                        "post_id": post.get('id'),
                        "url": url,
                        "url_normalized": normaliser_url(url),
                        "date_maj": datetime.now().isoformat(),
                    })
                page_num += 1
        except Exception as e:
            print(f"  ⚠️ Erreur recuperation {type_contenu} WordPress : {e}")
    if not lignes:
        return 0

    if not lignes:
        print("  ⚠️ Aucun post recupere, mapping non mis a jour")
        return 0

    # CHANTIER GROWTH ENGINEERING (suite) : resolution des anciennes URLs.
    # Google Search Console peut encore rapporter des URLs d'avant une
    # restructuration du site (l'index Google met du temps a se mettre a
    # jour). WordPress redirige proprement (301) ces anciennes URLs vers
    # les nouvelles, mais notre mapping ne le savait pas jusqu'ici. On
    # suit ces redirections pour ajouter ces anciennes URLs comme alias
    # du meme post_id, dans le meme lot que celui charge plus bas.
    try:
        urls_connues = {l['url_normalized'] for l in lignes}
        df_gsc_urls = client_bq.query(f"""
        SELECT DISTINCT page AS url
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        """).to_dataframe()

        nb_redirects_resolus = 0
        for _, row_gsc in df_gsc_urls.iterrows():
            url_gsc = row_gsc['url']
            url_gsc_norm = normaliser_url(url_gsc)
            if not url_gsc_norm or url_gsc_norm in urls_connues:
                continue
            try:
                r_head = requests.head(url_gsc, allow_redirects=True, timeout=10)
                url_finale_norm = normaliser_url(r_head.url)
                if url_finale_norm == url_gsc_norm:
                    continue
                match = next((l for l in lignes if l['url_normalized'] == url_finale_norm), None)
                if match:
                    lignes.append({
                        "post_id": match['post_id'],
                        "url": url_gsc,
                        "url_normalized": url_gsc_norm,
                        "date_maj": datetime.now().isoformat(),
                    })
                    urls_connues.add(url_gsc_norm)
                    nb_redirects_resolus += 1
            except Exception:
                continue
        if nb_redirects_resolus:
            print(f"  🔀 {nb_redirects_resolus} ancienne(s) URL(s) reliee(s) a un post_id via redirection")
    except Exception as e:
        print(f"  ⚠️ Erreur resolution redirections : {e}")

    try:
        from google.cloud import bigquery as bq_module
        table_ref = f"{PROJECT_ID}.02_cleaned.wp_url_mapping"
        job_config = bq_module.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bq_module.SchemaField("post_id", "INTEGER"),
                bq_module.SchemaField("url", "STRING"),
                bq_module.SchemaField("url_normalized", "STRING"),
                bq_module.SchemaField("date_maj", "TIMESTAMP"),
            ],
        )
        # Job de chargement (remplacement atomique complet) plutot que
        # DELETE + insertion en streaming : evite le blocage "streaming
        # buffer" de BigQuery quand la table vient d'etre rafraichie
        # recemment (le DELETE echoue silencieusement dans ce cas).
        load_job = client_bq.load_table_from_json(lignes, table_ref, job_config=job_config)
        load_job.result()
        print(f"  ✅ {len(lignes)} correspondances URL → post_id mises a jour (remplacement complet)")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def rafraichir_leads_app_authentifies(client_bq):
    """CHANTIER SOUVERAINETE SHELL : synchronise les leads des utilisateurs
    connectes a l'app mobile/web (Firestore, sous-collection users/{uid}/leads)
    vers BigQuery. Complete leads_convertis (canal anonyme/tracking-api) pour
    obtenir une vue unifiee des conversions, tous canaux confondus."""
    print("🔗 SYNCHRONISATION LEADS APP AUTHENTIFIES...")
    lignes = []
    try:
        from google.cloud import firestore as firestore_module
        db_fs = firestore_module.Client(project=PROJECT_ID)
        docs = db_fs.collection_group('leads').stream()
        for d in docs:
            data = d.to_dict()
            owner_uid = d.reference.parent.parent.id
            derniere_maj = data.get('derniere_maj')
            lignes.append({
                "lead_id": d.id,
                "owner_uid": owner_uid,
                "tool": data.get('tool', ''),
                "statut": data.get('statut', ''),
                "source_post_id": str(data.get('source_post_id', '') or ''),
                "montant_estime": float(data.get('montant_estime', 0) or 0),
                "economie_estimee": float(data.get('economie_estimee', 0) or 0),
                "details": json.dumps(data.get('details', {}), ensure_ascii=False),
                "derniere_maj": derniere_maj.isoformat() if derniere_maj else None,
                "synced_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"  ⚠️ Erreur lecture Firestore : {e}")
        return 0

    if not lignes:
        print("  ℹ️ Aucun lead trouve dans Firestore")
        return 0

    try:
        from google.cloud import bigquery as bq_module
        table_ref = f"{PROJECT_ID}.04_pipeline_seo.leads_app_authentifies"
        job_config = bq_module.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bq_module.SchemaField("lead_id", "STRING"),
                bq_module.SchemaField("owner_uid", "STRING"),
                bq_module.SchemaField("tool", "STRING"),
                bq_module.SchemaField("statut", "STRING"),
                bq_module.SchemaField("source_post_id", "STRING"),
                bq_module.SchemaField("montant_estime", "FLOAT"),
                bq_module.SchemaField("economie_estimee", "FLOAT"),
                bq_module.SchemaField("details", "STRING"),
                bq_module.SchemaField("derniere_maj", "TIMESTAMP"),
                bq_module.SchemaField("synced_at", "TIMESTAMP"),
            ],
        )
        load_job = client_bq.load_table_from_json(lignes, table_ref, job_config=job_config)
        load_job.result()
        print(f"  ✅ {len(lignes)} leads app synchronises (remplacement complet)")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def rafraichir_clarity_insights(client_bq):
    """CHANTIER SOUVERAINETE SHELL : synchronise les insights Microsoft
    Clarity (Data Export API) vers BigQuery. Limite API : 10 requetes/jour
    par projet, max 3 jours de donnees par appel — on utilise numOfDays=1,
    en phase avec un rafraichissement quotidien unique."""
    print("🔗 SYNCHRONISATION CLARITY INSIGHTS...")
    if not CLARITY_API_TOKEN:
        print("  ⚠️ CLARITY_API_TOKEN absent, synchronisation ignoree")
        return 0
    try:
        resp = requests.get(
            "https://www.clarity.ms/export-data/api/v1/project-live-insights",
            headers={"Authorization": f"Bearer {CLARITY_API_TOKEN}"},
            params={"numOfDays": 1},
            timeout=30
        )
        if resp.status_code != 200:
            print(f"  ⚠️ Erreur API Clarity {resp.status_code} : {resp.text[:200]}")
            return 0
        metrics = resp.json()
    except Exception as e:
        print(f"  ⚠️ Erreur appel API Clarity : {e}")
        return 0

    if not metrics:
        print("  ℹ️ Aucune metrique retournee")
        return 0

    date_sync = datetime.now().date().isoformat()
    lignes = []
    for m in metrics:
        lignes.append({
            "date_sync": date_sync,
            "metric_name": m.get("metricName", ""),
            "information": json.dumps(m.get("information", []), ensure_ascii=False),
            "synced_at": datetime.now().isoformat(),
        })

    try:
        errors = client_bq.insert_rows_json(
            f"{PROJECT_ID}.04_pipeline_seo.clarity_insights_quotidien", lignes
        )
        if errors:
            print(f"  ⚠️ Erreurs insertion BQ : {errors}")
            return 0
        print(f"  ✅ {len(lignes)} metriques Clarity synchronisees")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def rafraichir_clarity_par_page(client_bq):
    """CHANTIER G.2 : synchronise les insights Clarity PAR PAGE (dimension1=URL)
    pour permettre le chainage engagement->page dans le tunnel de conversion
    unifie. Complete rafraichir_clarity_insights() (vue globale du projet)."""
    print("🔗 SYNCHRONISATION CLARITY PAR PAGE...")
    if not CLARITY_API_TOKEN:
        print("  ⚠️ CLARITY_API_TOKEN absent, synchronisation ignoree")
        return 0
    try:
        resp = requests.get(
            "https://www.clarity.ms/export-data/api/v1/project-live-insights",
            headers={"Authorization": f"Bearer {CLARITY_API_TOKEN}"},
            params={"numOfDays": 1, "dimension1": "URL"},
            timeout=30
        )
        if resp.status_code != 200:
            print(f"  ⚠️ Erreur API Clarity {resp.status_code} : {resp.text[:200]}")
            return 0
        metrics = resp.json()
    except Exception as e:
        print(f"  ⚠️ Erreur appel API Clarity : {e}")
        return 0

    if not metrics:
        print("  ℹ️ Aucune metrique retournee")
        return 0

    date_sync = datetime.now().date().isoformat()
    lignes = []
    for m in metrics:
        metric_name = m.get("metricName", "")
        for item in m.get("information", []):
            url = item.get("Url", "")
            if not url:
                continue
            autres = {k: v for k, v in item.items() if k != "Url"}
            lignes.append({
                "date_sync": date_sync,
                "metric_name": metric_name,
                "url": url,
                "donnees": json.dumps(autres, ensure_ascii=False),
                "synced_at": datetime.now().isoformat(),
            })

    if not lignes:
        print("  ℹ️ Aucune ligne avec URL a inserer (dimension non supportee pour cette metrique ?)")
        return 0

    try:
        errors = client_bq.insert_rows_json(
            f"{PROJECT_ID}.04_pipeline_seo.clarity_insights_par_page", lignes
        )
        if errors:
            print(f"  ⚠️ Erreurs insertion BQ : {errors}")
            return 0
        print(f"  ✅ {len(lignes)} lignes Clarity par page synchronisees")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def auditer_site_technique(client_bq):
    """CHANTIER G.3 : robot d'audit technique maison. Verifie chaque page
    connue (wp_url_mapping) : code de reponse, chaine de redirection,
    titre/meta/H1. Remplace Screaming Frog (licence + VM ecartees, decision
    du 31/08) — s'appuie sur les 437 URLs deja connues, pas de decouverte
    par crawl necessaire."""
    print("🔗 AUDIT TECHNIQUE DU SITE...")
    try:
        query = f"SELECT post_id, url FROM `{PROJECT_ID}.02_cleaned.wp_url_mapping`"
        df = client_bq.query(query).to_dataframe()
    except Exception as e:
        print(f"  ⚠️ Erreur lecture wp_url_mapping : {e}")
        return 0

    lignes = []
    for _, row in df.iterrows():
        post_id = int(row['post_id'])
        url = row['url']
        entree = {
            "post_id": post_id, "url": url, "status_code": None,
            "url_finale": None, "nb_redirections": 0,
            "titre": None, "titre_longueur": None,
            "meta_description": None, "meta_description_longueur": None,
            "h1_liste": None, "nb_h1": None,
            "erreur": None, "audite_le": datetime.now().isoformat(),
        }
        try:
            resp = requests.get(url, timeout=15, allow_redirects=True)
            entree["status_code"] = resp.status_code
            entree["url_finale"] = resp.url
            entree["nb_redirections"] = len(resp.history)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                titre_tag = soup.find('title')
                titre = titre_tag.get_text().strip() if titre_tag else None
                entree["titre"] = titre
                entree["titre_longueur"] = len(titre) if titre else 0
                meta_tag = soup.find('meta', attrs={'name': 'description'})
                meta = meta_tag.get('content', '').strip() if meta_tag else None
                entree["meta_description"] = meta
                entree["meta_description_longueur"] = len(meta) if meta else 0
                h1_tags = soup.find_all('h1')
                h1_textes = [h.get_text().strip() for h in h1_tags]
                entree["h1_liste"] = json.dumps(h1_textes, ensure_ascii=False)
                entree["nb_h1"] = len(h1_textes)
        except Exception as e:
            entree["erreur"] = str(e)[:200]
        lignes.append(entree)

    if not lignes:
        print("  ℹ️ Aucune page a auditer")
        return 0

    try:
        table_ref = f"{PROJECT_ID}.04_pipeline_seo.audit_technique_site"
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bigquery.SchemaField("post_id", "INTEGER"),
                bigquery.SchemaField("url", "STRING"),
                bigquery.SchemaField("status_code", "INTEGER"),
                bigquery.SchemaField("url_finale", "STRING"),
                bigquery.SchemaField("nb_redirections", "INTEGER"),
                bigquery.SchemaField("titre", "STRING"),
                bigquery.SchemaField("titre_longueur", "INTEGER"),
                bigquery.SchemaField("meta_description", "STRING"),
                bigquery.SchemaField("meta_description_longueur", "INTEGER"),
                bigquery.SchemaField("h1_liste", "STRING"),
                bigquery.SchemaField("nb_h1", "INTEGER"),
                bigquery.SchemaField("erreur", "STRING"),
                bigquery.SchemaField("audite_le", "TIMESTAMP"),
            ],
        )
        load_job = client_bq.load_table_from_json(lignes, table_ref, job_config=job_config)
        load_job.result()
        print(f"  ✅ {len(lignes)} pages auditees (remplacement complet)")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def synchroniser_rankmath(client_bq):
    """CHANTIER G.3 : recupere les donnees SEO RankMath (titre, description,
    mot-cle cible) directement depuis la base WordPress via WP-CLI (SSH,
    IP fixe) — plus rapide et plus fiable que des appels HTTP individuels."""
    print("🔗 SYNCHRONISATION RANKMATH...")
    import io
    import paramiko

    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname="109.234.167.170", port=22, username="jolu5920", pkey=pkey, timeout=15)

        wp_path = "/home/jolu5920/public_html/comprendre-mon-energie.com"
        sql = ("SELECT p.ID, "
               "MAX(CASE WHEN pm.meta_key='rank_math_title' THEN pm.meta_value END), "
               "MAX(CASE WHEN pm.meta_key='rank_math_description' THEN pm.meta_value END), "
               "MAX(CASE WHEN pm.meta_key='rank_math_focus_keyword' THEN pm.meta_value END) "
               "FROM wpwn_posts p LEFT JOIN wpwn_postmeta pm ON p.ID=pm.post_id "
               "AND pm.meta_key IN ('rank_math_title','rank_math_description','rank_math_focus_keyword') "
               "WHERE p.post_status='publish' AND p.post_type IN ('post','page') GROUP BY p.ID")
        cmd = f'wp --path="{wp_path}" db query "{sql}" --skip-column-names'
        stdin, stdout, stderr = client.exec_command(cmd)
        resultat = stdout.read().decode()
        erreur_ssh = stderr.read().decode()
        client.close()

        if erreur_ssh:
            print(f"  ⚠️ Erreur WP-CLI : {erreur_ssh[:300]}")
            return 0
    except Exception as e:
        print(f"  ⚠️ Erreur connexion SSH : {e}")
        return 0

    lignes = []
    for ligne in resultat.strip().split("\n"):
        if not ligne.strip():
            continue
        parts = ligne.split("\t")
        if not parts or not parts[0]:
            continue
        try:
            post_id = int(parts[0])
        except ValueError:
            continue
        def _val(i):
            return parts[i] if len(parts) > i and parts[i] != "NULL" else None
        lignes.append({
            "post_id": post_id,
            "rank_math_title": _val(1),
            "rank_math_description": _val(2),
            "rank_math_focus_keyword": _val(3),
            "synced_at": datetime.now().isoformat(),
        })

    if not lignes:
        print("  ℹ️ Aucune donnee RankMath recuperee")
        return 0

    try:
        table_ref = f"{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data"
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bigquery.SchemaField("post_id", "INTEGER"),
                bigquery.SchemaField("rank_math_title", "STRING"),
                bigquery.SchemaField("rank_math_description", "STRING"),
                bigquery.SchemaField("rank_math_focus_keyword", "STRING"),
                bigquery.SchemaField("synced_at", "TIMESTAMP"),
            ],
        )
        load_job = client_bq.load_table_from_json(lignes, table_ref, job_config=job_config)
        load_job.result()
        print(f"  ✅ {len(lignes)} lignes RankMath synchronisees")
    except Exception as e:
        print(f"  ⚠️ Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def agent_orcaas_seo_technique(client_bq):
    """AGENT ORCAAS V1 -- Stack SEO technique/commercial. Corrige les titres
    RankMath et meta descriptions manquants ou dupliques, en privilegiant
    une approche commerciale/transactionnelle (constat du porteur de projet :
    contenu trop informationnel, CTR faible) plutot que purement descriptive.
    Genere un brief pour chaque intervention, ecrit directement en base
    WordPress via WP-CLI. Controle total : pas de validation humaine par
    correction (decision du 01/09/2026)."""
    print("AGENT ORCAAS -- Stack SEO technique/commercial...")

    query = f"""
    WITH doublons_titre AS (
      SELECT rank_math_title FROM `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data`
      WHERE rank_math_title IS NOT NULL
      GROUP BY rank_math_title HAVING COUNT(*) > 1
    ),
    doublons_meta AS (
      SELECT rank_math_description FROM `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data`
      WHERE rank_math_description IS NOT NULL
      GROUP BY rank_math_description HAVING COUNT(*) > 1
    )
    SELECT r.post_id, m.url, r.rank_math_title, r.rank_math_description, r.rank_math_focus_keyword,
      CASE
        WHEN r.rank_math_title IS NULL THEN 'titre_manquant'
        WHEN r.rank_math_title IN (SELECT rank_math_title FROM doublons_titre) THEN 'titre_duplique'
        ELSE NULL
      END AS probleme_titre,
      CASE
        WHEN r.rank_math_description IS NULL THEN 'meta_manquante'
        WHEN r.rank_math_description IN (SELECT rank_math_description FROM doublons_meta) THEN 'meta_dupliquee'
        ELSE NULL
      END AS probleme_meta
    FROM `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data` r
    JOIN `{PROJECT_ID}.02_cleaned.wp_url_mapping` m ON m.post_id = r.post_id
    """
    df = client_bq.query(query).to_dataframe()
    df_problemes = df[(df['probleme_titre'].notna()) | (df['probleme_meta'].notna())]

    if df_problemes.empty:
        print("  Aucun probleme detecte")
        return 0

    print(f"  {len(df_problemes)} page(s) a corriger")

    import io
    import paramiko
    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname="109.234.167.170", port=22, username="jolu5920", pkey=pkey, timeout=15)
    except Exception as e:
        print(f"  Erreur connexion SSH : {e}")
        return 0

    wp_path = "/home/jolu5920/public_html/comprendre-mon-energie.com"
    briefs = []
    corrections_reussies = 0

    for _, row in df_problemes.iterrows():
        post_id = int(row['post_id'])
        url = row['url']
        titre_actuel = row['rank_math_title']
        meta_actuelle = row['rank_math_description']
        mot_cle = row['rank_math_focus_keyword'] or ''
        probleme_titre = row['probleme_titre']
        probleme_meta = row['probleme_meta']
        probleme_texte = ' + '.join([p for p in [probleme_titre, probleme_meta] if p])

        prompt = (
            "Tu es un expert SEO technique ET commercial pour un site francais sur "
            "l'energie (gaz/electricite/renovation/aides).\n"
            f"Cette page a un probleme de metadonnees : {probleme_texte}\n"
            f"URL : {url}\n"
            f"Mot-cle cible : {mot_cle or chr(39)+'non defini, deduis-le de l url'+chr(39)}\n"
            f"Titre actuel : {titre_actuel or 'AUCUN'}\n"
            f"Meta actuelle : {meta_actuelle or 'AUCUNE'}\n\n"
            "Genere un NOUVEAU titre SEO (entre 50 et 60 caracteres) ET une NOUVELLE "
            "meta description (entre 140 et 160 caracteres).\n"
            "Constat important : le contenu du site est trop informationnel, ce qui "
            "limite le taux de clic (CTR). Privilegie une approche COMMERCIALE et "
            "TRANSACTIONNELLE (benefice concret, chiffre, incitation a l'action) "
            "plutot que purement descriptive -- sans jamais inventer de donnee fausse "
            "(pas de prix ou pourcentage invente).\n\n"
            'Reponds UNIQUEMENT avec un JSON strict, rien d\'autre : {"titre": "...", "meta": "..."}'
        )

        nouveau_titre = titre_actuel
        nouvelle_meta = meta_actuelle
        erreur = None

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CONFIG['ANTHROPIC_API_KEY'], "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": CONFIG['MODEL'], "max_tokens": 300, "messages": [{"role": "user", "content": prompt}]},
                timeout=30
            )
            resp.raise_for_status()
            texte = resp.json()['content'][0]['text']
            texte_json = texte[texte.find('{'):texte.rfind('}')+1]
            correction = json.loads(texte_json)
            nouveau_titre = correction.get('titre', titre_actuel)
            nouvelle_meta = correction.get('meta', meta_actuelle)
        except Exception as e:
            erreur = f"Generation IA : {str(e)[:200]}"

        if erreur:
            briefs.append({
                "brief_id": f"{post_id}_{int(datetime.now().timestamp())}",
                "date_execution": datetime.now().isoformat(),
                "stack": "seo_technique", "post_id": post_id, "url": url,
                "probleme_detecte": probleme_texte,
                "valeur_avant": titre_actuel or meta_actuelle or "",
                "valeur_apres": "", "statut": "echec", "erreur": erreur,
            })
            continue

        titre_echap = nouveau_titre.replace('"', '\\"')
        meta_echap = nouvelle_meta.replace('"', '\\"')
        try:
            cmd = (f'wp --path="{wp_path}" post meta update {post_id} rank_math_title "{titre_echap}" && '
                   f'wp --path="{wp_path}" post meta update {post_id} rank_math_description "{meta_echap}"')
            stdin, stdout, stderr = ssh.exec_command(cmd)
            sortie_erreur = stderr.read().decode()
            if sortie_erreur and 'Success' not in sortie_erreur:
                raise Exception(sortie_erreur[:200])
            corrections_reussies += 1
            statut = "corrige"
            erreur = None
        except Exception as e:
            statut = "echec"
            erreur = f"Ecriture WP-CLI : {str(e)[:200]}"

        briefs.append({
            "brief_id": f"{post_id}_{int(datetime.now().timestamp())}",
            "date_execution": datetime.now().isoformat(),
            "stack": "seo_technique", "post_id": post_id, "url": url,
            "probleme_detecte": probleme_texte,
            "valeur_avant": f"Titre: {titre_actuel or 'AUCUN'} | Meta: {meta_actuelle or 'AUCUNE'}",
            "valeur_apres": f"Titre: {nouveau_titre} | Meta: {nouvelle_meta}",
            "statut": statut, "erreur": erreur,
        })

    ssh.close()

    if not briefs:
        print("  Aucun brief genere")
        return 0

    try:
        table_ref = f"{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs"
        errors = client_bq.insert_rows_json(table_ref, briefs)
        if errors:
            print(f"  Erreurs insertion briefs : {errors}")
    except Exception as e:
        print(f"  Erreur ecriture briefs BigQuery : {e}")

    print(f"  {corrections_reussies}/{len(briefs)} corrections reussies")
    return corrections_reussies


def agent_orcaas_evaluer_impact(client_bq):
    """AGENT ORCAAS -- Boucle d'evaluation. Pour chaque correction passee
    (agent_orcaas_briefs, statut='corrige') pas encore evaluee, compare les
    metriques GSC avant/apres pour mesurer l'impact reel. Ferme la boucle
    apprentissage : l'agent peut consulter ses propres resultats avant sa
    prochaine decision, plutot que d'agir sans jamais verifier."""
    print("AGENT ORCAAS -- Evaluation d'impact...")

    query = f"""
    SELECT b.brief_id, b.post_id, b.date_execution, m.url
    FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs` b
    JOIN `{PROJECT_ID}.02_cleaned.wp_url_mapping` m ON m.post_id = b.post_id
    WHERE b.statut = 'corrige'
      AND b.brief_id NOT IN (
        SELECT brief_id FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
      )
    """
    try:
        df_briefs = client_bq.query(query).to_dataframe()
    except Exception as e:
        print(f"  Erreur lecture briefs : {e}")
        return 0

    if df_briefs.empty:
        print("  Aucun brief a evaluer")
        return 0

    lignes = []
    for _, row in df_briefs.iterrows():
        post_id = int(row['post_id'])
        url = row['url']
        date_correction = row['date_execution']
        brief_id = row['brief_id']

        maintenant = datetime.now(date_correction.tzinfo) if date_correction.tzinfo else datetime.now()
        jours_ecoules = (maintenant - date_correction).days

        url_norm = url.lower()
        for prefixe in ("https://www.", "http://www.", "https://", "http://"):
            if url_norm.startswith(prefixe):
                url_norm = url_norm[len(prefixe):]
                break
        url_norm = url_norm.rstrip("/")

        query_metriques = f"""
        SELECT
          SUM(CASE WHEN date < DATE('{date_correction.date()}') AND date >= DATE_SUB(DATE('{date_correction.date()}'), INTERVAL 30 DAY) THEN impressions ELSE 0 END) AS impressions_avant,
          SUM(CASE WHEN date < DATE('{date_correction.date()}') AND date >= DATE_SUB(DATE('{date_correction.date()}'), INTERVAL 30 DAY) THEN clics ELSE 0 END) AS clics_avant,
          AVG(CASE WHEN date < DATE('{date_correction.date()}') AND date >= DATE_SUB(DATE('{date_correction.date()}'), INTERVAL 30 DAY) THEN position END) AS position_avant,
          SUM(CASE WHEN date >= DATE('{date_correction.date()}') THEN impressions ELSE 0 END) AS impressions_apres,
          SUM(CASE WHEN date >= DATE('{date_correction.date()}') THEN clics ELSE 0 END) AS clics_apres,
          AVG(CASE WHEN date >= DATE('{date_correction.date()}') THEN position END) AS position_apres
        FROM `{PROJECT_ID}.01_raw.gsc_queries`
        WHERE LOWER(REGEXP_REPLACE(REGEXP_REPLACE(page, r'^https?://(www\.)?', ''), r'/$', '')) = '{url_norm}'
        """
        try:
            df_m = client_bq.query(query_metriques).to_dataframe()
        except Exception as e:
            continue

        if df_m.empty:
            continue

        r = df_m.iloc[0]
        imp_avant = int(r['impressions_avant']) if pd.notna(r['impressions_avant']) else 0
        clics_avant = int(r['clics_avant']) if pd.notna(r['clics_avant']) else 0
        pos_avant = float(r['position_avant']) if pd.notna(r['position_avant']) else None
        imp_apres = int(r['impressions_apres']) if pd.notna(r['impressions_apres']) else 0
        clics_apres = int(r['clics_apres']) if pd.notna(r['clics_apres']) else 0
        pos_apres = float(r['position_apres']) if pd.notna(r['position_apres']) else None

        ctr_avant = (clics_avant / imp_avant) if imp_avant > 0 else None
        ctr_apres = (clics_apres / imp_apres) if imp_apres > 0 else None

        if jours_ecoules < 7 or imp_apres < 10:
            verdict = "donnees_insuffisantes"
            commentaire = f"{jours_ecoules}j ecoules, {imp_apres} impressions apres -- attendre davantage avant de conclure"
        elif ctr_avant is not None and ctr_apres is not None:
            if ctr_apres > ctr_avant * 1.1:
                verdict = "amelioration"
                commentaire = f"CTR {ctr_avant*100:.1f}% -> {ctr_apres*100:.1f}%"
            elif ctr_apres < ctr_avant * 0.9:
                verdict = "degradation"
                commentaire = f"CTR {ctr_avant*100:.1f}% -> {ctr_apres*100:.1f}%"
            else:
                verdict = "stable"
                commentaire = f"CTR {ctr_avant*100:.1f}% -> {ctr_apres*100:.1f}% (variation faible)"
        else:
            verdict = "donnees_insuffisantes"
            commentaire = "CTR non calculable (0 impression sur une des periodes)"

        lignes.append({
            "brief_id": brief_id, "post_id": post_id,
            "date_evaluation": datetime.now().isoformat(),
            "jours_depuis_correction": jours_ecoules,
            "impressions_avant": imp_avant, "clics_avant": clics_avant,
            "ctr_avant": ctr_avant, "position_avant": pos_avant,
            "impressions_apres": imp_apres, "clics_apres": clics_apres,
            "ctr_apres": ctr_apres, "position_apres": pos_apres,
            "verdict": verdict, "commentaire": commentaire,
        })

    if not lignes:
        print("  Aucune evaluation generee")
        return 0

    try:
        errors = client_bq.insert_rows_json(
            f"{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations", lignes
        )
        if errors:
            print(f"  Erreurs insertion : {errors}")
            return 0
    except Exception as e:
        print(f"  Erreur ecriture BigQuery : {e}")
        return 0

    print(f"  {len(lignes)} evaluations enregistrees")
    return len(lignes)


def agent_orcaas_chat(question, client_bq):
    """AGENT ORCAAS -- Interface de conversation (couche 3). Repond a une
    question en langage libre, en s'appuyant EXCLUSIVEMENT sur le contexte
    reel du projet (briefs passes, evaluations d'impact, etat actuel du
    tunnel de conversion) -- jamais en inventant une donnee absente."""
    try:
        total_briefs = client_bq.query(f"""
            SELECT COUNT(*) AS total, COUNTIF(statut='corrige') AS corriges, COUNTIF(statut='echec') AS echecs
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs`
        """).to_dataframe().iloc[0]

        df_briefs = client_bq.query(f"""
            SELECT date_execution, stack, url, probleme_detecte, statut
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs`
            ORDER BY date_execution DESC LIMIT 20
        """).to_dataframe()

        total_evals = client_bq.query(f"""
            SELECT COUNT(*) AS total, verdict FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
            GROUP BY verdict
        """).to_dataframe()

        df_evals = client_bq.query(f"""
            SELECT post_id, verdict, commentaire, jours_depuis_correction
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
            ORDER BY date_evaluation DESC LIMIT 20
        """).to_dataframe()

        df_tunnel = client_bq.query(f"""
            SELECT url, impressions, clics, position_moyenne, sessions, bounce_rate_pct, nb_leads
            FROM `{PROJECT_ID}.04_pipeline_seo.tunnel_conversion_unifie`
            WHERE impressions > 0
            ORDER BY impressions DESC LIMIT 15
        """).to_dataframe()
    except Exception as e:
        return f"Erreur lors de la recuperation du contexte reel : {e}"

    contexte = (
        f"TOTAL REEL DE CORRECTIONS EFFECTUEES DEPUIS LE DEBUT : {int(total_briefs['total'])} "
        f"({int(total_briefs['corriges'])} reussies, {int(total_briefs['echecs'])} echouees) -- "
        "IMPORTANT : le detail ci-dessous ne montre QUE les 20 plus recentes, pas la totalite. "
        "Utilise TOUJOURS ce total reel dans ta reponse, jamais le nombre de lignes du detail.\n\n"
        "DERNIERS BRIEFS (echantillon des 20 plus recents, PAS le total) :\n"
        f"{df_briefs.to_string(index=False) if not df_briefs.empty else 'Aucun'}\n\n"
        "REPARTITION DES EVALUATIONS PAR VERDICT (TOTAL REEL) :\n"
        f"{total_evals.to_string(index=False) if not total_evals.empty else 'Aucune evaluation'}\n\n"
        "DERNIERES EVALUATIONS D'IMPACT (echantillon des 20 plus recentes) :\n"
        f"{df_evals.to_string(index=False) if not df_evals.empty else 'Aucune'}\n\n"
        "TOP 15 PAGES PAR IMPRESSIONS (tunnel de conversion) :\n"
        f"{df_tunnel.to_string(index=False) if not df_tunnel.empty else 'Aucune'}"
    )

    prompt = (
        "Tu es ORCAAS, l'agent IA SEO qui gere le site comprendre-mon-energie.fr, "
        "avec 3 competences : technique, analytique, commercial. Tu es rigoureux, "
        "honnete (tu ne fabriques jamais de donnee ni de chiffre), et tu t'appuies "
        "UNIQUEMENT sur le contexte reel fourni ci-dessous. IMPORTANT : reponds "
        "TOUJOURS dans la meme langue que la question posee, quelle que soit la "
        "langue de ce contexte ou de ces instructions.\n\n"
        f"CONTEXTE REEL DU PROJET :\n{contexte}\n\n"
        f"QUESTION DU PORTEUR DE PROJET (reponds dans la meme langue que cette "
        f"question precise, meme si tout ce qui precede est en francais) :\n{question}\n\n"
        "Reponds de facon claire et concrete, en t'appuyant EXCLUSIVEMENT sur les "
        "donnees ci-dessus. Si tu n'as pas l'information pour repondre precisement, "
        "dis-le clairement plutot que d'inventer."
    )

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": CONFIG['ANTHROPIC_API_KEY'], "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": CONFIG['MODEL'], "max_tokens": 800, "messages": [{"role": "user", "content": prompt}]},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()['content'][0]['text']
    except Exception as e:
        return f"Erreur lors de la generation de la reponse : {e}"


def _dash_top_pages(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT page AS url, SUM(impressions) AS impressions, SUM(clics) AS clics, AVG(position) AS position_moyenne
            FROM `{PROJECT_ID}.01_raw.gsc_queries`
            WHERE date BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY page ORDER BY impressions DESC LIMIT 10
        """).to_dataframe()
        liste = []
        for _, r in df.iterrows():
            url_courte = r['url'].replace('https://www.comprendre-mon-energie.fr', '') if r['url'] else ''
            liste.append({
                "url": url_courte if url_courte else "/",
                "impressions": int(r['impressions']) if pd.notna(r['impressions']) else 0,
                "clics": int(r['clics']) if pd.notna(r['clics']) else 0,
                "position": round(float(r['position_moyenne']), 1) if pd.notna(r['position_moyenne']) else None,
            })
        return ("top_pages", liste, None)
    except Exception as e:
        return ("top_pages", [], f"top_pages: {e}")


def _dash_briefs(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT probleme_detecte, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs`
            WHERE DATE(date_execution) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY probleme_detecte ORDER BY nb DESC
        """).to_dataframe()
        liste = [{"probleme": r['probleme_detecte'], "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("briefs_par_probleme", liste, None)
    except Exception as e:
        return ("briefs_par_probleme", [], f"briefs: {e}")


def _dash_evals(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT verdict, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
            WHERE DATE(date_evaluation) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY verdict ORDER BY nb DESC
        """).to_dataframe()
        liste = [{"verdict": r['verdict'], "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("evaluations_par_verdict", liste, None)
    except Exception as e:
        return ("evaluations_par_verdict", [], f"evals: {e}")


def _dash_opportunites(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT url, MAX(score_opportunite) AS score_opportunite, MIN(position) AS position
            FROM `{PROJECT_ID}.03_final.seo_opportunities`
            GROUP BY url ORDER BY score_opportunite DESC LIMIT 10
        """).to_dataframe()
        liste = []
        for _, r in df.iterrows():
            url_courte = r['url'].replace('https://www.comprendre-mon-energie.fr', '') if r['url'] else ''
            liste.append({
                "url": url_courte if url_courte else "/",
                "score": round(float(r['score_opportunite']), 1) if pd.notna(r['score_opportunite']) else 0,
                "position": round(float(r['position']), 1) if pd.notna(r['position']) else None,
            })
        return ("opportunites", liste, None)
    except Exception as e:
        return ("opportunites", [], f"opportunites: {e}")


def _dash_rankmath(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT COUNTIF(rank_math_focus_keyword IS NOT NULL) AS avec, COUNTIF(rank_math_focus_keyword IS NULL) AS sans
            FROM `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data`
        """).to_dataframe()
        if df.empty:
            return ("rankmath_couverture", {"avec_mot_cle": 0, "sans_mot_cle": 0}, None)
        valeur = {
            "avec_mot_cle": int(df.iloc[0]['avec']) if pd.notna(df.iloc[0]['avec']) else 0,
            "sans_mot_cle": int(df.iloc[0]['sans']) if pd.notna(df.iloc[0]['sans']) else 0,
        }
        return ("rankmath_couverture", valeur, None)
    except Exception as e:
        return ("rankmath_couverture", {"avec_mot_cle": 0, "sans_mot_cle": 0}, f"rankmath: {e}")


def _dash_audit(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT
              CASE WHEN status_code = 200 THEN '200 OK'
                   WHEN status_code >= 300 AND status_code < 400 THEN 'Redirection'
                   WHEN status_code >= 400 THEN 'Erreur'
                   ELSE 'Autre' END AS categorie,
              COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.audit_technique_site`
            GROUP BY categorie
        """).to_dataframe()
        liste = [{"categorie": r['categorie'], "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("audit_technique", liste, None)
    except Exception as e:
        return ("audit_technique", [], f"audit: {e}")


def _dash_leads(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT tool, COUNT(*) AS nb FROM (
              SELECT tool, timestamp AS date_lead FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
              UNION ALL
              SELECT tool, derniere_maj AS date_lead FROM `{PROJECT_ID}.04_pipeline_seo.leads_app_authentifies`
            )
            WHERE DATE(date_lead) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY tool ORDER BY nb DESC
        """).to_dataframe()
        liste = [{"outil": r['tool'], "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("leads_par_outil", liste, None)
    except Exception as e:
        return ("leads_par_outil", [], f"leads: {e}")


def _dash_publications(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT silo, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
            WHERE DATE(date_publication) BETWEEN '{date_debut}' AND '{date_fin}'
            GROUP BY silo ORDER BY nb DESC
        """).to_dataframe()
        liste = [{"silo": r['silo'], "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("publications_par_silo", liste, None)
    except Exception as e:
        return ("publications_par_silo", [], f"publications: {e}")


def _dash_indexation(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT coverage_state, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.indexation_google`
            GROUP BY coverage_state ORDER BY nb DESC
        """).to_dataframe()
        liste = [{"etat": r['coverage_state'] or 'Non verifie', "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("indexation", liste, None)
    except Exception as e:
        return ("indexation", [], f"indexation: {e}")


def agent_orcaas_donnees_dashboard(client_bq, date_debut=None, date_fin=None):
    """AGENT ORCAAS -- Prepare les donnees reelles du dashboard (couche
    Dashboard/Data Analytics). Filtrable par date (date_debut/date_fin,
    format AAAA-MM-JJ). Les 8 requetes s'executent EN PARALLELE
    (ThreadPoolExecutor) plutot qu'en serie -- chaque requete BigQuery a un
    cout de demarrage fixe (1-3s), qui s'additionnait auparavant (dizaines
    de secondes constatees en usage reel). En parallele, le temps total
    approche celui de la requete la plus lente, pas leur somme."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if not date_debut:
        date_debut = (datetime.now().date() - timedelta(days=30)).isoformat()
    if not date_fin:
        date_fin = datetime.now().date().isoformat()

    resultat = {
        "date_debut": date_debut, "date_fin": date_fin,
        "top_pages": [], "briefs_par_probleme": [], "evaluations_par_verdict": [],
        "opportunites": [], "rankmath_couverture": {"avec_mot_cle": 0, "sans_mot_cle": 0},
        "audit_technique": [], "leads_par_outil": [], "publications_par_silo": [],
        "indexation": [],
        "erreur": None,
    }

    taches = [_dash_top_pages, _dash_briefs, _dash_evals, _dash_opportunites,
              _dash_rankmath, _dash_audit, _dash_leads, _dash_publications,
              _dash_indexation]

    erreurs = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(t, client_bq, date_debut, date_fin) for t in taches]
        for future in as_completed(futures):
            try:
                cle, valeur, erreur = future.result()
                resultat[cle] = valeur
                if erreur:
                    erreurs.append(erreur)
            except Exception as e:
                erreurs.append(f"tache: {e}")

    if erreurs:
        resultat["erreur"] = " | ".join(erreurs)

    return resultat


def agent_orcaas_monitoring_pipeline(client_bq, date_cible=None):
    """AGENT ORCAAS -- Stack Monitoring du pipeline (nouvelle, ajoutee le
    02/09/2026 suite a un incident reel : deux executions concurrentes du
    pipeline principal ont produit 7 paires d'articles sur le meme sujet,
    avec des titres legerement differents -- une comparaison de texte simple
    ne les aurait pas detectees. Utilise Claude pour juger la similarite
    semantique entre articles publies le meme jour dans le meme silo.
    Controle total : supprime automatiquement le plus recent de chaque
    paire confirmee (WordPress + BigQuery), genere un brief par
    intervention."""
    print("AGENT ORCAAS -- Monitoring du pipeline...")

    if not date_cible:
        date_cible = datetime.now().date().isoformat()

    try:
        df = client_bq.query(f"""
            SELECT post_id, silo, titre, date_publication
            FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
            WHERE DATE(date_publication) = '{date_cible}'
            ORDER BY silo, date_publication
        """).to_dataframe()
    except Exception as e:
        print(f"  Erreur lecture historique_publications : {e}")
        return {"paires_analysees": 0, "doublons_supprimes": 0}

    if len(df) < 2:
        print("  Moins de 2 articles ce jour, rien a analyser")
        return {"paires_analysees": 0, "doublons_supprimes": 0}

    import io
    import paramiko
    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname="109.234.167.170", port=22, username="jolu5920", pkey=pkey, timeout=15)
    except Exception as e:
        print(f"  Erreur connexion SSH : {e}")
        return {"paires_analysees": 0, "doublons_supprimes": 0}

    wp_path = "/home/jolu5920/public_html/comprendre-mon-energie.com"
    briefs = []
    supprimes = 0
    deja_traites = set()

    for silo in df['silo'].unique():
        sous_df = df[df['silo'] == silo].reset_index(drop=True)
        for i in range(len(sous_df)):
            id_a = int(sous_df.iloc[i]['post_id'])
            if id_a in deja_traites:
                continue
            for j in range(i + 1, len(sous_df)):
                id_b = int(sous_df.iloc[j]['post_id'])
                if id_b in deja_traites:
                    continue
                titre_a = sous_df.iloc[i]['titre']
                titre_b = sous_df.iloc[j]['titre']

                prompt = (
                    "Ces deux titres d'articles, publies le meme jour dans le meme silo "
                    "thematique, traitent-ils du MEME sujet exact (un vrai doublon de "
                    "contenu, pas juste une thematique proche) ?\n"
                    f"Titre A : {titre_a}\n"
                    f"Titre B : {titre_b}\n"
                    'Reponds UNIQUEMENT en JSON strict, rien d\'autre : {"meme_sujet": true}'
                    ' ou {"meme_sujet": false}'
                )
                meme_sujet = False
                try:
                    resp = requests.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": CONFIG['ANTHROPIC_API_KEY'], "anthropic-version": "2023-06-01", "content-type": "application/json"},
                        json={"model": CONFIG['MODEL'], "max_tokens": 50, "messages": [{"role": "user", "content": prompt}]},
                        timeout=20
                    )
                    resp.raise_for_status()
                    texte = resp.json()['content'][0]['text']
                    texte_json = texte[texte.find('{'):texte.rfind('}') + 1]
                    jugement = json.loads(texte_json)
                    meme_sujet = bool(jugement.get('meme_sujet', False))
                except Exception:
                    meme_sujet = False

                if not meme_sujet:
                    continue

                deja_traites.add(id_b)
                statut = "echec"
                erreur = None
                try:
                    cmd = f'wp --path="{wp_path}" post delete {id_b} --force'
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    sortie = stdout.read().decode()
                    if "Success" in sortie:
                        client_bq.query(
                            f"DELETE FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications` WHERE post_id = {id_b}"
                        ).result()
                        statut = "corrige"
                        supprimes += 1
                    else:
                        erreur = sortie[:200]
                except Exception as e:
                    erreur = str(e)[:200]

                briefs.append({
                    "brief_id": f"{id_b}_{int(datetime.now().timestamp())}",
                    "date_execution": datetime.now().isoformat(),
                    "stack": "monitoring_pipeline", "post_id": id_b, "url": "",
                    "probleme_detecte": f"doublon_sujet (conserve {id_a} : {titre_a[:60]})",
                    "valeur_avant": titre_b, "valeur_apres": "Article supprime (WordPress + BigQuery)",
                    "statut": statut, "erreur": erreur,
                })
                break

    ssh.close()

    if briefs:
        try:
            client_bq.insert_rows_json(f"{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs", briefs)
        except Exception as e:
            print(f"  Erreur ecriture briefs : {e}")

    print(f"  {len(briefs)} paire(s) confirmee(s), {supprimes} suppression(s) reussie(s)")
    return {"paires_analysees": len(briefs), "doublons_supprimes": supprimes}


def synchroniser_indexation(client_bq, limite=None):
    """CHANTIER INDEXATION : verifie pour chaque page connue si Google l'a
    reellement indexee (URL Inspection API de Search Console). limite
    (optionnel) : ne traite que les N premieres pages, utile pour tester
    le comportement/la vitesse reelle de l'API avant de lancer sur
    l'ensemble du site."""
    print(f"SYNCHRONISATION INDEXATION GOOGLE (limite={limite})...")

    from google.oauth2 import service_account
    import google.auth.transport.requests

    try:
        cle = os.environ.get("SA_GTM_PRIVATE_KEY", "")
        creds = service_account.Credentials.from_service_account_info(
            json.loads(cle),
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        creds.refresh(google.auth.transport.requests.Request())
    except Exception as e:
        print(f"  Erreur authentification : {e}")
        return 0

    try:
        query = f"SELECT post_id, url FROM `{PROJECT_ID}.02_cleaned.wp_url_mapping`"
        df = client_bq.query(query).to_dataframe()
    except Exception as e:
        print(f"  Erreur lecture wp_url_mapping : {e}")
        return 0

    if limite:
        df = df.head(int(limite))

    debut_chrono = datetime.now()
    lignes = []
    for i, (_, row) in enumerate(df.iterrows()):
        post_id = int(row['post_id'])
        url = row['url']
        entree = {
            "post_id": post_id, "url": url,
            "coverage_state": None, "verdict": None, "robots_txt_state": None,
            "indexing_state": None, "page_fetch_state": None,
            "last_crawl_time": None, "crawled_as": None,
            "erreur": None, "checked_at": datetime.now().isoformat(),
        }
        try:
            body = {"inspectionUrl": url, "siteUrl": "https://www.comprendre-mon-energie.fr/"}
            r = requests.post(
                "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
                json=body, timeout=10
            )
            if r.status_code == 200:
                result = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
                entree["coverage_state"] = result.get("coverageState")
                entree["verdict"] = result.get("verdict")
                entree["robots_txt_state"] = result.get("robotsTxtState")
                entree["indexing_state"] = result.get("indexingState")
                entree["page_fetch_state"] = result.get("pageFetchState")
                entree["last_crawl_time"] = result.get("lastCrawlTime")
                entree["crawled_as"] = result.get("crawledAs")
            else:
                entree["erreur"] = f"HTTP {r.status_code}: {r.text[:150]}"
        except Exception as e:
            entree["erreur"] = str(e)[:200]

        lignes.append(entree)

        if (i + 1) % 20 == 0:
            ecoule = (datetime.now() - debut_chrono).total_seconds()
            print(f"  Progression : {i + 1}/{len(df)} pages traitees ({ecoule:.0f}s ecoulees)")

    if not lignes:
        print("  Aucune page a verifier")
        return 0

    try:
        table_ref = f"{PROJECT_ID}.04_pipeline_seo.indexation_google"
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            schema=[
                bigquery.SchemaField("post_id", "INTEGER"),
                bigquery.SchemaField("url", "STRING"),
                bigquery.SchemaField("coverage_state", "STRING"),
                bigquery.SchemaField("verdict", "STRING"),
                bigquery.SchemaField("robots_txt_state", "STRING"),
                bigquery.SchemaField("indexing_state", "STRING"),
                bigquery.SchemaField("page_fetch_state", "STRING"),
                bigquery.SchemaField("last_crawl_time", "TIMESTAMP"),
                bigquery.SchemaField("crawled_as", "STRING"),
                bigquery.SchemaField("erreur", "STRING"),
                bigquery.SchemaField("checked_at", "TIMESTAMP"),
            ],
        )
        load_job = client_bq.load_table_from_json(lignes, table_ref, job_config=job_config)
        load_job.result()
        print(f"  {len(lignes)} pages verifiees")
    except Exception as e:
        print(f"  Erreur ecriture BigQuery : {e}")
        return 0

    return len(lignes)


def agent_orcaas_detail_categorie(client_bq, graphique, categorie):
    """AGENT ORCAAS -- Detail cliquable du dashboard. Retourne la liste des
    elements individuels derriere une categorie agregee d'un graphique
    (ex: les 18 URLs derriere 'URL is unknown to Google'). Transparence
    uniquement -- la correction reste du ressort d'ORCAAS lui-meme."""
    try:
        if graphique == "indexation":
            job_config = bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("categorie", "STRING", categorie)])
            df = client_bq.query(f"""
                SELECT url, verdict FROM `{PROJECT_ID}.04_pipeline_seo.indexation_google`
                WHERE coverage_state = @categorie ORDER BY url
            """, job_config=job_config).to_dataframe()
            items = [{"url": r['url'], "detail": r['verdict'] or ''} for _, r in df.iterrows()]

        elif graphique == "audit_technique":
            if categorie == "200 OK":
                condition = "status_code = 200"
            elif categorie == "Redirection":
                condition = "status_code >= 300 AND status_code < 400"
            elif categorie == "Erreur":
                condition = "status_code >= 400"
            else:
                condition = "status_code IS NULL"
            df = client_bq.query(f"""
                SELECT url, status_code FROM `{PROJECT_ID}.04_pipeline_seo.audit_technique_site`
                WHERE {condition} ORDER BY url
            """).to_dataframe()
            items = [{"url": r['url'], "detail": f"Code {int(r['status_code'])}" if pd.notna(r['status_code']) else "N/A"} for _, r in df.iterrows()]

        elif graphique == "briefs":
            job_config = bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("categorie", "STRING", categorie)])
            df = client_bq.query(f"""
                SELECT url, post_id, date_execution, statut FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs`
                WHERE probleme_detecte = @categorie ORDER BY date_execution DESC LIMIT 200
            """, job_config=job_config).to_dataframe()
            items = [{"url": r['url'] or f"post {r['post_id']}", "detail": r['statut'] or ''} for _, r in df.iterrows()]

        elif graphique == "evaluations":
            job_config = bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("categorie", "STRING", categorie)])
            df = client_bq.query(f"""
                SELECT post_id, commentaire FROM `{PROJECT_ID}.04_pipeline_seo.agent_orcaas_evaluations`
                WHERE verdict = @categorie ORDER BY date_evaluation DESC LIMIT 200
            """, job_config=job_config).to_dataframe()
            items = [{"url": f"post {int(r['post_id'])}", "detail": r['commentaire'] or ''} for _, r in df.iterrows()]

        elif graphique == "leads":
            job_config = bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("categorie", "STRING", categorie)])
            df = client_bq.query(f"""
                SELECT CAST(source_post_id AS STRING) AS post_id, CAST(timestamp AS STRING) AS quand
                FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis` WHERE tool = @categorie
                UNION ALL
                SELECT CAST(source_post_id AS STRING) AS post_id, CAST(derniere_maj AS STRING) AS quand
                FROM `{PROJECT_ID}.04_pipeline_seo.leads_app_authentifies` WHERE tool = @categorie
                ORDER BY quand DESC LIMIT 200
            """, job_config=job_config).to_dataframe()
            items = [{"url": f"post {r['post_id']}", "detail": r['quand'] or ''} for _, r in df.iterrows()]

        elif graphique == "publications":
            job_config = bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("categorie", "STRING", categorie)])
            df = client_bq.query(f"""
                SELECT titre, CAST(date_publication AS STRING) AS quand
                FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
                WHERE silo = @categorie ORDER BY date_publication DESC LIMIT 200
            """, job_config=job_config).to_dataframe()
            items = [{"url": r['titre'], "detail": r['quand'] or ''} for _, r in df.iterrows()]

        elif graphique == "rankmath":
            condition = "rank_math_focus_keyword IS NOT NULL" if "avec" in categorie.lower() else "rank_math_focus_keyword IS NULL"
            df = client_bq.query(f"""
                SELECT r.post_id, m.url FROM `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data` r
                JOIN `{PROJECT_ID}.02_cleaned.wp_url_mapping` m ON m.post_id = r.post_id
                WHERE {condition} ORDER BY m.url LIMIT 200
            """).to_dataframe()
            items = [{"url": r['url'], "detail": ""} for _, r in df.iterrows()]

        else:
            return {"items": [], "erreur": f"Graphique inconnu : {graphique}"}

        return {"items": items, "erreur": None}
    except Exception as e:
        return {"items": [], "erreur": str(e)}


def agent_orcaas_analyser_chevauchement(client_bq):
    """AGENT ORCAAS -- Stack Contenu editorial, etape 1 (detection).
    Pour chaque page 'Crawled - currently not indexed', identifie les pages
    soeurs du meme sous-silo (meme prefixe d'URL) deja indexees, et utilise
    Claude pour juger s'il y a un chevauchement thematique reel. Lecture
    seule, aucune ecriture."""
    print("AGENT ORCAAS -- Analyse chevauchement editorial...")

    try:
        df_probleme = client_bq.query(f"""
            SELECT ig.url, wm.post_id, r.rank_math_title
            FROM `{PROJECT_ID}.04_pipeline_seo.indexation_google` ig
            JOIN `{PROJECT_ID}.02_cleaned.wp_url_mapping` wm ON wm.url = ig.url
            LEFT JOIN `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data` r ON r.post_id = wm.post_id
            WHERE ig.coverage_state = 'Crawled - currently not indexed'
        """).to_dataframe()
    except Exception as e:
        print(f"  Erreur lecture pages problematiques : {e}")
        return []

    if df_probleme.empty:
        print("  Aucune page a analyser")
        return []

    resultats = []
    for _, row in df_probleme.iterrows():
        url = row['url']
        post_id = int(row['post_id'])
        titre_actuel = row['rank_math_title'] or url

        parts = url.rstrip('/').rsplit('/', 1)
        prefixe_sous_silo = parts[0] + '/' if len(parts) > 1 else url

        try:
            df_soeurs = client_bq.query(f"""
                SELECT ig.url, r.rank_math_title
                FROM `{PROJECT_ID}.04_pipeline_seo.indexation_google` ig
                JOIN `{PROJECT_ID}.02_cleaned.wp_url_mapping` wm ON wm.url = ig.url
                LEFT JOIN `{PROJECT_ID}.04_pipeline_seo.rankmath_seo_data` r ON r.post_id = wm.post_id
                WHERE STARTS_WITH(ig.url, '{prefixe_sous_silo}') AND ig.url != '{url}'
                  AND ig.coverage_state = 'Submitted and indexed'
                LIMIT 8
            """).to_dataframe()
        except Exception as e:
            resultats.append({"post_id": post_id, "url": url, "classification": "erreur", "raison": str(e)[:150]})
            continue

        if df_soeurs.empty:
            resultats.append({"post_id": post_id, "url": url, "titre": titre_actuel,
                               "classification": "isole", "raison": "aucune page soeur indexee dans le sous-silo"})
            continue

        titres_soeurs = [r['rank_math_title'] or r['url'] for _, r in df_soeurs.iterrows()]
        prompt = (
            "Un article n'est pas pleinement indexe par Google alors que des articles "
            "TRES PROCHES du meme sous-theme le sont deja. Y a-t-il un chevauchement "
            "thematique reel qui expliquerait ca (sujets quasi-identiques), ou ces "
            "articles couvrent-ils des angles genuinement distincts ?\n"
            f"Article non indexe : {titre_actuel}\n"
            f"Articles voisins deja indexes : {', '.join(titres_soeurs)}\n"
            'Reponds UNIQUEMENT en JSON strict : {"chevauchement": true, "raison": "..."} '
            'ou {"chevauchement": false, "raison": "..."}'
        )
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CONFIG['ANTHROPIC_API_KEY'], "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": CONFIG['MODEL'], "max_tokens": 200, "messages": [{"role": "user", "content": prompt}]},
                timeout=20
            )
            resp.raise_for_status()
            texte = resp.json()['content'][0]['text']
            texte_json = texte[texte.find('{'):texte.rfind('}') + 1]
            jugement = json.loads(texte_json)
            chevauchement = bool(jugement.get('chevauchement', False))
            raison = jugement.get('raison', '')
        except Exception as e:
            resultats.append({"post_id": post_id, "url": url, "titre": titre_actuel,
                               "classification": "erreur", "raison": f"IA: {str(e)[:150]}"})
            continue

        resultats.append({
            "post_id": post_id, "url": url, "titre": titre_actuel,
            "classification": "chevauchement" if chevauchement else "isole",
            "raison": raison, "pages_soeurs": titres_soeurs[:3],
        })

    print(f"  {len(resultats)} page(s) analysee(s)")
    return resultats


def agent_orcaas_differencier_contenu(client_bq):
    """AGENT ORCAAS -- Stack Contenu editorial, etape 2 (differenciation).
    Pour chaque page classee 'chevauchement' par l'etape 1, recupere le
    contenu actuel et demande a Claude de resserrer l'angle pour le rendre
    genuinement distinct des pages soeurs deja indexees. Reecrit titre,
    meta ET corps de l'article. Garde-fous : contenu genere pas trop court
    (>= 50% de l'original), aucune annee perimee introduite."""
    print("AGENT ORCAAS -- Differenciation contenu editorial...")

    analyses = agent_orcaas_analyser_chevauchement(client_bq)
    a_traiter = [a for a in analyses if a.get('classification') == 'chevauchement']

    if not a_traiter:
        print("  Aucune page en chevauchement a traiter")
        return {"traitees": 0, "reussies": 0}

    import io
    import paramiko
    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname="109.234.167.170", port=22, username="jolu5920", pkey=pkey, timeout=15)
    except Exception as e:
        print(f"  Erreur connexion SSH : {e}")
        return {"traitees": 0, "reussies": 0}

    wp_path = "/home/jolu5920/public_html/comprendre-mon-energie.com"
    annee_actuelle = datetime.now().year
    annees_perimees = [str(y) for y in range(2020, annee_actuelle)]
    briefs = []
    reussies = 0

    for item in a_traiter:
        post_id = item['post_id']
        url = item['url']
        titre_actuel = item['titre']
        raison = item.get('raison', '')
        soeurs = item.get('pages_soeurs', [])
        erreur_finale = None
        statut = "echec"
        nouveau_titre = titre_actuel

        try:
            stdin, stdout, stderr = ssh.exec_command(
                f'wp --path="{wp_path}" post get {int(post_id)} --field=content'
            )
            contenu_actuel = stdout.read().decode()
            if not contenu_actuel:
                raise Exception((stderr.read().decode() or "contenu vide")[:150])
        except Exception as e:
            briefs.append({
                "brief_id": f"{post_id}_{int(datetime.now().timestamp())}",
                "date_execution": datetime.now().isoformat(),
                "stack": "contenu_editorial", "post_id": post_id, "url": url,
                "probleme_detecte": f"chevauchement_thematique: {raison[:100]}",
                "valeur_avant": titre_actuel, "valeur_apres": "",
                "statut": "echec", "erreur": f"lecture: {str(e)[:150]}",
            })
            continue

        prompt = (
            "Tu es un redacteur SEO expert. Cet article n'est pas pleinement indexe "
            "par Google car il chevauche trop avec des articles voisins deja indexes "
            "du meme site.\n"
            f"PROBLEME IDENTIFIE : {raison}\n"
            f"ARTICLES VOISINS DEJA INDEXES (evite de refaire leur travail) : {', '.join(soeurs)}\n\n"
            f"TITRE ACTUEL : {titre_actuel}\n"
            f"CONTENU ACTUEL (HTML) :\n{contenu_actuel[:12000]}\n\n"
            "Reecris ce contenu pour lui donner un ANGLE GENUINEMENT DISTINCT des "
            "articles voisins -- pas une reformulation generique, un vrai angle "
            "different (cas pratique specifique, public cible different, aspect "
            "technique non couvert ailleurs). Garde le format HTML, garde les "
            "informations factuelles exactes (ne change aucun chiffre, montant ou "
            "condition legale), garde une longueur similaire a l'original. Genere "
            "aussi un nouveau titre SEO (50-60 caracteres) et une nouvelle meta "
            "description (140-160 caracteres) refletant ce nouvel angle. N'utilise "
            "JAMAIS une annee anterieure a " + str(annee_actuelle) + ".\n\n"
            'Reponds UNIQUEMENT en JSON strict : {"titre": "...", "meta": "...", "contenu": "..."}'
        )

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CONFIG['ANTHROPIC_API_KEY'], "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": CONFIG['MODEL'], "max_tokens": 8000, "messages": [{"role": "user", "content": prompt}]},
                timeout=90
            )
            resp.raise_for_status()
            texte = resp.json()['content'][0]['text']
            texte_json = texte[texte.find('{'):texte.rfind('}') + 1]
            resultat = json.loads(texte_json)
            nouveau_titre = resultat.get('titre', titre_actuel)
            nouvelle_meta = resultat.get('meta', '')
            nouveau_contenu = resultat.get('contenu', '')
        except Exception as e:
            briefs.append({
                "brief_id": f"{post_id}_{int(datetime.now().timestamp())}",
                "date_execution": datetime.now().isoformat(),
                "stack": "contenu_editorial", "post_id": post_id, "url": url,
                "probleme_detecte": f"chevauchement_thematique: {raison[:100]}",
                "valeur_avant": titre_actuel, "valeur_apres": "",
                "statut": "echec", "erreur": f"IA: {str(e)[:150]}",
            })
            continue

        if len(nouveau_contenu) < len(contenu_actuel) * 0.5:
            erreur_finale = "garde-fou: contenu genere trop court (< 50% de l'original)"
        elif any(a in nouveau_titre or a in nouvelle_meta for a in annees_perimees):
            erreur_finale = "garde-fou: annee perimee detectee dans titre/meta"

        if erreur_finale:
            briefs.append({
                "brief_id": f"{post_id}_{int(datetime.now().timestamp())}",
                "date_execution": datetime.now().isoformat(),
                "stack": "contenu_editorial", "post_id": post_id, "url": url,
                "probleme_detecte": f"chevauchement_thematique: {raison[:100]}",
                "valeur_avant": titre_actuel, "valeur_apres": "",
                "statut": "echec", "erreur": erreur_finale,
            })
            continue

        try:
            sftp = ssh.open_sftp()
            chemin_temp = f"/tmp/orcaas_contenu_{post_id}.html"
            with sftp.open(chemin_temp, 'w') as f:
                f.write(nouveau_contenu)
            sftp.close()

            titre_echap = nouveau_titre.replace('"', '\\"')
            meta_echap = nouvelle_meta.replace('"', '\\"')
            cmd = (
                f'wp --path="{wp_path}" post update {post_id} --post_content="$(cat {chemin_temp})" && '
                f'wp --path="{wp_path}" post meta update {post_id} rank_math_title "{titre_echap}" && '
                f'wp --path="{wp_path}" post meta update {post_id} rank_math_description "{meta_echap}" && '
                f'rm {chemin_temp}'
            )
            stdin, stdout, stderr = ssh.exec_command(cmd)
            sortie = stdout.read().decode()
            erreur_ecriture = stderr.read().decode()
            if "Success" in sortie:
                statut = "corrige"
                reussies += 1
            else:
                erreur_finale = (erreur_ecriture[:200] or "ecriture non confirmee")
        except Exception as e:
            erreur_finale = str(e)[:200]

        briefs.append({
            "brief_id": f"{post_id}_{int(datetime.now().timestamp())}",
            "date_execution": datetime.now().isoformat(),
            "stack": "contenu_editorial", "post_id": post_id, "url": url,
            "probleme_detecte": f"chevauchement_thematique: {raison[:100]}",
            "valeur_avant": titre_actuel,
            "valeur_apres": nouveau_titre if statut == "corrige" else "",
            "statut": statut, "erreur": erreur_finale,
        })

    ssh.close()

    if briefs:
        try:
            client_bq.insert_rows_json(f"{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs", briefs)
        except Exception as e:
            print(f"  Erreur ecriture briefs : {e}")

    print(f"  {len(briefs)} page(s) traitee(s), {reussies} reussie(s)")
    return {"traitees": len(briefs), "reussies": reussies}


def rafraichir_indicateurs_reglementaires(client_bq):
    """Recupere les dernieres valeurs officielles connues (CRE Gaz/Elec,
    ANAH Aides) depuis les sources officielles et les insere dans
    indicateurs_reglementaires. Concu pour tourner periodiquement
    (hebdomadaire via Cloud Scheduler), independamment du run de redaction —
    sans ce rafraichissement, les donnees injectees dans les articles
    deviendraient obsoletes avec le temps."""
    import io
    from datetime import datetime as dt
    headers_cre = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    run_id = dt.now().strftime("%Y%m%d_%H%M")
    lignes = []

    # --- Electricite (TRVE) ---
    try:
        r = requests.get(
            "https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/Option_Base.csv",
            headers=headers_cre, timeout=30
        )
        df_elec = pd.read_csv(io.StringIO(r.content.decode("latin-1")), sep=None, engine="python")
        df_elec['DATE_DEBUT_dt'] = pd.to_datetime(df_elec['DATE_DEBUT'], dayfirst=True)
        derniere_date = df_elec['DATE_DEBUT_dt'].max()
        df_derniere = df_elec[df_elec['DATE_DEBUT_dt'] == derniere_date]
        for _, row in df_derniere.iterrows():
            puissance = f"{row['P_SOUSCRITE']} kVA"
            for indicateur, col, unite in [
                ("TRVE_part_variable_TTC", "PART_VARIABLE_TTC", "€/kWh"),
                ("TRVE_part_fixe_TTC", "PART_FIXE_TTC", "€/an"),
            ]:
                val = str(row[col]).replace(",", ".")
                lignes.append({
                    "domaine": "Électricité", "indicateur": indicateur,
                    "sous_categorie": puissance, "valeur": float(val), "unite": unite,
                    "date_debut_validite": derniere_date.date().isoformat(),
                    "date_verification": dt.now().isoformat(), "run_id": run_id,
                    "source_url": "https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/Option_Base.csv",
                })
        print(f"  ✅ Electricite : {len(df_derniere) * 2} valeurs ({derniere_date.date()})")
    except Exception as e:
        print(f"  ⚠️ Erreur refresh Electricite : {e}")

    # --- Gaz (PRVG) ---
    try:
        r = requests.get(
            "https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/OPEN_DATA_GRDF.xlsx",
            headers=headers_cre, timeout=30
        )
        df_gaz = pd.read_excel(io.BytesIO(r.content), sheet_name="Historique PRVG moyen")
        derniere_ligne = df_gaz.iloc[-1]
        lignes.append({
            "domaine": "Gaz", "indicateur": "PRVG_moyen_TTC", "sous_categorie": None,
            "valeur": float(derniere_ligne['Prix repère moyen TTC (€/MWh)']), "unite": "€/MWh",
            "date_debut_validite": pd.to_datetime(derniere_ligne['Date']).date().isoformat(),
            "date_verification": dt.now().isoformat(), "run_id": run_id,
            "source_url": "https://www.cre.fr/fileadmin/Documents/Open_data/Marches_de_detail/OPEN_DATA_GRDF.xlsx",
        })
        print(f"  ✅ Gaz : PRVG {lignes[-1]['valeur']} €/MWh ({lignes[-1]['date_debut_validite']})")
    except Exception as e:
        print(f"  ⚠️ Erreur refresh Gaz : {e}")

    # --- Aides (ANAH — situation-temoin fixe, validee) ---
    try:
        situation = {
            "vous.propriétaire.statut": '"propriétaire occupant"',
            "logement.propriétaire occupant": "oui",
            "ménage.personnes": 3,
            "ménage.revenu": '"modeste"',
            "ménage.commune": '"75056"',
            "parcours d'aide": '"accompagné"',
            "fields": "ampleur.pourcent d'écrêtement",
        }
        r = requests.get("https://mesaides.france-renov.gouv.fr/api/v1/", params=situation, timeout=20)
        data_aide = r.json()["ampleur.pourcent d'écrêtement"]
        lignes.append({
            "domaine": "Aides", "indicateur": "ampleur_pourcent_ecretement",
            "sous_categorie": "propriétaire occupant modeste, 3 pers., parcours accompagné",
            "valeur": float(data_aide["rawValue"]), "unite": "%",
            "date_debut_validite": dt.now().date().isoformat(),
            "date_verification": dt.now().isoformat(), "run_id": run_id,
            "source_url": "https://mesaides.france-renov.gouv.fr/api/v1/",
        })
        print(f"  ✅ Aides : écrêtement {lignes[-1]['valeur']} %")
    except Exception as e:
        print(f"  ⚠️ Erreur refresh Aides : {e}")

    if lignes:
        client_bq.insert_rows_json(
            f"{PROJECT_ID}.{DATASET_ID}.indicateurs_reglementaires", lignes
        )
        print(f"✅ RAFRAICHISSEMENT INDICATEURS : {len(lignes)} lignes inserees")
    return len(lignes)


MOIS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def construire_brief_actualite(changement, client_bq):
    """MODE ACTUALITE : construit un brief directement depuis un changement
    d'indicateur reglementaire detecte (vue_changements_indicateurs), SANS
    scraping concurrent ni appel IA supplementaire — pour publier le plus
    vite possible et etre premier sur le sujet. Retourne None si aucun
    silo/sous-silo n'est mappe pour cet indicateur."""
    indicateur = changement['indicateur']
    indicateur_safe = indicateur.replace("'", "''")
    try:
        df_cible = client_bq.query(f"""
        SELECT silo, sous_silo_strategique, pertinence
        FROM `{PROJECT_ID}.{DATASET_ID}.mapping_indicateur_sous_silo`
        WHERE indicateur = '{indicateur_safe}'
        ORDER BY pertinence = 'directe' DESC
        LIMIT 1
        """).to_dataframe()
    except Exception as e:
        print(f"  ⚠️ Erreur recherche silo cible pour {indicateur} : {e}")
        return None
    if df_cible.empty:
        return None
    silo = df_cible.iloc[0]['silo']
    sous_silo = df_cible.iloc[0]['sous_silo_strategique']
    maintenant = datetime.now()
    mois_annee = f"{MOIS_FR[maintenant.month]} {maintenant.year}"
    variation = changement['variation_pct']
    sens = "hausse" if variation > 0 else "baisse"
    source_officielle = "ANAH" if changement['domaine'] == 'Aides' else "CRE"
    valeur_actuelle_r = round(float(changement['valeur_actuelle']), 2)
    valeur_precedente_r = round(float(changement['valeur_precedente']), 2)
    titre = f"{sous_silo} : {sens} de {abs(variation):.1f}% en {mois_annee}"[:60]
    meta_description = (
        f"Découvrez la {sens} de {abs(variation):.1f}% sur {sous_silo.lower()} : "
        f"nouveau tarif de {valeur_actuelle_r} {changement['unite']} en {mois_annee}. "
        f"Ce que ça change concrètement pour votre facture."
    )[:160]
    return {
        "silo": silo,
        "sous_silo": sous_silo,
        "titre_seo": titre,
        "meta_description": meta_description,
        "mot_cle_principal": f"{sous_silo.lower()} {mois_annee.lower()}",
        "mots_cles_secondaires": [indicateur, "prix", mois_annee.lower(), sens],
        "volume_recommande": 800,
        "ton_recommande": "actualité, factuel, direct",
        "angle_differentiant": (
            f"Article d'actualité annonçant un changement officiel recemment "
            f"constate : {indicateur} passe de {valeur_precedente_r} "
            f"a {valeur_actuelle_r} {changement['unite']} "
            f"({sens} de {abs(variation):.1f}%), effectif depuis le "
            f"{changement['date_debut_validite']}. Source officielle : {source_officielle} "
            f"uniquement — ne pas attribuer ce chiffre a un autre organisme. "
            f"IMPORTANT : arrondir systematiquement tous les chiffres a 2 decimales "
            f"maximum dans l'article, ne jamais afficher un nombre avec plus de "
            f"decimales (ex: 172.05, jamais 172.0495426360616)."
        ),
        "structure": [
            {"niveau": "H1", "texte": titre, "conseil": "titre factuel avec le chiffre exact"},
            {"niveau": "H2", "texte": "Ce qui change", "conseil": "annonce claire avec les deux valeurs (avant/apres)"},
            {"niveau": "H2", "texte": "Pourquoi ce changement", "conseil": "contexte reglementaire general, rester factuel, ne rien inventer au-dela des donnees fournies"},
            {"niveau": "H2", "texte": "Impact concret pour vous", "conseil": "exemple chiffre base sur la nouvelle valeur uniquement"},
            {"niveau": "H2", "texte": "Ce qu'il faut retenir", "conseil": "resume actionnable en quelques lignes"},
        ],
        "champ_semantique": {
            "indispensables": [sous_silo, mois_annee],
            "enrichissement": [],
            "a_eviter": [],
        },
        "faq_recommandee": [],
    }


def publier_actualites_reglementaires(client_bq, config, wp_config, run_id):
    """MODE ACTUALITE : detecte les changements d'indicateurs reglementaires
    (vue_changements_indicateurs) et publie immediatement un article dedie
    pour chacun, en contournant le scraping concurrent — la vitesse de
    publication prime sur la profondeur, l'objectif etant d'etre premier
    sur le sujet plutot que de suivre la concurrence. Inclut schemas SVG,
    image mise en avant et notification push, comme le run principal."""
    print("📰 MODE ACTUALITE — detection des changements reglementaires...")
    try:
        df_changements = client_bq.query(f"""
        SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.vue_changements_indicateurs`
        """).to_dataframe()
    except Exception as e:
        print(f"  ⚠️ Erreur detection changements : {e}")
        return []
    if df_changements.empty:
        print("  ℹ️ Aucun changement detecte, rien a publier")
        return []
    print(f"  🔎 {len(df_changements)} changement(s) detecte(s)")
    lignes_publications = []
    for _, changement in df_changements.iterrows():
        brief = construire_brief_actualite(changement, client_bq)
        if not brief:
            print(f"  ⚠️ Pas de silo mappe pour {changement['indicateur']}, ignore")
            continue
        print(f"  ✍️ Redaction : {brief['titre_seo']}")
        contenu_html, erreur = rediger_article(brief, config, None, client_bq)
        if erreur:
            print(f"  ❌ {brief['titre_seo']} : {erreur}")
            continue
        resultat = publier_article(
            brief, brief['silo'], brief['sous_silo'], contenu_html,
            wp_config, client_bq, run_id, config
        )
        if resultat['success']:
            print(f"  ✅ ACTUALITE PUBLIEE : {resultat['url']}")
            try:
                client_bq.query(f"""
                UPDATE `{PROJECT_ID}.{DATASET_ID}.historique_publications`
                SET type_publication = 'actualite'
                WHERE post_id = {resultat['post_id']}
                """).result()
            except Exception as e:
                print(f"  ⚠️ Erreur marquage type_publication : {e}")
            nb_mots = len(re.sub(r'<[^>]+>', '', contenu_html).split())
            lignes_publications.append({
                "Silo": brief['silo'],
                "Titre": brief['titre_seo'],
                "Mot_cle": brief['mot_cle_principal'],
                "Nb_mots": nb_mots,
                "Post_ID": resultat['post_id'],
                "URL_WP": resultat['url'],
                "Statut": "publish",
                "Contenu_HTML": contenu_html,
                "sous_silo": brief['sous_silo'],
            })
        else:
            print(f"  ❌ {resultat.get('erreur')}")
    if lignes_publications:
        df_publications = pd.DataFrame(lignes_publications)
        try:
            nettoyer_et_generer_schemas(df_publications, wp_config, config)
        except Exception as e:
            print(f"  ⚠️ Erreur schemas Mode Actualite : {e}")
        try:
            generer_featured_images(df_publications, client_bq, config, OPENAI_CONFIG, wp_config)
        except Exception as e:
            print(f"  ⚠️ Erreur images Mode Actualite : {e}")
        try:
            notifier_nouveaux_articles(df_publications, config)
        except Exception as e:
            print(f"  ⚠️ Erreur notification Mode Actualite : {e}")
    print(f"📰 MODE ACTUALITE termine : {len(lignes_publications)} article(s) publie(s)")
    return lignes_publications


def recuperer_donnees_officielles(silo, sous_silo, client_bq):
    """Recupere les dernieres valeurs officielles connues (PRVG, TRVE,
    aides...) pour ce silo/sous-silo via la table de mapping du chantier
    veille reglementaire, pour eviter que l'IA n'invente des chiffres.
    Retourne une chaine prete a injecter dans le prompt, vide si rien
    ne correspond (fonctionne meme si les tables n'existent pas encore)."""
    try:
        silo_safe = silo.replace("'", "''")
        sous_silo_safe = (sous_silo or "").replace("'", "''")
        df = client_bq.query(f"""
        SELECT DISTINCT i.indicateur, i.valeur, i.unite, i.date_debut_validite
        FROM `{PROJECT_ID}.{DATASET_ID}.mapping_indicateur_sous_silo` m
        JOIN `{PROJECT_ID}.{DATASET_ID}.indicateurs_reglementaires` i
            ON i.indicateur = m.indicateur
        WHERE m.silo = '{silo_safe}'
          AND m.sous_silo_strategique = '{sous_silo_safe}'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY i.indicateur ORDER BY i.date_verification DESC) = 1
        """).to_dataframe()
        if df.empty:
            return ""
        return "\n".join([
            f"- {row['indicateur']} : {row['valeur']} {row['unite']} (en vigueur depuis le {row['date_debut_validite']})"
            for _, row in df.iterrows()
        ])
    except Exception:
        return ""


def rediger_article(brief, config, articles_silo=None, client_bq=None):
    annee_courante = datetime.now().year
    annee_suivante = annee_courante + 1
    annee_interdite = annee_courante - 1

    structure_str = "\n".join([
        f"{s['niveau']} : {s['texte']} → {s.get('conseil', '')}"
        for s in brief.get('structure', [])
    ])
    faq_str = "\n".join([f"- {f['question']}" for f in brief.get('faq_recommandee', [])])
    semantique = brief.get('champ_semantique', {})

    maillage_str = ""
    if articles_silo:
        liens = "\n".join([f"- {a.get('titre')} → {a.get('url')}" for a in articles_silo])
        maillage_str = f"\nMAILLAGE INTERNE :\n{liens}\n"
    donnees_officielles_str = ""
    if client_bq is not None:
        donnees = recuperer_donnees_officielles(brief.get('silo', ''), brief.get('sous_silo', ''), client_bq)
        print(f"  🔎 Donnees officielles pour {brief.get('silo')} | {brief.get('sous_silo')} : {'TROUVEES' if donnees else 'aucune'}")
        if donnees:
            donnees_officielles_str = f"\nDONNÉES OFFICIELLES ACTUELLES (source : CRE/ANAH, vérifiées — utilise IMPÉRATIVEMENT ces valeurs exactes dans au moins un exemple chiffré concret) :\n{donnees}\n"

    prompt = f"""Tu es un rédacteur SEO expert et conseiller commercial, spécialisé exclusivement dans 3 secteurs : l'électricité, le gaz et les aides à la rénovation énergétique en France.
Rédige un article complet basé sur ce brief :

BRIEF :
- Titre H1 : {brief.get('titre_seo')}
- Mot-clé : {brief.get('mot_cle_principal')}
- Mots-clés secondaires : {', '.join(brief.get('mots_cles_secondaires', []))}
- Volume : {brief.get('volume_recommande')} mots
- Ton : {brief.get('ton_recommande')}
- Angle : {brief.get('angle_differentiant')}

STRUCTURE :
{structure_str}

CHAMP SÉMANTIQUE :
- Indispensables : {', '.join(semantique.get('indispensables', []))}
- Enrichissement : {', '.join(semantique.get('enrichissement', []))}
- À éviter : {', '.join(semantique.get('a_eviter', []))}

FAQ :
{faq_str}

{maillage_str}
{donnees_officielles_str}

RÈGLES :
1. HTML propre (h1, h2, h3, p, ul, li, strong)
2. NE PAS ajouter de CTA commercial
3. Dates : {annee_courante} ou {annee_suivante} UNIQUEMENT — INTERDIT TOUTE année antérieure ({annee_interdite}, {annee_interdite - 1}, etc.), même si le contexte concurrent scrapé en mentionne une
4. Apostrophes : uniquement l'apostrophe droite simple (') — jamais d'entité HTML (&rsquo; interdit)
5. Chiffres précis (prix, taux, tarifs) : SI la section DONNÉES OFFICIELLES ACTUELLES est présente ci-dessus, tu DOIS OBLIGATOIREMENT reprendre ces valeurs exactes dans au moins un exemple chiffré concret de l'article — ne construis JAMAIS un exemple "simplifié" ou fictif avec un prix inventé si une donnée officielle existe pour ce sujet. INTERDIT d'inventer un prix, un taux ou une offre commerciale attribuée à une marque réelle (EDF, Engie, TotalEnergies...). Si aucune donnée officielle n'est fournie pour un point précis, reste général (ex: "les tarifs varient selon les fournisseurs") plutôt que d'inventer un chiffre.
6. Commence DIRECTEMENT par <h1>...</h1>
7. INTERDIT : ```html, <!DOCTYPE>, <html>, <head>, <body>"""

    headers = {
        "x-api-key": config['ANTHROPIC_API_KEY'],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {
        "model": config['MODEL'],
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
                         headers=headers, json=body, timeout=240)
        r.raise_for_status()
        contenu = r.json()['content'][0]['text']
        contenu = contenu.strip()
        contenu = re.sub(r'^```html\s*', '', contenu, flags=re.IGNORECASE)
        contenu = re.sub(r'^```\s*', '', contenu)
        contenu = re.sub(r'```\s*$', '', contenu)
        contenu = re.sub(r'<!DOCTYPE[^>]*>', '', contenu, flags=re.IGNORECASE)
        contenu = re.sub(r'<html[^>]*>|</html>', '', contenu, flags=re.IGNORECASE)
        contenu = re.sub(r'<head>.*?</head>', '', contenu, flags=re.DOTALL|re.IGNORECASE)
        contenu = re.sub(r'<body[^>]*>|</body>', '', contenu, flags=re.IGNORECASE)
        match = re.search(r'(<h[1-6]|<p|<article|<section)', contenu, re.IGNORECASE)
        if match:
            contenu = contenu[match.start():]
        contenu = nettoyer_texte_ia(contenu, annee_courante)
        return contenu.strip(), None
    except Exception as e:
        return None, f"❌ Erreur rédaction : {e}"


def get_ou_creer_categorie(sous_silo, parent_id, wp_config):
    slug_cible = MAPPING_CATEGORIES_WP.get(sous_silo)
    if not slug_cible:
        slug_cible = sous_silo.lower()
        for a, b in [('à','a'),('â','a'),('é','e'),('è','e'),('ê','e'),
                     ('î','i'),('ô','o'),('ù','u'),('û','u'),('ç','c'),
                     ("'",""),(' ','-')]:
            slug_cible = slug_cible.replace(a, b)
        slug_cible = re.sub(r'[^a-z0-9-]', '', slug_cible)

    r = requests.get(
        f"{wp_config['url']}/wp-json/wp/v2/categories",
        params={"slug": slug_cible, "per_page": 1},
        auth=(wp_config['username'], wp_config['app_password'])
    )
    cats = r.json()
    if cats:
        return cats[0]['id']

    r = requests.post(
        f"{wp_config['url']}/wp-json/wp/v2/categories",
        json={"name": sous_silo, "slug": slug_cible, "parent": parent_id},
        auth=(wp_config['username'], wp_config['app_password'])
    )
    return r.json().get('id')


def logger_publication_bq(client_bq, post_id, silo, titre,
                          mot_cle, url_wp, run_id, sous_silo_strategique, image_id=None):
    """Log publication dans BQ avec retry x3. Requetes parametrees :
    aucun risque d'echappement casse par des apostrophes/guillemets/accents,
    quel que soit le contenu (titre, silo, sous-silo...)."""
    from google.cloud import bigquery
    max_retries = 3
    for attempt in range(max_retries):
        try:
            df_check = client_bq.query(
                f"""SELECT COUNT(*) as nb
                FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
                WHERE post_id = @post_id""",
                job_config=bigquery.QueryJobConfig(query_parameters=[
                    bigquery.ScalarQueryParameter("post_id", "INT64", post_id)
                ])
            ).to_dataframe()

            params = [
                bigquery.ScalarQueryParameter("post_id", "INT64", post_id),
                bigquery.ScalarQueryParameter("silo", "STRING", silo),
                bigquery.ScalarQueryParameter("titre", "STRING", titre),
                bigquery.ScalarQueryParameter("mot_cle", "STRING", mot_cle),
                bigquery.ScalarQueryParameter("url_wp", "STRING", url_wp),
                bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
                bigquery.ScalarQueryParameter("sous_silo", "STRING", sous_silo_strategique),
                bigquery.ScalarQueryParameter("image_id", "STRING", image_id),
            ]

            if df_check['nb'].iloc[0] > 0:
                query = """
                UPDATE `{}.{}.historique_publications`
                SET date_publication = CURRENT_TIMESTAMP(),
                    silo = @silo,
                    titre = @titre,
                    mot_cle = @mot_cle,
                    url_wp = @url_wp,
                    run_id = @run_id,
                    sous_silo_strategique = @sous_silo,
                    image_id = @image_id
                WHERE post_id = @post_id
                """.format(PROJECT_ID, DATASET_ID)
            else:
                query = """
                INSERT INTO `{}.{}.historique_publications`
                (date_publication, post_id, silo, titre, mot_cle,
                 url_wp, run_id, sous_silo_strategique, image_id)
                VALUES (CURRENT_TIMESTAMP(), @post_id, @silo, @titre, @mot_cle,
                    @url_wp, @run_id, @sous_silo, @image_id)
                """.format(PROJECT_ID, DATASET_ID)

            client_bq.query(
                query,
                job_config=bigquery.QueryJobConfig(query_parameters=params)
            ).result()
            return True
        except Exception as e:
            print(f"  ⚠️ Log BQ tentative {attempt+1}/{max_retries} échoué : {e}")
            if attempt < max_retries - 1:
                import time; time.sleep(2)
    print(f"  ❌ Log BQ définitivement échoué après {max_retries} tentatives")
    return False


def recuperer_articles_meme_silo(silo_name, wp_config):
    silo_propre = silo_name.split('. ')[-1] if '. ' in silo_name else silo_name
    r = requests.get(
        f"{wp_config['url']}/wp-json/wp/v2/categories",
        params={"per_page": 100},
        auth=(wp_config['username'], wp_config['app_password'])
    )
    if r.status_code != 200:
        return []
    toutes_cats = r.json()
    cat_silo = next(
        (c for c in toutes_cats if c['name'].strip().lower() == silo_propre.lower()),
        None
    )
    if not cat_silo:
        return []
    silo_id = cat_silo['id']
    sous_ids = [c['id'] for c in toutes_cats if c['parent'] == silo_id]
    cats_ids = [silo_id] + sous_ids
    r_posts = requests.get(
        f"{wp_config['url']}/wp-json/wp/v2/posts",
        params={"categories": ",".join(map(str, cats_ids)), "per_page": 10, "status": "publish"},
        auth=(wp_config['username'], wp_config['app_password'])
    )
    if r_posts.status_code != 200:
        return []
    return [
        {"titre": p['title']['rendered'], "url": p['link'],
         "mot_cle": p.get('slug', '').replace('-', ' ')}
        for p in r_posts.json()
    ][:5]


def verifier_article_wp_existe(slug, wp_config):
    """Vérifie si un article avec ce slug existe déjà sur WordPress."""
    try:
        r = requests.get(
            f"{wp_config['url']}/wp-json/wp/v2/posts",
            params={"slug": slug, "status": "publish", "per_page": 1},
            auth=(wp_config['username'], wp_config['app_password']),
            timeout=15
        )
        if r.status_code == 200:
            posts = r.json()
            if posts:
                print(f"  ⚠️ Article déjà publié sur WP : {posts[0].get('link', slug)}")
                return True, posts[0]['id']
        return False, None
    except Exception as e:
        print(f"  ⚠️ Vérif WP échouée : {e}")
        return False, None



# ============================================================
# CTA — Boutons vers les simulateurs (injectes dans chaque article)
# ============================================================
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

def tronquer_proprement(texte, limite):
    """Tronque un texte a la limite de caracteres donnee sans jamais
    couper un mot en deux. Filet de securite si l'IA depasse malgre
    les instructions du prompt. Retourne le texte tel quel s'il est
    deja dans la limite."""
    if not texte or len(texte) <= limite:
        return texte
    tronque = texte[:limite]
    dernier_espace = tronque.rfind(' ')
    if dernier_espace > 0:
        return tronque[:dernier_espace].rstrip('.,;:!?-')
    return tronque


def generer_legende_facebook(titre_article, silo_name, config):
    """Genere une legende de repli pour Facebook, utilisee uniquement si
    l'extraction de l'introduction de l'article echoue."""
    prompt = f"""Tu es un community manager specialise energie/renovation en France.
Ecris UNE legende Facebook courte (2-3 phrases MAX, 300 caracteres MAX) pour promouvoir cet article :

Titre : {titre_article}
Theme : {silo_name}

Contraintes :
- Ton direct, accrocheur, pas de jargon SEO
- 0 a 2 hashtags maximum, jamais plus
- Donne envie de cliquer sans etre putaclic
- Pas de guillemets autour du texte, pas de prefixe type "Legende :"

Reponds uniquement avec le texte de la legende, rien d'autre."""
    headers = {
        "x-api-key": config['ANTHROPIC_API_KEY'],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    body = {
        "model": config['MODEL'],
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
                         headers=headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json()['content'][0]['text'].strip()
    except Exception:
        return titre_article


def extraire_introduction_article(contenu_html, limite=400):
    """Extrait le premier paragraphe de l'article (son introduction reelle)
    pour servir de description au post Facebook. Coupe proprement au
    dernier mot si necessaire (jamais de mot tronque)."""
    try:
        soup = BeautifulSoup(contenu_html, 'html.parser')
        premier_p = soup.find('p')
        if not premier_p:
            return None
        texte = premier_p.get_text(strip=True)
        if not texte:
            return None
        return tronquer_proprement(texte, limite)
    except Exception:
        return None


def publier_facebook(titre_article, url_article, message, facebook_config):
    """Publie un lien vers l'article sur la Page Facebook avec le message
    fourni (introduction de l'article, ou legende de repli). Facebook
    genere automatiquement l'apercu (image, titre) a partir des balises
    Open Graph de la page WordPress -- pas besoin de reuploader l'image."""
    page_id = facebook_config.get('page_id')
    access_token = facebook_config.get('access_token')
    if not page_id or not access_token:
        return False, "Configuration Facebook manquante"
    try:
        r = requests.post(
            f"https://graph.facebook.com/v21.0/{page_id}/feed",
            data={
                "message": message,
                "link": url_article,
                "access_token": access_token
            },
            timeout=30
        )
        if r.status_code == 200:
            return True, r.json().get('id', '')
        return False, f"HTTP {r.status_code} — {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def publier_instagram(image_url, message, instagram_config):
    """Publie une image sur le compte Instagram Business, avec la legende
    fournie. Processus en 2 etapes propre a l'API Instagram : creation d'un
    conteneur media, puis publication de ce conteneur (contrairement a
    Facebook qui publie en un seul appel)."""
    import time
    ig_user_id = instagram_config.get('business_account_id')
    access_token = instagram_config.get('access_token')
    if not ig_user_id or not access_token:
        return False, "Configuration Instagram manquante"
    try:
        r1 = requests.post(
            f"https://graph.facebook.com/v21.0/{ig_user_id}/media",
            data={
                "image_url": image_url,
                "caption": message,
                "access_token": access_token
            },
            timeout=30
        )
        if r1.status_code != 200:
            return False, f"HTTP {r1.status_code} (creation) — {r1.text[:200]}"
        creation_id = r1.json().get('id', '')
        time.sleep(3)
        r2 = requests.post(
            f"https://graph.facebook.com/v21.0/{ig_user_id}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": access_token
            },
            timeout=30
        )
        if r2.status_code == 200:
            return True, r2.json().get('id', '')
        return False, f"HTTP {r2.status_code} (publication) — {r2.text[:200]}"
    except Exception as e:
        return False, str(e)


def logger_publication_facebook_bq(client_bq, post_id, silo, titre, url_article,
                                     facebook_post_id, message, succes, erreur=None):
    """Enregistre chaque tentative de publication Facebook dans BigQuery,
    pour tracabilite et futur rapprochement avec les stats d'engagement."""
    try:
        rows = [{
            "date_publication": datetime.now().isoformat(),
            "post_id": post_id,
            "silo": silo,
            "titre": titre,
            "url_article": url_article,
            "facebook_post_id": facebook_post_id or "",
            "message_utilise": message or "",
            "succes": succes,
            "erreur": erreur or "",
        }]
        client_bq.insert_rows_json(
            f"{PROJECT_ID}.{DATASET_ID}.historique_publications_facebook", rows
        )
    except Exception as e:
        print(f"  ⚠️ Erreur log Facebook BQ : {e}")


def logger_publication_instagram_bq(client_bq, post_id, silo, titre, url_article,
                                      instagram_post_id, message, succes, erreur=None):
    """Enregistre chaque tentative de publication Instagram dans BigQuery,
    meme logique de tracabilite que pour Facebook."""
    try:
        rows = [{
            "date_publication": datetime.now().isoformat(),
            "post_id": post_id,
            "silo": silo,
            "titre": titre,
            "url_article": url_article,
            "instagram_post_id": instagram_post_id or "",
            "message_utilise": message or "",
            "succes": succes,
            "erreur": erreur or "",
        }]
        client_bq.insert_rows_json(
            f"{PROJECT_ID}.{DATASET_ID}.historique_publications_instagram", rows
        )
    except Exception as e:
        print(f"  ⚠️ Erreur log Instagram BQ : {e}")


def notifier_nouveaux_articles(df_publications, config):
    """Notifie tous les utilisateurs de l'app mobile ayant active les
    notifications qu'un nouveau lot d'articles vient d'etre publie.
    Un seul envoi groupe par run, pas un par article (evite le spam)."""
    nb = len(df_publications)
    if nb == 0 or not BROADCAST_API_KEY:
        return
    if nb == 1:
        corps = "1 nouvel article vient d'etre publie"
    else:
        corps = f"{nb} nouveaux articles viennent d'etre publies"
    try:
        r = requests.post(
            f"{CLIENT_API_URL}/notifications/broadcast",
            json={
                "title": "Nouveaux articles disponibles",
                "body": corps,
                "data": {"type": "nouveaux_articles"}
            },
            headers={"X-Broadcast-Key": BROADCAST_API_KEY, "Content-Type": "application/json"},
            timeout=15
        )
        if r.status_code == 200:
            print(f"  📱 Notification push envoyee : {r.json().get('count', 0)} appareils")
        else:
            print(f"  ⚠️ Notification push echouee : HTTP {r.status_code}")
    except Exception as e:
        print(f"  ⚠️ Erreur notification push : {e}")


def publier_tous_facebook(df_publications, client_bq, config, facebook_config):
    """Publie chaque article du run sur la Page Facebook, avec en
    description l'introduction reelle de l'article (repli sur une legende
    generee par IA si l'extraction echoue). Chaque tentative est loggee
    dans BigQuery pour tracabilite."""
    print("📘 PUBLICATION FACEBOOK...")
    if not facebook_config.get('access_token') or not facebook_config.get('page_id'):
        print("  ⏭️ Facebook non configure, etape ignoree")
        return
    for idx, row in df_publications.iterrows():
        post_id = row['Post_ID']
        silo_name = row['Silo']
        titre_article = row['Titre']
        contenu_html = row.get('Contenu_HTML', '') if hasattr(row, 'get') else row['Contenu_HTML']

        try:
            df_url = client_bq.query(f"""
            SELECT url_wp FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE post_id = {post_id} LIMIT 1
            """).to_dataframe()
            url_article = df_url['url_wp'].iloc[0] if not df_url.empty else None
        except Exception:
            url_article = None

        if not url_article:
            print(f"  ⚠️ {titre_article[:50]}... — URL introuvable, ignore")
            continue

        message = extraire_introduction_article(contenu_html)
        if not message:
            message = generer_legende_facebook(titre_article, silo_name, config)
        emoji_silo = SILO_EMOJIS.get(silo_name, "")
        if emoji_silo and message:
            message = f"{emoji_silo} {message}"

        succes, resultat = publier_facebook(titre_article, url_article, message, facebook_config)
        if succes:
            print(f"  ✅ {titre_article[:50]}... — post {resultat}")
            logger_publication_facebook_bq(client_bq, post_id, silo_name, titre_article,
                                            url_article, resultat, message, True)
        else:
            print(f"  ❌ {titre_article[:50]}... — {resultat}")
            logger_publication_facebook_bq(client_bq, post_id, silo_name, titre_article,
                                            url_article, None, message, False, erreur=resultat)


def publier_tous_instagram(df_publications, client_bq, config, instagram_config):
    """Publie chaque article du run sur Instagram, avec l'image mise en
    avant de l'article (recuperee depuis WordPress) et la meme legende que
    Facebook, complete par un renvoi vers la bio (Instagram n'autorise pas
    les liens cliquables dans les legendes de posts)."""
    print("📸 PUBLICATION INSTAGRAM...")
    if not instagram_config.get('access_token') or not instagram_config.get('business_account_id'):
        print("  ⏭️ Instagram non configure, etape ignoree")
        return
    for idx, row in df_publications.iterrows():
        post_id = row['Post_ID']
        silo_name = row['Silo']
        titre_article = row['Titre']
        contenu_html = row.get('Contenu_HTML', '') if hasattr(row, 'get') else row['Contenu_HTML']
        try:
            df_url = client_bq.query(f"""
            SELECT url_wp FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE post_id = {post_id} LIMIT 1
            """).to_dataframe()
            url_article = df_url['url_wp'].iloc[0] if not df_url.empty else None
        except Exception:
            url_article = None
        if not url_article:
            print(f"  ⚠️ {titre_article[:50]}... — URL introuvable, ignore")
            continue
        try:
            r = requests.get(f"{WP_CONFIG['url']}/wp-json/wp/v2/posts/{post_id}?_embed", timeout=15)
            image_url = r.json()['_embedded']['wp:featuredmedia'][0]['source_url']
        except Exception:
            image_url = None
        if not image_url:
            print(f"  ⚠️ {titre_article[:50]}... — image introuvable, ignore")
            logger_publication_instagram_bq(client_bq, post_id, silo_name, titre_article,
                                             url_article, None, "", False, erreur="Image introuvable")
            continue
        message = extraire_introduction_article(contenu_html)
        if not message:
            message = generer_legende_facebook(titre_article, silo_name, config)
        emoji_silo = SILO_EMOJIS.get(silo_name, "")
        if emoji_silo and message:
            message = f"{emoji_silo} {message}"
        message = f"{message}\n\n🔗 Lien dans la bio"
        succes, resultat = publier_instagram(image_url, message, instagram_config)
        if succes:
            print(f"  ✅ {titre_article[:50]}... — post {resultat}")
            logger_publication_instagram_bq(client_bq, post_id, silo_name, titre_article,
                                             url_article, resultat, message, True)
        else:
            print(f"  ❌ {titre_article[:50]}... — {resultat}")
            logger_publication_instagram_bq(client_bq, post_id, silo_name, titre_article,
                                             url_article, None, message, False, erreur=resultat)


SILO_EMOJIS = {
    "1. Gaz": "🔥",
    "5. Électricité": "⚡",
    "4. Solaire": "☀️",
    "2. Rénovation Énergétique": "🏠",
    "3. Aide Énergétique": "💶",
}


def generer_cta_html(silo_name, post_id=None):
    """Genere le bloc CTA HTML a injecter en fin d'article selon le silo.
    Si post_id est fourni, ajoute ?src_post={post_id} au lien pour tracer
    l'attribution article -> clic -> lead jusqu'a BigQuery.

    Le div clear:both en tete de bloc evite le chevauchement visuel avec
    le footer quand l'article se termine par un tableau HTML genere par
    l'IA (tableaux parfois plus larges que leur conteneur, ce qui casse
    le flux de la page sans ce clearfix)."""
    cfg = CTA_TOOLS.get(silo_name)
    if not cfg:
        return ""
    url_finale = cfg["url"]
    if post_id:
        sep = '&' if '?' in url_finale else '?'
        url_finale = f"{url_finale}{sep}src_post={post_id}"
    return f'''
<div style="clear:both;overflow:hidden;"></div>
<div style="background:linear-gradient(135deg,{cfg["couleur1"]},{cfg["couleur2"]});border-radius:16px;padding:1.75rem;text-align:center;margin:32px 0;max-width:100%;box-sizing:border-box;">
  <h3 style="color:#fff;font-size:20px;font-weight:700;margin:0 0 8px">{cfg["titre"]}</h3>
  <p style="color:rgba(255,255,255,.9);font-size:14px;margin:0 0 18px;line-height:1.5">{cfg["texte"]}</p>
  <a href="{url_finale}" style="display:inline-block;background:#fff;color:{cfg["couleur2"]};font-size:15px;font-weight:700;padding:14px 32px;border-radius:10px;text-decoration:none;">{cfg["bouton"]} &rarr;</a>
</div>
'''

def publier_article(brief, silo_name, sous_silo_val, contenu_html,
                    wp_config, client_bq, run_id, config):
    # Slug
    slug_article = brief.get('slug_article', '')
    slug_complet = brief.get('slug_complet', '')
    if slug_article:
        slug = re.sub(r'[^a-z0-9-]', '-', slug_article.lower().strip('/'))
        slug = re.sub(r'-+', '-', slug).strip('-')
    else:
        slug = brief.get('mot_cle_principal', '').lower()
        for a, b in [('à','a'),('â','a'),('é','e'),('è','e'),('ê','e'),
                     ('î','i'),('ô','o'),('ù','u'),('û','u'),('ç','c')]:
            slug = slug.replace(a, b)
        slug = re.sub(r'[^a-z0-9-]', '-', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
    if len(slug) > 75:
        slug = slug[:slug[:75].rfind('-')] if '-' in slug[:75] else slug[:75]

    titre_seo = tronquer_proprement(brief.get('titre_seo', ''), 60)
    meta_desc = tronquer_proprement(brief.get('meta_description', ''), 160)

    # Catégories
    silo_propre = silo_name.split('. ')[-1] if '. ' in silo_name else silo_name
    cat_parent_id = get_ou_creer_categorie(silo_propre, 0, wp_config)
    if sous_silo_val and str(sous_silo_val) != 'nan':
        cat_enfant_id = get_ou_creer_categorie(sous_silo_val, cat_parent_id, wp_config)
        categories_ids = [cat_enfant_id]
    else:
        categories_ids = [cat_parent_id]

    # Vérification anti-doublon WordPress avant publication
    existe_wp, post_id_existant = verifier_article_wp_existe(slug, wp_config)
    if existe_wp and post_id_existant:
        titre_existant = ''
        try:
            check = requests.get(
                f"{wp_config['url']}/wp-json/wp/v2/posts/{post_id_existant}",
                auth=(wp_config['username'], wp_config['app_password']),
                timeout=10
            )
            if check.status_code == 200:
                titre_existant = check.json().get('title', {}).get('rendered', '').strip()
        except Exception as e:
            print(f"  ⚠️ Vérif titre existant échouée : {e}")

        if titre_existant and titre_existant == titre_seo.strip():
            url_wp = f"{wp_config['url']}/?p={post_id_existant}"
            print(f"  ↩️ Article existant récupéré (post_id={post_id_existant})")
            logger_publication_bq(
                client_bq, post_id_existant, silo_name, titre_seo,
                brief.get('mot_cle_principal', ''), url_wp, run_id,
                sous_silo_val or ''
            )
            return {"success": True, "post_id": post_id_existant, "url": url_wp, "existant": True}
        else:
            suffixe = datetime.now().strftime('%m%d')
            slug = f"{slug}-{suffixe}"
            print(f"  ⚠️ Collision de slug (titre different: '{titre_existant}' != '{titre_seo}')")
            print(f"  🔀 Nouveau slug généré : {slug}")

    payload = {
        "title": titre_seo,
        "content": contenu_html,
        "status": "publish",
        "excerpt": meta_desc,
        "slug": slug,
        "categories": categories_ids,
        "meta": {
            "rank_math_focus_keyword": brief.get('mot_cle_principal', ''),
            "rank_math_description": meta_desc,
            "rank_math_title": titre_seo
        }
    }
    try:
        r = requests.post(
            f"{wp_config['url']}/wp-json/wp/v2/posts",
            json=payload,
            auth=(wp_config['username'], wp_config['app_password']),
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        if r.status_code == 201:
            data = r.json()
            post_id = data.get('id')
            url_wp = data.get('link')
            print(f"  ✅ Publié : {url_wp}")
            print(f"  🆔 Post ID : {post_id}")

            # PATCH : injecter le CTA avec l'attribution ?src_post={post_id}
            # (impossible de le faire avant, le post_id n'existait pas encore)
            try:
                cta_final = generer_cta_html(silo_name, post_id)
                r_patch = requests.post(
                    f"{wp_config['url']}/wp-json/wp/v2/posts/{post_id}",
                    json={"content": contenu_html + cta_final},
                    auth=(wp_config['username'], wp_config['app_password']),
                    timeout=30
                )
                if r_patch.status_code == 200:
                    print(f"  🎯 CTA avec attribution injecté (src_post={post_id})")
                else:
                    print(f"  ⚠️ PATCH CTA échoué : HTTP {r_patch.status_code}")
            except Exception as e_cta:
                print(f"  ⚠️ Erreur injection CTA : {e_cta}")

            logger_publication_bq(
                client_bq, post_id, silo_name, titre_seo,
                brief.get('mot_cle_principal', ''),
                url_wp, run_id, sous_silo_val
            )
            return {"success": True, "post_id": post_id, "url": url_wp}
        else:
            return {"success": False, "erreur": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"success": False, "erreur": str(e)}


def rediger_et_publier(all_briefs_finaux, silos_a_traiter, wp_config, client_bq, config, run_id):
    df_publications = []
    print("✍️ RÉDACTION + PUBLICATION...")
    silos_df = pd.DataFrame(silos_a_traiter)

    for _cle, brief in all_briefs_finaux.items():
        # split('||') sans limite : voir PATCH 1/2, meme raison.
        parts = _cle.split('||')
        silo_name = parts[0]
        sous_silo_override = parts[1] if len(parts) > 1 else ''
        print(f"\n{'='*55}")
        print(f"📂 {silo_name} — {brief.get('titre_seo')}")

        articles_silo = recuperer_articles_meme_silo(silo_name, wp_config)
        contenu_html, erreur = rediger_article(brief, config, articles_silo, client_bq)
        if erreur:
            print(f"  {erreur}")
            continue

        liens = re.findall(
            r'<a href="https://www\.comprendre-mon-energie\.fr[^"]*"', contenu_html
        )
        nb_mots = len(re.sub(r'<[^>]+>', '', contenu_html).split())
        print(f"  🔗 {len(liens)} liens internes | {nb_mots} mots")

        try:
            if sous_silo_override:
                sous_silo_val = sous_silo_override
            else:
                sous_silo_val = silos_df[silos_df['silo'] == silo_name]['sous_silo'].iloc[0]
                if pd.isna(sous_silo_val): sous_silo_val = ''
        except:
            sous_silo_val = sous_silo_override or ''
        # Retire le suffixe technique ' (2)', ' (3)'... ajoute a la selection
        # pour distinguer plusieurs sujets industrialises partageant le meme
        # sous-silo. La vraie categorisation WordPress/BigQuery doit garder
        # le nom de sous-silo original.
        sous_silo_val = re.sub(r' \(\d+\)$', '', sous_silo_val)

        resultat = publier_article(
            brief, silo_name, sous_silo_val, contenu_html,
            wp_config, client_bq, run_id, config
        )
        if resultat['success']:
            df_publications.append({
                "Silo": silo_name,
                "Titre": brief.get('titre_seo'),
                "Mot_cle": brief.get('mot_cle_principal'),
                "Nb_mots": nb_mots,
                "Post_ID": resultat['post_id'],
                "URL_WP": resultat['url'],
                "Statut": "publish",
                "Contenu_HTML": contenu_html,
                "sous_silo": sous_silo_val,
            })
        else:
            print(f"  ❌ {resultat['erreur']}")

    return pd.DataFrame(df_publications)


# ============================================================
# CELLULE 11B — SCHÉMAS SVG
# ============================================================
def get_couleur_silo(silo_name):
    silo_lower = str(silo_name).lower()
    for key, couleur in COULEURS_SILO.items():
        if key in silo_lower:
            return couleur
    return '#1A73E8'


def extraire_donnees_svg(html_article, h2_texte, type_svg, config):
    soup = BeautifulSoup(html_article, 'html.parser')
    texte_section = ""
    for h2 in soup.find_all('h2'):
        if h2_texte[:25].lower() in h2.get_text().lower():
            sibling = h2.find_next_sibling()
            parts = []
            while sibling and sibling.name not in ['h2', 'h1']:
                parts.append(sibling.get_text(strip=True))
                sibling = sibling.find_next_sibling()
            texte_section = ' '.join(parts)[:2000]
            break

    if type_svg == 'flowchart':
        prompt = f"""Extrait les étapes du processus.
Texte : "{texte_section}"
H2 : "{h2_texte}"
JSON : {{"labels":["Étape 1","Étape 2","Étape 3"],"descriptions":["desc","desc","desc"]}}
Max 5 étapes. Labels 25 car. Descriptions 45 car."""
    elif type_svg == 'comparatif':
        prompt = f"""Structure un comparatif.
Texte : "{texte_section}"
H2 : "{h2_texte}"
JSON : {{"items":["Option A","Option B"],"criteres":[{{"nom":"Crit","item_0":"val","item_1":"val","score_0":8,"score_1":6}}]}}
Max 3 options, 5 critères."""
    else:
        prompt = f"""Identifie les composants techniques.
Texte : "{texte_section}"
H2 : "{h2_texte}"
JSON : {{"titre":"titre 40 car","composants":[{{"nom":"Comp","desc":"rôle","icone":"⚡"}}]}}
Max 5 composants. Noms 15 car."""

    headers = {
        "x-api-key": config['ANTHROPIC_API_KEY'],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json={"model": config['MODEL'], "max_tokens": 500,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30
        )
        contenu = r.json()['content'][0]['text'].strip()
        contenu = contenu.replace("```json", "").replace("```", "").strip()
        return json.loads(contenu)
    except Exception as e:
        print(f"    ⚠️ Extraction SVG échouée : {e}")
        return None


def generer_flowchart_svg(labels, descriptions, couleur, index=0):
    nb = len(labels)
    largeur = 680
    hauteur_etape = 85
    hauteur = nb * hauteur_etape + 80
    marge = 35
    PALETTES = [
        [couleur, '#34A853', '#FBBC04', '#EA4335', '#9C27B0'],
        ['#1A73E8', '#FF6D00', '#00BCD4', '#E91E63', '#34A853'],
        ['#9C27B0', '#FF6D00', '#34A853', '#1A73E8', '#EA4335'],
    ]
    couleurs = PALETTES[index % len(PALETTES)]

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largeur} {hauteur}"
     style="font-family:Arial,sans-serif;background:#FAFAFA;border-radius:8px;">
  <rect x="0" y="0" width="{largeur}" height="38" rx="8" fill="{couleur}"/>
  <rect x="0" y="28" width="{largeur}" height="10" fill="{couleur}"/>
  <text x="{largeur//2}" y="24" text-anchor="middle" fill="white" font-size="13" font-weight="bold">Processus étape par étape</text>'''

    for i, (label, desc) in enumerate(zip(labels, descriptions)):
        y = 50 + i * hauteur_etape
        c = couleurs[i % len(couleurs)]
        if i < nb - 1:
            svg += f'''
  <line x1="{marge+22}" y1="{y+44}" x2="{marge+22}" y2="{y+hauteur_etape-4}" stroke="{c}" stroke-width="2" stroke-dasharray="4,3"/>
  <polygon points="{marge+17},{y+hauteur_etape-7} {marge+27},{y+hauteur_etape-7} {marge+22},{y+hauteur_etape+1}" fill="{couleurs[(i+1)%len(couleurs)]}"/>'''
        svg += f'''
  <circle cx="{marge+22}" cy="{y+24}" r="20" fill="{c}" opacity="0.15"/>
  <circle cx="{marge+22}" cy="{y+24}" r="16" fill="{c}"/>
  <text x="{marge+22}" y="{y+29}" text-anchor="middle" fill="white" font-size="13" font-weight="bold">{i+1}</text>
  <rect x="{marge+52}" y="{y+4}" width="{largeur-marge-72}" height="42" rx="6" fill="white" stroke="{c}" stroke-width="1.5"/>
  <text x="{marge+67}" y="{y+22}" fill="#202124" font-size="12" font-weight="bold">{label[:28]}</text>
  <text x="{marge+67}" y="{y+37}" fill="#5F6368" font-size="10">{desc[:48]}</text>'''

    svg += '\n</svg>'
    return svg.encode('utf-8')


def generer_technique_svg(titre, composants, couleur, index=0):
    largeur = 680
    nb = min(len(composants), 5)
    hauteur = 380
    PALETTES = [
        ['#1A73E8', '#34A853', '#FBBC04', '#EA4335', '#9C27B0'],
        ['#FF6D00', '#00BCD4', '#E91E63', '#34A853', '#1A73E8'],
        ['#9C27B0', '#FBBC04', '#34A853', '#1A73E8', '#FF6D00'],
    ]
    cols = PALETTES[index % len(PALETTES)]

    if nb <= 2:
        positions = [(170, 200), (510, 200)]
    elif nb == 3:
        positions = [(130, 200), (340, 200), (550, 200)]
    elif nb == 4:
        positions = [(100, 170), (280, 170), (460, 170), (340, 300)]
    else:
        positions = [(110, 160), (290, 160), (470, 160), (200, 290), (480, 290)]

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largeur} {hauteur}"
     style="font-family:Arial,sans-serif;background:#FAFAFA;border-radius:8px;">
  <defs><linearGradient id="grad{index}" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" style="stop-color:#F8F9FA;stop-opacity:1"/>
    <stop offset="100%" style="stop-color:#E8F0FE;stop-opacity:1"/>
  </linearGradient></defs>
  <rect width="{largeur}" height="{hauteur}" fill="url(#grad{index})" rx="8"/>
  <rect x="0" y="0" width="{largeur}" height="38" rx="8" fill="{couleur}"/>
  <rect x="0" y="28" width="{largeur}" height="10" fill="{couleur}"/>
  <text x="{largeur//2}" y="24" text-anchor="middle" fill="white" font-size="13" font-weight="bold">{titre[:45]}</text>'''

    for i in range(len(positions) - 1):
        x1, y1 = positions[i]
        x2, y2 = positions[i + 1]
        svg += f'\n  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#DADCE0" stroke-width="2" stroke-dasharray="6,3"/>'

    for i, comp in enumerate(composants[:nb]):
        if i >= len(positions):
            break
        x, y = positions[i]
        c = cols[i % len(cols)]
        svg += f'''
  <circle cx="{x}" cy="{y}" r="52" fill="white" stroke="{c}" stroke-width="2.5"/>
  <circle cx="{x}" cy="{y}" r="44" fill="{c}" opacity="0.08"/>
  <text x="{x}" y="{y-12}" text-anchor="middle" font-size="22">{comp.get('icone','⚙️')}</text>
  <text x="{x}" y="{y+8}" text-anchor="middle" fill="{c}" font-size="10" font-weight="bold">{comp.get('nom','')[:15]}</text>
  <text x="{x}" y="{y+22}" text-anchor="middle" fill="#5F6368" font-size="9">{comp.get('desc','')[:22]}</text>'''

    svg += '\n</svg>'
    return svg.encode('utf-8')


def generer_comparatif_svg(items, criteres, couleur, index=0):
    nb_items = min(len(items), 3)
    nb_criteres = min(len(criteres), 5)
    largeur = 680
    col_w = (largeur - 160) // nb_items
    ligne_h = 48
    hauteur = nb_criteres * ligne_h + 110
    COULEURS_ITEMS = [
        ['#1A73E8', '#34A853', '#EA4335'],
        ['#FF6D00', '#9C27B0', '#00BCD4'],
        ['#34A853', '#1A73E8', '#FBBC04'],
    ]
    cols = COULEURS_ITEMS[index % len(COULEURS_ITEMS)]

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largeur} {hauteur}"
     style="font-family:Arial,sans-serif;background:#FAFAFA;border-radius:8px;">
  <rect x="0" y="0" width="{largeur}" height="38" rx="8" fill="{couleur}"/>
  <rect x="0" y="28" width="{largeur}" height="10" fill="{couleur}"/>
  <text x="{largeur//2}" y="24" text-anchor="middle" fill="white" font-size="13" font-weight="bold">Tableau comparatif</text>'''

    for i in range(nb_items):
        x = 160 + i * col_w + col_w // 2
        svg += f'''
  <rect x="{160+i*col_w}" y="42" width="{col_w}" height="32" fill="{cols[i]}" opacity="0.9"/>
  <text x="{x}" y="62" text-anchor="middle" fill="white" font-size="11" font-weight="bold">{items[i][:14]}</text>'''

    for j, critere in enumerate(criteres[:nb_criteres]):
        y = 78 + j * ligne_h
        bg = '#FFFFFF' if j % 2 == 0 else '#F8F9FA'
        svg += f'''
  <rect x="0" y="{y}" width="{largeur}" height="{ligne_h}" fill="{bg}"/>
  <text x="10" y="{y+20}" fill="#202124" font-size="11" font-weight="bold">{critere.get('nom','')[:22]}</text>'''
        for i in range(nb_items):
            x = 160 + i * col_w + col_w // 2
            valeur = critere.get(f'item_{i}', '—')
            score = critere.get(f'score_{i}')
            if score is not None:
                bar_w = int((int(score) / 10) * (col_w - 16))
                svg += f'''
  <rect x="{160+i*col_w+6}" y="{y+24}" width="{col_w-12}" height="12" rx="6" fill="#EEEEEE"/>
  <rect x="{160+i*col_w+6}" y="{y+24}" width="{bar_w}" height="12" rx="6" fill="{cols[i]}" opacity="0.85"/>
  <text x="{x}" y="{y+17}" text-anchor="middle" fill="#202124" font-size="9">{str(valeur)[:12]}</text>'''
            else:
                svg += f'\n  <text x="{x}" y="{y+30}" text-anchor="middle" fill="#202124" font-size="10">{str(valeur)[:12]}</text>'
        svg += f'\n  <line x1="0" y1="{y+ligne_h}" x2="{largeur}" y2="{y+ligne_h}" stroke="#E8EAED" stroke-width="1"/>'

    svg += '\n</svg>'
    return svg.encode('utf-8')


def upload_svg_wordpress(svg_bytes, filename, seo_tags, wp_config):
    try:
        import cairosvg
        png_bytes = cairosvg.svg2png(bytestring=svg_bytes, dpi=150, output_width=680)
    except:
        png_bytes = svg_bytes

    try:
        r = requests.post(
            f"{wp_config['url']}/wp-json/wp/v2/media",
            headers={"Content-Disposition": f'attachment; filename="{filename}"',
                     "Content-Type": "image/png"},
            data=png_bytes,
            auth=(wp_config['username'], wp_config['app_password']),
            timeout=30
        )
        if r.status_code == 201:
            media = r.json()
            media_id = media.get('id')
            requests.post(
                f"{wp_config['url']}/wp-json/wp/v2/media/{media_id}",
                json={"alt_text": seo_tags.get('alt', ''),
                      "title": seo_tags.get('titre', ''),
                      "caption": seo_tags.get('caption', '')},
                auth=(wp_config['username'], wp_config['app_password'])
            )
            return {"success": True, "media_id": media_id, "url": media.get('source_url')}
        return {"success": False, "erreur": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"success": False, "erreur": str(e)}


def injecter_image_apres_h2(html_article, h2_texte, image_url, seo_tags):
    img_html = f'''
<figure class="wp-block-image size-large">
    <img src="{image_url}" alt="{seo_tags.get('alt','')}"
         title="{seo_tags.get('titre','')}" loading="lazy" decoding="async"/>
    <figcaption>{seo_tags.get('caption','')}</figcaption>
</figure>
'''
    pattern = re.compile(
        rf'(<h2[^>]*>.*?{re.escape(h2_texte[:30])}.*?</h2>)',
        re.IGNORECASE | re.DOTALL
    )
    return pattern.sub(r'\1' + img_html, html_article, count=1)


def nettoyer_et_generer_schemas(df_publications, wp_config, config):
    print("🎨 GÉNÉRATION SCHÉMAS SVG...")
    ROTATION_TYPES = ['flowchart', 'technique', 'comparatif']

    for _, row in df_publications.iterrows():
        silo_name = row['Silo']
        post_id = row['Post_ID']
        couleur = get_couleur_silo(str(silo_name))

        # Nettoyage
        r = requests.get(
            f"{wp_config['url']}/wp-json/wp/v2/posts/{post_id}",
            auth=(wp_config['username'], wp_config['app_password'])
        )
        if r.status_code != 200:
            continue
        contenu = r.json()['content']['rendered']
        contenu_propre = re.sub(r'<figure[^>]*>.*?</figure>', '', contenu, flags=re.DOTALL)
        requests.post(
            f"{wp_config['url']}/wp-json/wp/v2/posts/{post_id}",
            json={"content": contenu_propre},
            auth=(wp_config['username'], wp_config['app_password'])
        )

        html_article = contenu_propre
        soup = BeautifulSoup(html_article, 'html.parser')
        h2_liste = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
        html_enrichi = html_article
        images_generees = []

        print(f"\n📂 {silo_name} — {row['Titre'][:50]}")

        for i, h2_texte in enumerate(h2_liste[:6]):
            if len(images_generees) >= 3:
                break
            type_schema = ROTATION_TYPES[len(images_generees)]
            print(f"  🔍 H2 {i+1} : {h2_texte[:40]}... → {type_schema}")

            data = extraire_donnees_svg(html_article, h2_texte, type_schema, config)
            if not data:
                continue

            schema_index = len(images_generees)
            if type_schema == 'flowchart':
                svg_bytes = generer_flowchart_svg(
                    data.get('labels', []), data.get('descriptions', []),
                    couleur, schema_index
                )
            elif type_schema == 'comparatif':
                svg_bytes = generer_comparatif_svg(
                    data.get('items', []), data.get('criteres', []),
                    couleur, schema_index
                )
            else:
                svg_bytes = generer_technique_svg(
                    data.get('titre', h2_texte[:40]),
                    data.get('composants', []),
                    couleur, schema_index
                )

            seo_tags = {
                "alt": f"Schéma {type_schema} {silo_name} — {h2_texte[:60]}",
                "titre": f"{h2_texte[:60]}",
                "caption": f"Schéma : {h2_texte[:80]}"
            }
            filename = f"{re.sub(r'[^a-zA-Z0-9]','_',str(silo_name)[:20])}_{i+1}_{type_schema}.png"
            upload = upload_svg_wordpress(svg_bytes, filename, seo_tags, wp_config)

            if upload['success']:
                print(f"  ✅ {upload['url']}")
                html_enrichi = injecter_image_apres_h2(
                    html_enrichi, h2_texte, upload['url'], seo_tags
                )
                images_generees.append({"h2": h2_texte, "type": type_schema})

        if images_generees:
            requests.post(
                f"{wp_config['url']}/wp-json/wp/v2/posts/{post_id}",
                json={"content": html_enrichi},
                auth=(wp_config['username'], wp_config['app_password'])
            )
            print(f"  ✅ {len(images_generees)} schémas injectés")


# ============================================================
# CELLULE 11C — FEATURED IMAGE DALL-E
# ============================================================
def generer_prompt_dalle(mot_cle, sous_silo, silo_name, titre_article, config):
    prompt = f"""Génère un prompt gpt-image-1 pour illustrer :
- Titre : "{titre_article}"
- Mot-clé : "{mot_cle}"
- Sous-silo : "{sous_silo}"
RÈGLES : photo réaliste, équipement réel, contexte résidentiel français,
pas de texte visible, pas de personnes en premier plan.
JSON : {{"prompt_dalle":"prompt anglais 50-100 mots","description_fr":"description courte"}}"""

    headers = {
        "x-api-key": config['ANTHROPIC_API_KEY'],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json={"model": config['MODEL'], "max_tokens": 300,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30
        )
        contenu = r.json()['content'][0]['text'].strip()
        contenu = contenu.replace("```json", "").replace("```", "").strip()
        return json.loads(contenu)
    except:
        return {
            "prompt_dalle": f"Professional photo of {mot_cle} in a modern French home, photorealistic, no text",
            "description_fr": f"{mot_cle} - {sous_silo}"
        }


def generer_image_dalle(prompt_dalle, openai_config):
    headers = {
        "Authorization": f"Bearer {openai_config['api_key']}",
        "Content-Type": "application/json"
    }
    body = {
        "model": openai_config['model'],
        "prompt": prompt_dalle,
        "n": 1,
        "size": openai_config['size'],
        "quality": openai_config['quality'],
        "output_format": "png"
    }
    try:
        r = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers, json=body, timeout=60
        )
        if r.status_code == 401:
            return None, "❌ Clé OpenAI invalide"
        if r.status_code == 400:
            return None, f"❌ Prompt refusé : {r.json().get('error', {}).get('message', '')}"
        r.raise_for_status()
        image_b64 = r.json()['data'][0]['b64_json']
        return base64.b64decode(image_b64), None
    except Exception as e:
        return None, f"❌ Erreur : {e}"


def set_featured_image_wordpress(image_bytes, filename, seo_tags, post_id, wp_config):
    try:
        r = requests.post(
            f"{wp_config['url']}/wp-json/wp/v2/media",
            headers={"Content-Disposition": f'attachment; filename="{filename}"',
                     "Content-Type": "image/png"},
            data=image_bytes,
            auth=(wp_config['username'], wp_config['app_password']),
            timeout=60
        )
        if r.status_code != 201:
            return False, f"Upload échoué : HTTP {r.status_code}"
        media = r.json()
        media_id = media.get('id')
        requests.post(
            f"{wp_config['url']}/wp-json/wp/v2/media/{media_id}",
            json={"alt_text": seo_tags['alt'], "title": seo_tags['titre'],
                  "caption": seo_tags['caption']},
            auth=(wp_config['username'], wp_config['app_password'])
        )
        r_post = requests.post(
            f"{wp_config['url']}/wp-json/wp/v2/posts/{post_id}",
            json={"featured_media": media_id},
            auth=(wp_config['username'], wp_config['app_password'])
        )
        if r_post.status_code == 200:
            return True, {"media_id": media_id, "url": media.get('source_url')}
        return False, f"Set featured image échoué : {r_post.status_code}"
    except Exception as e:
        return False, str(e)


def generer_featured_images(df_publications, client_bq, config, openai_config, wp_config):
    print("🎨 FEATURED IMAGES DALL-E...")
    ids_utilises = set()
    try:
        df_ids = client_bq.query(f"""
        SELECT DISTINCT image_id FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE image_id IS NOT NULL AND image_id != ''
        """).to_dataframe()
        ids_utilises = set(df_ids['image_id'].tolist())
    except:
        pass

    for idx, row in df_publications.iterrows():
        post_id = row['Post_ID']
        silo_name = row['Silo']
        titre_article = row['Titre']

        soup = BeautifulSoup(row['Contenu_HTML'], 'html.parser')
        h1 = soup.find('h1')
        h1_texte = h1.get_text(strip=True) if h1 else titre_article

        # Récupérer mot-clé et sous-silo depuis BQ
        mot_cle_brief = row['Mot_cle']
        sous_silo = row.get('sous_silo', '')
        try:
            df_mk = client_bq.query(f"""
            SELECT mot_cle, sous_silo_strategique
            FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            WHERE post_id = {post_id} LIMIT 1
            """).to_dataframe()
            if not df_mk.empty:
                mot_cle_brief = str(df_mk['mot_cle'].iloc[0] or mot_cle_brief)
                sous_silo = str(df_mk['sous_silo_strategique'].iloc[0] or '')
        except:
            pass

        print(f"\n📂 {silo_name} | {sous_silo}")

        prompt_data = generer_prompt_dalle(mot_cle_brief, sous_silo, silo_name, h1_texte, config)
        image_bytes, erreur = generer_image_dalle(prompt_data['prompt_dalle'], openai_config)

        if not image_bytes:
            print(f"  ❌ {erreur}")
            continue

        seo_tags = {
            "alt": f"{mot_cle_brief} - {silo_name} - {datetime.now().year}",
            "titre": titre_article[:60],
            "caption": "Image générée par IA"
        }
        filename = f"dalle_{re.sub(r'[^a-zA-Z0-9]','_',sous_silo[:20])}_{post_id}.png"
        succes, resultat = set_featured_image_wordpress(
            image_bytes, filename, seo_tags, post_id, wp_config
        )

        if succes:
            image_id = f"dalle_{post_id}_{idx}"
            ids_utilises.add(image_id)
            try:
                client_bq.query(f"""
                UPDATE `{PROJECT_ID}.{DATASET_ID}.historique_publications`
                SET image_id = '{image_id}'
                WHERE post_id = {post_id}
                """).result()
            except:
                pass
            print(f"  ✅ {resultat['url']}")
        else:
            print(f"  ❌ {resultat}")


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================
def run_pipeline(force=False):
    print(f"\n{'='*60}")
    print("🚀 CME SEO AI PIPELINE")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}\n")

    # Init
    client_bq = init_bigquery()
    creer_table_historique(client_bq)

    # Vérification jour
    if not force and not est_jour_publication(CONFIG):
        print("⏸️ Pas un jour de publication. Utilisez force=True pour forcer.")
        return

    # ── ORCHESTRATEUR ─────────────────────────────────────
    print("\n📂 SÉLECTION DES SILOS...")
    silos_a_traiter = selectionner_silos_a_traiter(client_bq, CONFIG)
    if silos_a_traiter is None or silos_a_traiter.empty:
        print("❌ Aucun silo disponible")
        return

    # Vérification anti-doublons
    # Pas de filtre doublon par titre : la rotation gère la diversité
    silos_valides = list(silos_a_traiter.iterrows())
    if not silos_valides:
        print("⚠️ Aucun silo disponible")
        return
    # silos_a_traiter déjà prêt

    # ── SCRAPING ───────────────────────────────────────────
    print("\n🔎 SCRAPING CONCURRENTS...")
    df_market = scraper_concurrents(silos_a_traiter, SEARCH_API_KEY)
    if df_market.empty:
        print("❌ Aucun concurrent trouvé")
        return

    # ── EXTRACTION CONTENU ─────────────────────────────────
    print("\n📄 EXTRACTION CONTENU...")
    df_contenus = scraper_contenu_concurrents(df_market)
    if df_contenus.empty:
        print("❌ Aucun contenu extrait")
        return

    # ── ANALYSE STYLE ──────────────────────────────────────
    print("\n🧠 ANALYSE ÉDITORIALE...")
    df_analyses = analyser_contenus(df_contenus, CONFIG)

    # ── CONSOLIDATION ──────────────────────────────────────
    print("\n🔗 CONSOLIDATION...")
    df_final = consolider_briefs(df_analyses, df_contenus)

    # ── GÉNÉRATION BRIEFS ──────────────────────────────────
    print("\n✍️ GÉNÉRATION BRIEFS...")
    all_briefs_finaux = generer_tous_briefs(df_final, client_bq, CONFIG)
    if not all_briefs_finaux:
        print("❌ Aucun brief généré")
        return

    # ── EXPORT BIGQUERY ────────────────────────────────────
    print("\n💾 EXPORT BIGQUERY...")
    run_id = exporter_bigquery(df_final, all_briefs_finaux, client_bq)

    # ── RÉDACTION + PUBLICATION ────────────────────────────
    print("\n🚀 RÉDACTION + PUBLICATION...")
    df_publications = rediger_et_publier(
        all_briefs_finaux, silos_a_traiter,
        WP_CONFIG, client_bq, CONFIG, run_id
    )
    if df_publications.empty:
        print("❌ Aucun article publié")
        return

    # ── SCHÉMAS SVG ────────────────────────────────────────
    print("\n🎨 SCHÉMAS SVG...")
    nettoyer_et_generer_schemas(df_publications, WP_CONFIG, CONFIG)

    # ── FEATURED IMAGES ────────────────────────────────────
    print("\n🖼️ FEATURED IMAGES DALL-E...")
    generer_featured_images(df_publications, client_bq, CONFIG, OPENAI_CONFIG, WP_CONFIG)
    # ── PUBLICATION FACEBOOK ────────────────────────────────
    if CONFIG.get("FACEBOOK_INSTAGRAM_ACTIF", True):
        publier_tous_facebook(df_publications, client_bq, CONFIG, FACEBOOK_CONFIG)
        publier_tous_instagram(df_publications, client_bq, CONFIG, INSTAGRAM_CONFIG)
    else:
        print("⏭️  Facebook/Instagram desactives temporairement (FACEBOOK_INSTAGRAM_ACTIF=False)")
    notifier_nouveaux_articles(df_publications, CONFIG)

    print(f"\n{'='*60}")
    print(f"✅ PIPELINE TERMINÉ — {len(df_publications)} articles publiés")
    print(f"📅 Run ID : {run_id}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    run_pipeline(force=force)
