/**
 * CME — Leads Comparateur Energie -> Google Sheets
 * Nouvel onglet dedie, independant du script "Leads Solaire"
 * ============================================================
 * INSTALLATION :
 * 1. script.google.com -> Nouveau projet -> Coller ce code
 * 2. Deployer -> Nouveau deploiement -> Application Web
 *    Executer en tant que : Moi
 *    Qui a acces : Tout le monde
 * 3. Copier l'URL /exec generee
 * 4. La coller dans wp-config.php :
 *    define('CME_CMP_APPS_SCRIPT_URL', 'URL_ICI');
 * ============================================================
 */

var SPREADSHEET_ID = '1LBgHQPioaT0buv9rev5egywRDtE8hKIFHFVwjNqw00o'; // meme classeur que solaire
var SHEET_NAME = 'Leads Comparateur';

var HEADERS = [
  'Date & Heure',
  'Prenom', 'Nom', 'Email', 'Telephone',
  'Energie comparee', 'Fournisseur choisi', 'Offre',
  'Prix annuel estime (EUR)', 'Economie vs reference (EUR)',
  'Consommation (kWh/an)', 'Option tarifaire',
  'Type logement', 'Surface (m2)', 'Nb personnes', 'Mode chauffage',
  'Code postal', 'N PDL/PRM', 'N PCE',
  'Lien offre fournisseur'
];

function doGet(e) {
  if (e && e.parameter && e.parameter.payload) {
    try {
      var d = JSON.parse(decodeURIComponent(e.parameter.payload));
      ecrireSheet(d);
      return ContentService
        .createTextOutput(JSON.stringify({status:'ok', rows:getSheet().getLastRow()}))
        .setMimeType(ContentService.MimeType.JSON);
    } catch(err) {
      return ContentService
        .createTextOutput(JSON.stringify({status:'error', msg:err.toString()}))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }
  return ContentService
    .createTextOutput('CME Leads Comparateur actif - ' + new Date().toLocaleString('fr-FR'))
    .setMimeType(ContentService.MimeType.TEXT);
}

function getSheet() {
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    appliquerEntetes(sheet);
  } else {
    var premiereCase = sheet.getRange(1, 1).getValue();
    if (!premiereCase || premiereCase.toString().trim() === '') {
      appliquerEntetes(sheet);
    } else {
      sheet.setFrozenRows(1);
    }
  }
  return sheet;
}

function appliquerEntetes(sheet) {
  var range = sheet.getRange(1, 1, 1, HEADERS.length);
  range.setValues([HEADERS]);
  range.setFontWeight('bold').setFontColor('#1d4ed8')
       .setBackground('#eff6ff').setHorizontalAlignment('center');
  sheet.setFrozenRows(1);
  sheet.setColumnWidth(1, 150);
  sheet.setColumnWidth(4, 200);
  sheet.setColumnWidth(6, 140);
  sheet.setColumnWidth(20, 280);
}

function ecrireSheet(d) {
  var sheet = getSheet();
  sheet.appendRow([
    new Date(),
    d.prenom || '', d.nom || '', d.email || '', d.telephone || '',
    d.energie || '', d.fournisseur || '', d.offre || '',
    d.prix_annuel || '', d.economie || '',
    d.kwh || '', d.option_tarifaire || '',
    d.logement || '', d.surface || '', d.personnes || '', d.chauffage || '',
    d.codepostal || '', d.pdl || '', d.pce || '',
    d.lien_offre || ''
  ]);
}
