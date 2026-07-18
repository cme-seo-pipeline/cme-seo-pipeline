with open('simulateur-solaire/simulateur-solaire.php', 'r') as f:
    content = f.read()

old = """function showSuccess(){
  var form=$g('mform');
  if(form){
    var mail=($g('f-mail')||{}).value||'';
    form.innerHTML='<div class="modal-ok"><div class="ok-ico">✓</div><h4>Demande envoyée !</h4><p>Nous vous contactons sous 48h à l\\'adresse<br><strong>'+mail+'</strong><br><br>Vérifiez vos spams si vous ne recevez pas notre email.</p></div>';
  }
  setTimeout(closeModal,3500);
}"""

new = """function showSuccess(){
  var form=$g('mform');
  if(form){
    var prn=($g('f-prn')||{}).value||'';
    var nom=($g('f-nom')||{}).value||'';
    var mail=($g('f-mail')||{}).value||'';
    var tel=($g('f-tel')||{}).value||'';
    var lienCompte='https://espace-client-217943559750.europe-west1.run.app/register?prenom='
      +encodeURIComponent(prn)+'&nom='+encodeURIComponent(nom)+'&email='+encodeURIComponent(mail)+'&telephone='+encodeURIComponent(tel);
    form.innerHTML='<div class="modal-ok"><div class="ok-ico">✓</div><h4>Demande envoyée !</h4><p>Nous vous contactons sous 48h à l\\'adresse<br><strong>'+mail+'</strong><br><br>Vérifiez vos spams si vous ne recevez pas notre email.</p>'
      +'<a href="'+lienCompte+'" target="_blank" style="display:inline-block;margin-top:16px;background:#16a34a;color:#fff;font-weight:600;padding:12px 24px;border-radius:10px;text-decoration:none;font-size:14px">Créer mon espace client &rarr;</a>'
      +'<p style="font-size:12px;color:#9ca3af;margin-top:8px">Suivez l\\'avancement de votre dossier en ligne</p></div>';
  }
  setTimeout(closeModal,8000);
}"""

if old in content:
    content = content.replace(old, new, 1)
    print("✅ Patch solaire appliqué")
else:
    print("❌ Pattern non trouvé")

with open('simulateur-solaire/simulateur-solaire.php', 'w') as f:
    f.write(content)
