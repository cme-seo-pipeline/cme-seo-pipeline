with open('simulateur-aides/simulateur-aides.php', 'r') as f:
    content = f.read()

old = """function showLeadSuccess(){
  var form=document.getElementById(UID+'-lmform');
  if(form){form.innerHTML='<div style="text-align:center;padding:20px 10px"><div style="width:52px;height:52px;border-radius:50%;background:#dcfce7;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">✓</div><div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoyée !</div><div style="font-size:13px;color:#6b7280;line-height:1.5">Un conseiller vous recontacte sous 48h.</div></div>';}
  setTimeout(closeLeadModal,2200);
}"""

new = """function showLeadSuccess(){
  var form=document.getElementById(UID+'-lmform');
  if(form){
    var prn=(document.getElementById(UID+'-lm-prn')||{}).value||'';
    var nom=(document.getElementById(UID+'-lm-nom')||{}).value||'';
    var mail=(document.getElementById(UID+'-lm-mail')||{}).value||'';
    var tel=(document.getElementById(UID+'-lm-tel')||{}).value||'';
    var lienCompte='https://espace-client-217943559750.europe-west1.run.app/register?prenom='
      +encodeURIComponent(prn)+'&nom='+encodeURIComponent(nom)+'&email='+encodeURIComponent(mail)+'&telephone='+encodeURIComponent(tel);
    form.innerHTML='<div style="text-align:center;padding:20px 10px"><div style="width:52px;height:52px;border-radius:50%;background:#dcfce7;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">✓</div><div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoyée !</div><div style="font-size:13px;color:#6b7280;line-height:1.5">Un conseiller vous recontacte sous 48h.</div>'
      +'<a href="'+lienCompte+'" target="_blank" style="display:inline-block;margin-top:16px;background:#f59e0b;color:#fff;font-weight:600;padding:12px 24px;border-radius:10px;text-decoration:none;font-size:14px">Créer mon espace client &rarr;</a></div>';
  }
  setTimeout(closeLeadModal,6000);
}"""

if old in content:
    content = content.replace(old, new, 1)
    print("✅ Patch aides appliqué")
else:
    print("❌ Pattern non trouvé")

with open('simulateur-aides/simulateur-aides.php', 'w') as f:
    f.write(content)
