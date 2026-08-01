FICHIER = "wordpress-plugins/simulateur-solaire/simulateur-solaire.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = """  // Telecharger le PDF directement via blob URL
  var dateStr = new Date().toISOString().split('T')[0];
  try {
    var pdfBlob = doc.output('blob');
    var blobUrl = URL.createObjectURL(pdfBlob);
    var dlLink = document.createElement('a');
    dlLink.href = blobUrl;
    dlLink.download = 'Estimation-Solaire-CME-'+dateStr+'.pdf';
    dlLink.style.display = 'none';
    document.body.appendChild(dlLink);
    dlLink.click();
    setTimeout(function(){
      document.body.removeChild(dlLink);
      URL.revokeObjectURL(blobUrl);
    }, 2000);
  } catch(saveErr) {
    // Fallback final : methode native jsPDF
    doc.save('Estimation-Solaire-CME-'+dateStr+'.pdf');
  }
}"""

nouveau = """  // Telecharger le PDF : pont vers l'app mobile si on tourne dans sa
  // WebView (le telechargement navigateur classique n'y fonctionne pas),
  // sinon comportement navigateur standard inchange.
  var dateStr = new Date().toISOString().split('T')[0];
  try {
    var pdfBlob = doc.output('blob');
    if (window.ReactNativeWebView) {
      var reader = new FileReader();
      reader.onloadend = function() {
        var base64 = String(reader.result).split(',')[1];
        window.ReactNativeWebView.postMessage(JSON.stringify({
          type: 'pdf_ready',
          base64: base64,
          filename: 'Estimation-Solaire-CME-'+dateStr+'.pdf'
        }));
      };
      reader.readAsDataURL(pdfBlob);
    } else {
      var blobUrl = URL.createObjectURL(pdfBlob);
      var dlLink = document.createElement('a');
      dlLink.href = blobUrl;
      dlLink.download = 'Estimation-Solaire-CME-'+dateStr+'.pdf';
      dlLink.style.display = 'none';
      document.body.appendChild(dlLink);
      dlLink.click();
      setTimeout(function(){
        document.body.removeChild(dlLink);
        URL.revokeObjectURL(blobUrl);
      }, 2000);
    }
  } catch(saveErr) {
    // Fallback final : methode native jsPDF
    doc.save('Estimation-Solaire-CME-'+dateStr+'.pdf');
  }
}"""

if ancien not in contenu:
    print("❌ PATCH (PDF solaire) : bloc non trouve")
else:
    contenu = contenu.replace(ancien, nouveau)
    print("✅ PATCH (PDF solaire) : pont app mobile ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
