/**
 * CME — Leads Simulateur Aides Renovation -> Google Sheets
 * ============================================================
 * INSTALLATION :
 * 1. script.google.com -> Nouveau projet -> Coller ce code
 * 2. Deployer -> Nouveau deploiement -> Application Web
 *    Executer en tant que : Moi
 *    Qui a acces : Tout le monde
 * 3. Copier l'URL /exec generee
 * 4. WordPress -> Reglages -> CME Simulateur Aides -> coller l'URL
 * ============================================================
 */

var SPREADSHEET_ID = '1LBgHQPioaT0buv9rev5egywRDtE8hKIFHFVwjNqw00o'; // meme classeur
var SHEET_NAME = 'Leads Aides';

var HEADERS = [
  'Date & Heure', 'Prenom', 'Nom', 'Email', 'Telephone', 'Adresse',
  'Profil MaPrimeRenov', 'Travaux envisages',
  'Budget travaux (EUR)', 'Montant MaPrimeRenov (EUR)', 'Montant CEE (EUR)',
  'Total aides (EUR)', 'Reste a charge (EUR)'
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
    .createTextOutput('CME Leads Aides actif - ' + new Date().toLocaleString('fr-FR'))
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
  range.setFontWeight('bold').setFontColor('#92400e')
       .setBackground('#fffbeb').setHorizontalAlignment('center');
  sheet.setFrozenRows(1);
  sheet.setColumnWidth(1, 150);
  sheet.setColumnWidth(4, 200);
  sheet.setColumnWidth(6, 250);
  sheet.setColumnWidth(8, 220);
}

function ecrireSheet(d) {
  var sheet = getSheet();
  sheet.appendRow([
    new Date(),
    d.prenom || '', d.nom || '', d.email || '', d.telephone || '', d.adresse || '',
    d.profil || '', d.travaux || '',
    d.budget || '', d.montant_mpr || '', d.montant_cee || '',
    d.total_aides || '', d.reste_a_charge || ''
  ]);
}
