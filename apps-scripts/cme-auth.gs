/**
 * CME — Authentification par compte de service (remplace ScriptApp.getOAuthToken())
 * Evite le renouvellement hebdomadaire de consentement : les comptes de
 * service ne sont pas soumis a cette contrainte, contrairement aux
 * identites utilisateur sur scopes sensibles (Search Console, BigQuery).
 *
 * SECURITE : la cle privee n'est jamais en dur dans ce fichier — elle est
 * lue depuis les Proprietes du script (⚙️ Parametres du projet > Proprietes
 * du script), pour ne jamais apparaitre dans l'historique de versions du
 * script ni dans une eventuelle sauvegarde/export de ce fichier.
 * Proprietes attendues : SA_CLIENT_EMAIL, SA_PRIVATE_KEY
 */
function getServiceAccountToken_() {
  var props = PropertiesService.getScriptProperties();
  var clientEmail = props.getProperty('SA_CLIENT_EMAIL');
  var privateKey  = props.getProperty('SA_PRIVATE_KEY');

  if (!clientEmail || !privateKey) {
    throw new Error('SA_CLIENT_EMAIL ou SA_PRIVATE_KEY manquant dans les proprietes du script. '
      + 'Parametres du projet > Proprietes du script.');
  }

  var service = OAuth2.createService('CME-ServiceAccount')
      .setTokenUrl('https://oauth2.googleapis.com/token')
      .setPrivateKey(privateKey)
      .setIssuer(clientEmail)
      .setPropertyStore(props)
      .setScope('https://www.googleapis.com/auth/webmasters.readonly https://www.googleapis.com/auth/bigquery https://www.googleapis.com/auth/analytics.readonly');

  if (!service.hasAccess()) {
    Logger.log('❌ Erreur autorisation compte de service : ' + service.getLastError());
    throw new Error('Token compte de service impossible : ' + service.getLastError());
  }
  return service.getAccessToken();
}
