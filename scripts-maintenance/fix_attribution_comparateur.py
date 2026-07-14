with open('wordpress-plugins/comparateur-energie/comparateur-energie.php', 'r') as f:
    content = f.read()

old_js = """  var data=Object.assign({
    prenom:prn.trim(),nom:nom.trim(),email:mail.trim(),telephone:tel.trim(),
    logement:S.logement,surface:S.surface,personnes:S.personnes,chauffage:S.chauffage,
    codepostal:S.codepostal,pdl:S.pdl,pce:S.pce
  },LEAD_CTX);"""
new_js = """  var data=Object.assign({
    prenom:prn.trim(),nom:nom.trim(),email:mail.trim(),telephone:tel.trim(),
    logement:S.logement,surface:S.surface,personnes:S.personnes,chauffage:S.chauffage,
    codepostal:S.codepostal,pdl:S.pdl,pce:S.pce,
    src_post:new URLSearchParams(window.location.search).get('src_post')||''
  },LEAD_CTX);"""
if old_js in content:
    content = content.replace(old_js, new_js, 1)
    print("✅ 1/2 Comparateur JS patché")
else:
    print("❌ 1/2 Comparateur JS non trouvé")

old_php = """      'details' => array('energie'=>$energie,'fournisseur'=>$fourn,'offre'=>$offre,'kwh'=>$kwh,'option_tarifaire'=>$opt,'lien_offre'=>$lien),
      'source_page' => 'comparateur-energie-electricite-gaz'"""
new_php = """      'details' => array('energie'=>$energie,'fournisseur'=>$fourn,'offre'=>$offre,'kwh'=>$kwh,'option_tarifaire'=>$opt,'lien_offre'=>$lien),
      'source_page' => 'comparateur-energie-electricite-gaz',
      'source_post_id' => sanitize_text_field($data['src_post'] ?? '')"""
if old_php in content:
    content = content.replace(old_php, new_php, 1)
    print("✅ 2/2 Comparateur PHP patché")
else:
    print("❌ 2/2 Comparateur PHP non trouvé")

with open('wordpress-plugins/comparateur-energie/comparateur-energie.php', 'w') as f:
    f.write(content)
