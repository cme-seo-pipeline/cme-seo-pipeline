FICHIER = "wordpress-plugins/comparateur-energie/comparateur-energie.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = r"""function showLeadSuccess(){
  var form=document.getElementById(UID+'-lmform');
  if(form){
    var prn=(document.getElementById(UID+'-lm-prn')||{}).value||'';
    var nom=(document.getElementById(UID+'-lm-nom')||{}).value||'';
    var mail=(document.getElementById(UID+'-lm-mail')||{}).value||'';
    var tel=(document.getElementById(UID+'-lm-tel')||{}).value||'';
    var srcPost=new URLSearchParams(window.location.search).get('src_post')||'';
    var ctx=LEAD_CTX||{};
    var leadData={
      tool:'comparateur-energie',
      source_post_id:srcPost,
      montant_estime:ctx.prix_annuel||0,
      economie_estimee:ctx.economie||0,
      details:{energie:ctx.energie||'',fournisseur:ctx.fournisseur||'',offre:ctx.offre||'',kwh:ctx.kwh||0,option_tarifaire:ctx.option_tarifaire||''}
    };
    var lienCompte='https://espace-client.comprendre-mon-energie.fr/register?prenom='
      +encodeURIComponent(prn)+'&nom='+encodeURIComponent(nom)+'&email='+encodeURIComponent(mail)+'&telephone='+encodeURIComponent(tel)
      +'&lead_data='+encodeURIComponent(JSON.stringify(leadData));
    form.innerHTML='<div style="text-align:center;padding:20px 10px">'
      +'<div style="width:52px;height:52px;border-radius:50%;background:#d1fae5;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">\u2713</div>'
      +'<div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoy\u00e9e !</div>'
      +'<div style="font-size:13px;color:#6b7280;line-height:1.5">Nous vous recontactons sous 48h.<br>L\'offre du fournisseur s\'est ouverte dans un nouvel onglet.</div>'
      +'<a href="'+lienCompte+'" target="_blank" style="display:inline-block;margin-top:16px;background:#3b82f6;color:#fff;font-weight:600;padding:12px 24px;border-radius:10px;text-decoration:none;font-size:14px">Créer mon espace client &rarr;</a>'
      +'</div>';
  }
  setTimeout(closeLeadModal,6000);
}"""

nouveau = r"""function showLeadSuccess(){
  var form=document.getElementById(UID+'-lmform');
  if(form){
    var prn=(document.getElementById(UID+'-lm-prn')||{}).value||'';
    var nom=(document.getElementById(UID+'-lm-nom')||{}).value||'';
    var mail=(document.getElementById(UID+'-lm-mail')||{}).value||'';
    var tel=(document.getElementById(UID+'-lm-tel')||{}).value||'';
    var srcPost=new URLSearchParams(window.location.search).get('src_post')||'';
    var ctx=LEAD_CTX||{};
    var leadData={
      tool:'comparateur-energie',
      source_post_id:srcPost,
      montant_estime:ctx.prix_annuel||0,
      economie_estimee:ctx.economie||0,
      details:{energie:ctx.energie||'',fournisseur:ctx.fournisseur||'',offre:ctx.offre||'',kwh:ctx.kwh||0,option_tarifaire:ctx.option_tarifaire||''}
    };
    if(window.CME_APP_TOKEN){
      fetch('https://cme-client-api-217943559750.europe-west1.run.app/leads',{
        method:'POST',
        headers:{'Authorization':'Bearer '+window.CME_APP_TOKEN,'Content-Type':'application/json'},
        body:JSON.stringify(leadData)
      }).catch(function(){});
      form.innerHTML='<div style="text-align:center;padding:20px 10px">'
        +'<div style="width:52px;height:52px;border-radius:50%;background:#d1fae5;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">\u2713</div>'
        +'<div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoy\u00e9e !</div>'
        +'<div style="font-size:13px;color:#6b7280;line-height:1.5">Ajout\u00e9e \u00e0 vos dossiers dans l\'app.<br>Nous vous recontactons sous 48h.</div>'
        +'</div>';
    }else{
      var lienCompte='https://espace-client.comprendre-mon-energie.fr/register?prenom='
        +encodeURIComponent(prn)+'&nom='+encodeURIComponent(nom)+'&email='+encodeURIComponent(mail)+'&telephone='+encodeURIComponent(tel)
        +'&lead_data='+encodeURIComponent(JSON.stringify(leadData));
      form.innerHTML='<div style="text-align:center;padding:20px 10px">'
        +'<div style="width:52px;height:52px;border-radius:50%;background:#d1fae5;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">\u2713</div>'
        +'<div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoy\u00e9e !</div>'
        +'<div style="font-size:13px;color:#6b7280;line-height:1.5">Nous vous recontactons sous 48h.<br>L\'offre du fournisseur s\'est ouverte dans un nouvel onglet.</div>'
        +'<a href="'+lienCompte+'" target="_blank" style="display:inline-block;margin-top:16px;background:#3b82f6;color:#fff;font-weight:600;padding:12px 24px;border-radius:10px;text-decoration:none;font-size:14px">Créer mon espace client &rarr;</a>'
        +'</div>';
    }
  }
  setTimeout(closeLeadModal,6000);
}"""

if "window.CME_APP_TOKEN" in contenu:
    print("⏭️  PATCH (comparateur) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (comparateur) : bloc non trouve")
else:
    contenu = contenu.replace(ancien, nouveau)
    print("✅ PATCH (comparateur) : pont vers /leads ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
