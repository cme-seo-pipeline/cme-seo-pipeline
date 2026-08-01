FICHIER = "wordpress-plugins/simulateur-aides/simulateur-aides.php"

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
      tool:'aides-renovation',
      source_post_id:srcPost,
      montant_estime:ctx.total_aides||0,
      economie_estimee:0,
      details:{profil:ctx.profil||'',travaux:ctx.travaux||'',montant_mpr:ctx.montant_mpr||0,montant_cee:ctx.montant_cee||0,reste_a_charge:ctx.reste_a_charge||0,budget:ctx.budget||0}
    };
    var lienCompte='https://espace-client.comprendre-mon-energie.fr/register?prenom='
      +encodeURIComponent(prn)+'&nom='+encodeURIComponent(nom)+'&email='+encodeURIComponent(mail)+'&telephone='+encodeURIComponent(tel)
      +'&lead_data='+encodeURIComponent(JSON.stringify(leadData));
    form.innerHTML='<div style="text-align:center;padding:20px 10px"><div style="width:52px;height:52px;border-radius:50%;background:#dcfce7;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">✓</div><div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoyée !</div><div style="font-size:13px;color:#6b7280;line-height:1.5">Un conseiller vous recontacte sous 48h.</div>'
      +'<a href="'+lienCompte+'" target="_blank" style="display:inline-block;margin-top:16px;background:#f59e0b;color:#fff;font-weight:600;padding:12px 24px;border-radius:10px;text-decoration:none;font-size:14px">Créer mon espace client &rarr;</a></div>';
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
      tool:'aides-renovation',
      source_post_id:srcPost,
      montant_estime:ctx.total_aides||0,
      economie_estimee:0,
      details:{profil:ctx.profil||'',travaux:ctx.travaux||'',montant_mpr:ctx.montant_mpr||0,montant_cee:ctx.montant_cee||0,reste_a_charge:ctx.reste_a_charge||0,budget:ctx.budget||0}
    };
    if(window.CME_APP_TOKEN){
      fetch('https://cme-client-api-217943559750.europe-west1.run.app/leads',{
        method:'POST',
        headers:{'Authorization':'Bearer '+window.CME_APP_TOKEN,'Content-Type':'application/json'},
        body:JSON.stringify(leadData)
      }).catch(function(){});
      form.innerHTML='<div style="text-align:center;padding:20px 10px"><div style="width:52px;height:52px;border-radius:50%;background:#dcfce7;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">✓</div><div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoyée !</div><div style="font-size:13px;color:#6b7280;line-height:1.5">Ajoutée à vos dossiers dans l\'app.</div></div>';
    }else{
      var lienCompte='https://espace-client.comprendre-mon-energie.fr/register?prenom='
        +encodeURIComponent(prn)+'&nom='+encodeURIComponent(nom)+'&email='+encodeURIComponent(mail)+'&telephone='+encodeURIComponent(tel)
        +'&lead_data='+encodeURIComponent(JSON.stringify(leadData));
      form.innerHTML='<div style="text-align:center;padding:20px 10px"><div style="width:52px;height:52px;border-radius:50%;background:#dcfce7;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">✓</div><div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoyée !</div><div style="font-size:13px;color:#6b7280;line-height:1.5">Un conseiller vous recontacte sous 48h.</div>'
        +'<a href="'+lienCompte+'" target="_blank" style="display:inline-block;margin-top:16px;background:#f59e0b;color:#fff;font-weight:600;padding:12px 24px;border-radius:10px;text-decoration:none;font-size:14px">Créer mon espace client &rarr;</a></div>';
    }
  }
  setTimeout(closeLeadModal,6000);
}"""

if "window.CME_APP_TOKEN" in contenu:
    print("⏭️  PATCH (aides) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (aides) : bloc non trouve")
else:
    contenu = contenu.replace(ancien, nouveau)
    print("✅ PATCH (aides) : pont vers /leads ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
