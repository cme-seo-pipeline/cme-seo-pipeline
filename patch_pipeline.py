import re

FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — CTA : clearfix anti-chevauchement avec tableau
# ============================================================
ancien_cta = '''def generer_cta_html(silo_name, post_id=None):
    """Genere le bloc CTA HTML a injecter en fin d'article selon le silo.
    Si post_id est fourni, ajoute ?src_post={post_id} au lien pour tracer
    l'attribution article -> clic -> lead jusqu'a BigQuery."""
    cfg = CTA_TOOLS.get(silo_name)
    if not cfg:
        return ""
    url_finale = cfg["url"]
    if post_id:
        sep = '&' if '?' in url_finale else '?'
        url_finale = f"{url_finale}{sep}src_post={post_id}"
    return f\'\'\'
<div style="background:linear-gradient(135deg,{cfg["couleur1"]},{cfg["couleur2"]});border-radius:16px;padding:1.75rem;text-align:center;margin:32px 0;">
  <h3 style="color:#fff;font-size:20px;font-weight:700;margin:0 0 8px">{cfg["titre"]}</h3>
  <p style="color:rgba(255,255,255,.9);font-size:14px;margin:0 0 18px;line-height:1.5">{cfg["texte"]}</p>
  <a href="{url_finale}" style="display:inline-block;background:#fff;color:{cfg["couleur2"]};font-size:15px;font-weight:700;padding:14px 32px;border-radius:10px;text-decoration:none;">{cfg["bouton"]} &rarr;</a>
</div>
\'\'\''''

nouveau_cta = '''def generer_cta_html(silo_name, post_id=None):
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
    return f\'\'\'
<div style="clear:both;overflow:hidden;"></div>
<div style="background:linear-gradient(135deg,{cfg["couleur1"]},{cfg["couleur2"]});border-radius:16px;padding:1.75rem;text-align:center;margin:32px 0;max-width:100%;box-sizing:border-box;">
  <h3 style="color:#fff;font-size:20px;font-weight:700;margin:0 0 8px">{cfg["titre"]}</h3>
  <p style="color:rgba(255,255,255,.9);font-size:14px;margin:0 0 18px;line-height:1.5">{cfg["texte"]}</p>
  <a href="{url_finale}" style="display:inline-block;background:#fff;color:{cfg["couleur2"]};font-size:15px;font-weight:700;padding:14px 32px;border-radius:10px;text-decoration:none;">{cfg["bouton"]} &rarr;</a>
</div>
\'\'\''''

if ancien_cta not in contenu:
    print("❌ PATCH 1 (CTA) : bloc de recherche non trouve, aucune modification")
else:
    contenu = contenu.replace(ancien_cta, nouveau_cta)
    print("✅ PATCH 1 (CTA) : clearfix ajoute")

# ============================================================
# PATCH 2a — Prompt : instructions titre/meta plus precises
# ============================================================
ancien_prompt = '''  "titre_seo": "titre H1 MAX 60 caractères",
  "meta_description": "meta MAX 160 caractères",'''

nouveau_prompt = '''  "titre_seo": "titre SEO percutant, ENTRE 50 ET 60 CARACTERES pile (jamais plus, jamais moins de 50), phrase ou expression complete, ne JAMAIS couper un mot en cours de generation",
  "meta_description": "meta description incitant au clic, ENTRE 150 ET 160 CARACTERES pile (jamais plus, jamais moins de 150), phrase complete se terminant par un point, ne JAMAIS couper un mot en cours de generation",'''

if ancien_prompt not in contenu:
    print("❌ PATCH 2a (prompt) : bloc de recherche non trouve, aucune modification")
else:
    contenu = contenu.replace(ancien_prompt, nouveau_prompt)
    print("✅ PATCH 2a (prompt) : instructions SEO renforcees")

# ============================================================
# PATCH 2b — Troncature de secours au mot le plus proche
# ============================================================
ancienne_troncature = '''    titre_seo = brief.get('titre_seo', '')[:60]
    meta_desc = brief.get('meta_description', '')[:160]'''

nouvelle_troncature = '''    titre_seo = tronquer_proprement(brief.get('titre_seo', ''), 60)
    meta_desc = tronquer_proprement(brief.get('meta_description', ''), 160)'''

if ancienne_troncature not in contenu:
    print("❌ PATCH 2b (troncature) : bloc de recherche non trouve, aucune modification")
else:
    contenu = contenu.replace(ancienne_troncature, nouvelle_troncature)
    print("✅ PATCH 2b (troncature) : appel a tronquer_proprement()")

# ============================================================
# PATCH 2c — Ajout de la fonction tronquer_proprement()
# (inseree juste avant generer_cta_html)
# ============================================================
ancre_insertion = "def generer_cta_html(silo_name, post_id=None):"

fonction_helper = '''def tronquer_proprement(texte, limite):
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


''' + ancre_insertion

if ancre_insertion not in contenu:
    print("❌ PATCH 2c (fonction helper) : point d'insertion non trouve, aucune modification")
elif "def tronquer_proprement(" in contenu:
    print("⏭️  PATCH 2c (fonction helper) : deja presente, ignoree")
else:
    contenu = contenu.replace(ancre_insertion, fonction_helper, 1)
    print("✅ PATCH 2c (fonction helper) : tronquer_proprement() ajoutee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("\n📝 Fichier sauvegarde :", FICHIER)
