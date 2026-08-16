FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def recuperer_donnees_officielles(silo, sous_silo, client_bq):"

nouvelles_fonctions = '''def construire_brief_actualite(changement, client_bq):
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
    mois_annee = datetime.now().strftime("%B %Y")
    variation = changement['variation_pct']
    sens = "hausse" if variation > 0 else "baisse"
    titre = f"{sous_silo} {mois_annee} : {sens} de {abs(variation):.1f}%"[:60]
    return {
        "silo": silo,
        "sous_silo": sous_silo,
        "titre_seo": titre,
        "mot_cle_principal": f"{sous_silo.lower()} {mois_annee.lower()}",
        "mots_cles_secondaires": [indicateur, "prix", mois_annee.lower(), sens],
        "volume_recommande": 800,
        "ton_recommande": "actualité, factuel, direct",
        "angle_differentiant": (
            f"Article d'actualité annonçant un changement officiel recemment "
            f"constate : {indicateur} passe de {changement['valeur_precedente']} "
            f"a {changement['valeur_actuelle']} {changement['unite']} "
            f"({sens} de {abs(variation):.1f}%), effectif depuis le "
            f"{changement['date_debut_validite']}. Source : CRE/ANAH."
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
    sur le sujet plutot que de suivre la concurrence."""
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
    publications = []
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
            publications.append(resultat)
        else:
            print(f"  ❌ {resultat.get('erreur')}")
    print(f"📰 MODE ACTUALITE termine : {len(publications)} article(s) publie(s)")
    return publications


def recuperer_donnees_officielles(silo, sous_silo, client_bq):'''

if "def construire_brief_actualite" in contenu:
    print("⏭️  PATCH (Mode Actualite) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (Mode Actualite) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelles_fonctions, 1)
    print("✅ PATCH (Mode Actualite) : construire_brief_actualite + publier_actualites_reglementaires ajoutees")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
