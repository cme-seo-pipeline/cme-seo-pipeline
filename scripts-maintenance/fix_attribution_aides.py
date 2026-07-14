with open('wordpress-plugins/simulateur-aides/simulateur-aides.php', 'r') as f:
    content = f.read()

old_js = "  var data=Object.assign({prenom:prn.trim(),nom:nom.trim(),email:mail.trim(),telephone:tel.trim(),adresse:S.adresse},LEAD_CTX);"
new_js = "  var data=Object.assign({prenom:prn.trim(),nom:nom.trim(),email:mail.trim(),telephone:tel.trim(),adresse:S.adresse,src_post:new URLSearchParams(window.location.search).get('src_post')||''},LEAD_CTX);"
if old_js in content:
    content = content.replace(old_js, new_js, 1)
    print("✅ 1/2 Aides JS patché")
else:
    print("❌ 1/2 Aides JS non trouvé")

old_php = """      'details' => array('profil'=>$profil,'travaux'=>$travaux,'montant_mpr'=>$mpr,'montant_cee'=>$cee,'reste_a_charge'=>$reste),
      'source_page' => 'simulateur-aides-renovation-energetique'"""
new_php = """      'details' => array('profil'=>$profil,'travaux'=>$travaux,'montant_mpr'=>$mpr,'montant_cee'=>$cee,'reste_a_charge'=>$reste),
      'source_page' => 'simulateur-aides-renovation-energetique',
      'source_post_id' => sanitize_text_field($data['src_post'] ?? '')"""
if old_php in content:
    content = content.replace(old_php, new_php, 1)
    print("✅ 2/2 Aides PHP patché")
else:
    print("❌ 2/2 Aides PHP non trouvé")

with open('wordpress-plugins/simulateur-aides/simulateur-aides.php', 'w') as f:
    f.write(content)
