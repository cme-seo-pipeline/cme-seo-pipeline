FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''    maintenant = datetime.now()
    mois_annee = f"{MOIS_FR[maintenant.month]} {maintenant.year}"
    variation = changement['variation_pct']
    sens = "hausse" if variation > 0 else "baisse"
    source_officielle = "ANAH" if changement['domaine'] == 'Aides' else "CRE"
    titre = f"{sous_silo} : {sens} de {abs(variation):.1f}% en {mois_annee}"[:60]
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
            f"{changement['date_debut_validite']}. Source officielle : {source_officielle} "
            f"uniquement — ne pas attribuer ce chiffre a un autre organisme."
        ),'''

nouveau = '''    maintenant = datetime.now()
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
        ),'''

if "valeur_actuelle_r = round" in contenu:
    print("⏭️  PATCH (arrondi + meta description) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (arrondi + meta description) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (arrondi + meta description) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
