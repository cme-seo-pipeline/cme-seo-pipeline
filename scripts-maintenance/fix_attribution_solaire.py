with open('wordpress-plugins/simulateur-solaire/simulateur-solaire.php', 'r') as f:
    content = f.read()

# 1. Injection dans le payload JS
old_js = """    // Source calcul
    pvgis_utilise:S.pvgis_prod&&S.pvgis_prod>0?'Oui (satellite)':'Non (estimation)',
    timestamp:new Date().toISOString()
  };"""
new_js = """    // Source calcul
    pvgis_utilise:S.pvgis_prod&&S.pvgis_prod>0?'Oui (satellite)':'Non (estimation)',
    timestamp:new Date().toISOString(),
    src_post:new URLSearchParams(window.location.search).get('src_post')||''
  };"""
if old_js in content:
    content = content.replace(old_js, new_js, 1)
    print("✅ 1/2 Solaire JS patché")
else:
    print("❌ 1/2 Solaire JS non trouvé")

# 2. Relais PHP vers log-lead
old_php = """      'details' => array('surface'=>$sf,'orientation'=>$ori,'chauffage'=>$ch,'nb_panneaux'=>$nb,'kwc'=>$kwc,'production'=>$prod,'roi'=>$roi,'co2'=>$co2),
      'source_page' => 'devis-panneau-solaire'"""
new_php = """      'details' => array('surface'=>$sf,'orientation'=>$ori,'chauffage'=>$ch,'nb_panneaux'=>$nb,'kwc'=>$kwc,'production'=>$prod,'roi'=>$roi,'co2'=>$co2),
      'source_page' => 'devis-panneau-solaire',
      'source_post_id' => sanitize_text_field($data['src_post'] ?? '')"""
if old_php in content:
    content = content.replace(old_php, new_php, 1)
    print("✅ 2/2 Solaire PHP patché")
else:
    print("❌ 2/2 Solaire PHP non trouvé")

with open('wordpress-plugins/simulateur-solaire/simulateur-solaire.php', 'w') as f:
    f.write(content)
