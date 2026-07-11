with open('pipeline.py', 'r') as f:
    content = f.read()

cta_function = '''
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
    "5. Electricite": {
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
    "2. Renovation Energetique": {
        "url": "https://www.comprendre-mon-energie.fr/simulateur-aides-renovation-energetique/",
        "titre": "Calculez vos aides a la renovation",
        "texte": "MaPrimeRenov', CEE, Eco-PTZ : estimez vos aides en 2 minutes, gratuitement.",
        "bouton": "Simuler mes aides",
        "couleur1": "#78350f", "couleur2": "#f59e0b"
    },
    "3. Aide Energetique": {
        "url": "https://www.comprendre-mon-energie.fr/simulateur-aides-renovation-energetique/",
        "titre": "Calculez vos aides a la renovation",
        "texte": "MaPrimeRenov', CEE, Eco-PTZ : estimez vos aides en 2 minutes, gratuitement.",
        "bouton": "Simuler mes aides",
        "couleur1": "#78350f", "couleur2": "#f59e0b"
    },
}

def generer_cta_html(silo_name):
    """Genere le bloc CTA HTML a injecter en fin d'article selon le silo."""
    cfg = CTA_TOOLS.get(silo_name)
    if not cfg:
        return ""
    return f\'\'\'
<div style="background:linear-gradient(135deg,{cfg["couleur1"]},{cfg["couleur2"]});border-radius:16px;padding:1.75rem;text-align:center;margin:32px 0;">
  <h3 style="color:#fff;font-size:20px;font-weight:700;margin:0 0 8px">{cfg["titre"]}</h3>
  <p style="color:rgba(255,255,255,.9);font-size:14px;margin:0 0 18px;line-height:1.5">{cfg["texte"]}</p>
  <a href="{cfg["url"]}" style="display:inline-block;background:#fff;color:{cfg["couleur2"]};font-size:15px;font-weight:700;padding:14px 32px;border-radius:10px;text-decoration:none;">{cfg["bouton"]} &rarr;</a>
</div>
\'\'\'

'''

marker = "def publier_article(brief, silo_name, sous_silo_val, contenu_html,"
if marker in content:
    content = content.replace(marker, cta_function + marker, 1)
    print("✅ Fonction CTA_TOOLS + generer_cta_html inseree")
else:
    print("❌ Marqueur publier_article non trouve")

old_inject = "    payload = {\n        \"title\": titre_seo,\n        \"content\": contenu_html,"
new_inject = "    contenu_html = contenu_html + generer_cta_html(silo_name)\n\n    payload = {\n        \"title\": titre_seo,\n        \"content\": contenu_html,"
if old_inject in content:
    content = content.replace(old_inject, new_inject, 1)
    print("✅ Injection CTA dans le payload de publication")
else:
    print("❌ Pattern payload non trouve")

with open('pipeline.py', 'w') as f:
    f.write(content)

with open('pipeline.py') as f: c = f.read()
print(f"\nCTA_TOOLS present: {'CTA_TOOLS' in c}")
print(f"generer_cta_html present: {'generer_cta_html' in c}")
print(f"Injection dans publier_article: {'contenu_html = contenu_html + generer_cta_html' in c}")
