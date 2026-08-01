FICHIER = "wordpress-plugins/simulateur-aides/simulateur-aides.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = """  var dateStr=new Date().toISOString().split('T')[0];
  try{
    var pdfBlob=doc.output('blob');var blobUrl=URL.createObjectURL(pdfBlob);
    var dlLink=document.createElement('a');dlLink.href=blobUrl;dlLink.download='Estimation-Aides-CME-'+dateStr+'.pdf';
    dlLink.style.display='none';document.body.appendChild(dlLink);dlLink.click();
    setTimeout(function(){document.body.removeChild(dlLink);URL.revokeObjectURL(blobUrl);},2000);
  }catch(saveErr){doc.save('Estimation-Aides-CME-'+dateStr+'.pdf');}"""

nouveau = """  var dateStr=new Date().toISOString().split('T')[0];
  try{
    var pdfBlob=doc.output('blob');
    if(window.ReactNativeWebView){
      var reader=new FileReader();
      reader.onloadend=function(){
        var base64=String(reader.result).split(',')[1];
        window.ReactNativeWebView.postMessage(JSON.stringify({type:'pdf_ready',base64:base64,filename:'Estimation-Aides-CME-'+dateStr+'.pdf'}));
      };
      reader.readAsDataURL(pdfBlob);
    }else{
      var blobUrl=URL.createObjectURL(pdfBlob);
      var dlLink=document.createElement('a');dlLink.href=blobUrl;dlLink.download='Estimation-Aides-CME-'+dateStr+'.pdf';
      dlLink.style.display='none';document.body.appendChild(dlLink);dlLink.click();
      setTimeout(function(){document.body.removeChild(dlLink);URL.revokeObjectURL(blobUrl);},2000);
    }
  }catch(saveErr){doc.save('Estimation-Aides-CME-'+dateStr+'.pdf');}"""

if ancien not in contenu:
    print("❌ PATCH (PDF aides) : bloc non trouve")
else:
    contenu = contenu.replace(ancien, nouveau)
    print("✅ PATCH (PDF aides) : pont app mobile ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
