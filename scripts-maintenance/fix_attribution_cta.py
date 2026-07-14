with open('pipeline.py', 'r') as f:
    content = f.read()

# ── 1. generer_cta_html accepte maintenant un post_id optionnel ────────────
old_fn = '''def generer_cta_html(silo_name):
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
\'\'\''''

new_fn = '''def generer_cta_html(silo_name, post_id=None):
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

if old_fn in content:
    content = content.replace(old_fn, new_fn, 1)
    print("✅ 1/3 generer_cta_html accepte post_id")
else:
    print("❌ 1/3 Pattern non trouvé")

# ── 2. Retirer l'injection prématurée du CTA (avant publication) ───────────
old_premature = "    contenu_html = contenu_html + generer_cta_html(silo_name)\n    payload = {"
new_premature = "    payload = {"
if old_premature in content:
    content = content.replace(old_premature, new_premature, 1)
    print("✅ 2/3 Injection prématurée retirée")
else:
    print("❌ 2/3 Pattern non trouvé")

# ── 3. Ajouter le PATCH post-publication avec le CTA + post_id ─────────────
old_success = '''        if r.status_code == 201:
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
            return {"success": True, "post_id": post_id, "url": url_wp}'''

new_success = '''        if r.status_code == 201:
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
            return {"success": True, "post_id": post_id, "url": url_wp}'''

if old_success in content:
    content = content.replace(old_success, new_success, 1)
    print("✅ 3/3 PATCH post-publication ajouté")
else:
    print("❌ 3/3 Pattern non trouvé")

with open('pipeline.py', 'w') as f:
    f.write(content)
