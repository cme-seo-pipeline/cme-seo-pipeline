#!/usr/bin/env python3
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
    "JOURS_PUBLICATION": [1, 3, 5],  # Mardi, Jeudi, Samedi
    "heure_publication": 8,
    "nb_articles_par_run": 5,
    "fenetre_anti_doublon_jours": 90,
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
    date_limite = (datetime.now() - timedelta(
        days=config['fenetre_anti_doublon_jours']
    )).strftime('%Y-%m-%d')
    query = f"""
    SELECT COUNT(*) as nb
    FROM `{PROJECT_ID}.{DATASET_ID}.briefs_editoriaux`
    WHERE (
        LOWER(titre_seo) LIKE LOWER('%{titre[:20]}%')
        OR LOWER(mot_cle_principal) = LOWER('{mot_cle}')
    )
    AND date_run >= '{date_limite}'
    """
    try:
        result = client_bq.query(query).to_dataframe()
        return result['nb'].iloc[0] > 0
    except:
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
    try:
        df_traites = client_bq.query("""
        SELECT DISTINCT silo, sous_silo_strategique
        FROM `seo-data-hub-cme.04_pipeline_seo.historique_publications`
        WHERE sous_silo_strategique IS NOT NULL AND sous_silo_strategique != ''
        AND date_publication >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        """).to_dataframe()

        df_strategie = client_bq.query("""
        SELECT silo, sous_silo, priorite
        FROM `seo-data-hub-cme.04_pipeline_seo.sous_silos_strategiques`
        ORDER BY silo ASC, priorite ASC
        """).to_dataframe()

        if not df_traites.empty:
            combos_traites = set(zip(df_traites['silo'], df_traites['sous_silo_strategique']))
            df_strategie['combo'] = list(zip(df_strategie['silo'], df_strategie['sous_silo']))
            df_vierges = df_strategie[~df_strategie['combo'].isin(combos_traites)].drop(columns=['combo'])
            df_deja_traites = df_strategie[df_strategie['combo'].isin(combos_traites)].drop(columns=['combo'])
        else:
            df_vierges = df_strategie.copy()
            df_deja_traites = df_strategie.iloc[0:0]
        if not df_vierges.empty:
            df_disponibles = df_vierges
            print(f"   → {len(df_vierges)} sous-silos vierges (priorité absolue)")
        else:
            df_disponibles = df_deja_traites
            print("♻️ Tous couverts — nouveaux angles")
        if df_disponibles.empty:
            print("♻️ CYCLE COMPLET — Réinitialisation")
            df_disponibles = df_strategie
        df_selection = df_disponibles.sort_values(
            by=['silo', 'priorite']
        ).drop_duplicates(subset=['silo'], keep='first')
        df_final = df_selection.head(config.get('nb_articles_par_run', 5))

        print(f"✅ {len(df_final)} silos sélectionnés :")
        for _, row in df_final.iterrows():
            print(f"   → {row['silo']} | {row['sous_silo']} (priorité {row['priorite']})")

        return df_final

    except Exception as e:
        print(f"❌ Erreur sélection silos : {e}")
        return None


# ============================================================
# CELLULE 4 — SCRAPING SEARCHAPI
# ============================================================
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
        try:
            response = requests.get(
                "https://www.searchapi.io/api/v1/search",
                params=params, timeout=30
            )
            organic_results = response.json().get("organic_results", [])
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
        except Exception as e:
            print(f"❌ Erreur scraping : {e}")

    df_market = pd.DataFrame(all_market_data)
    df_market = df_market.groupby('Silo').head(5)
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


def generer_brief_silo(contexte, config, titres_existants=None):
    silo = contexte.get('silo', '')
    sous_silo = contexte.get('sous_silo', '')
    silo_propre = silo.split('. ')[-1] if '. ' in silo else silo
    slug_silo = to_slug(silo_propre)
    slug_sous_silo = to_slug(sous_silo)

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
  "titre_seo": "titre H1 MAX 60 caractères",
  "meta_description": "meta MAX 160 caractères",
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
            all_briefs_finaux[silo_name] = brief
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
    for silo_name, brief in all_briefs_finaux.items():
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
def rediger_article(brief, config, articles_silo=None):
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

    prompt = f"""Tu es un rédacteur SEO expert spécialisé dans l'énergie en France.
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

RÈGLES :
1. HTML propre (h1, h2, h3, p, ul, li, strong)
2. NE PAS ajouter de CTA commercial
3. Dates : {annee_courante} ou {annee_suivante} uniquement — INTERDIT {annee_interdite}
4. Commence DIRECTEMENT par <h1>...</h1>
5. INTERDIT : ```html, <!DOCTYPE>, <html>, <head>, <body>"""

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
                         headers=headers, json=body, timeout=120)
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
    try:
        df_check = client_bq.query(f"""
        SELECT COUNT(*) as nb
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE post_id = {post_id}
        """).to_dataframe()

        if df_check['nb'].iloc[0] > 0:
            query = f"""
            UPDATE `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            SET date_publication = CURRENT_TIMESTAMP(),
                silo = '{silo.replace("'", "''")}',
                titre = '{titre.replace("'", "''")}',
                mot_cle = '{mot_cle.replace("'", "''")}',
                url_wp = '{url_wp}',
                run_id = '{run_id}',
                sous_silo_strategique = '{sous_silo_strategique}',
                image_id = {"'" + image_id + "'" if image_id else 'NULL'}
            WHERE post_id = {post_id}
            """
        else:
            query = f"""
            INSERT INTO `{PROJECT_ID}.{DATASET_ID}.historique_publications`
            (date_publication, post_id, silo, titre, mot_cle,
             url_wp, run_id, sous_silo_strategique, image_id)
            VALUES (CURRENT_TIMESTAMP(), {post_id},
                '{silo.replace("'", "''")}',
                '{titre.replace("'", "''")}',
                '{mot_cle.replace("'", "''")}',
                '{url_wp}', '{run_id}',
                '{sous_silo_strategique.replace("'", "''")}',
                {"'" + image_id + "'" if image_id else 'NULL'})
            """
        client_bq.query(query).result()
        return True
    except Exception as e:
        print(f"  ⚠️ Log BQ échoué : {e}")
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

    titre_seo = brief.get('titre_seo', '')[:60]
    meta_desc = brief.get('meta_description', '')[:160]

    # Catégories
    silo_propre = silo_name.split('. ')[-1] if '. ' in silo_name else silo_name
    cat_parent_id = get_ou_creer_categorie(silo_propre, 0, wp_config)
    if sous_silo_val and str(sous_silo_val) != 'nan':
        cat_enfant_id = get_ou_creer_categorie(sous_silo_val, cat_parent_id, wp_config)
        categories_ids = [cat_enfant_id]
    else:
        categories_ids = [cat_parent_id]

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

    for silo_name, brief in all_briefs_finaux.items():
        print(f"\n{'='*55}")
        print(f"📂 {silo_name} — {brief.get('titre_seo')}")

        articles_silo = recuperer_articles_meme_silo(silo_name, wp_config)
        contenu_html, erreur = rediger_article(brief, config, articles_silo)
        if erreur:
            print(f"  {erreur}")
            continue

        liens = re.findall(
            r'<a href="https://www\.comprendre-mon-energie\.fr[^"]*"', contenu_html
        )
        nb_mots = len(re.sub(r'<[^>]+>', '', contenu_html).split())
        print(f"  🔗 {len(liens)} liens internes | {nb_mots} mots")

        try:
            sous_silo_val = silos_df[silos_df['silo'] == silo_name]['sous_silo'].iloc[0]
            if pd.isna(sous_silo_val):
                sous_silo_val = ''
        except:
            sous_silo_val = ''

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
    silos_valides = []
    for _, row in silos_a_traiter.iterrows():
        if not verifier_doublons(row['silo'], row['sous_silo'], client_bq, CONFIG):
            silos_valides.append(row)
    if not silos_valides:
        print("⚠️ Tous les silos sont des doublons")
        return
    silos_a_traiter = pd.DataFrame(silos_valides)

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

    print(f"\n{'='*60}")
    print(f"✅ PIPELINE TERMINÉ — {len(df_publications)} articles publiés")
    print(f"📅 Run ID : {run_id}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    run_pipeline(force=force)
