/**
 * CME — Leads Mini-formulaire integre aux articles -> Google Sheets
 * ============================================================
 * Recoit les leads du mini-formulaire interactif insere toutes les ~230
 * mots dans le corps des articles (wordpress-mu-plugins/cme-cta-progressifs.php,
 * chantier du 22/10/2026 -- remplace les anciens boutons CTA). Ecrit dans un
 * onglet dedie du MEME classeur que les leads des 3 anciens simulateurs
 * (cme-aides-leads.gs, cme-comparateur-leads.gs) et de l'espace client
 * (cme-espace-client-leads.gs) -- l'operateur garde un seul endroit a
 * surveiller pour tous les leads du site, au lieu d'en ajouter un nouveau.
 *
 * Ces leads arrivent AUSSI dans BigQuery (table leads_convertis, via
 * /wp-json/cme/v1/log-lead -> cme-tracking-conversion.php -> API Cloud Run)
 * -- ce script est un relais SUPPLEMENTAIRE, pas un remplacement : la copie
 * BigQuery reste la source de verite pour les tableaux de bord/analyses,
 * celle-ci est pour la surveillance au jour le jour par l'operateur.
 *
 * INSTALLATION :
 * 1. script.google.com -> Nouveau projet -> Coller ce code
 * 2. Deployer -> Nouveau deploiement -> Application Web
 *    Executer en tant que : Moi
 *    Qui a acces : Tout le monde
 * 3. Copier l'URL /exec generee
 * 4. La coller dans wordpress-mu-plugins/cme-tracking-conversion.php,
 *    constante CME_APPS_SCRIPT_LEADS_INLINE_URL (puis redeployer ce fichier
 *    en cPanel comme d'habitude -- cloudshell download, .bak horodate,
 *    upload, purge des 2 caches LiteSpeed)
 * ============================================================
 */

var SPREADSHEET_ID = '1LBgHQPioaT0buv9rev5egywRDtE8hKIFHFVwjNqw00o'; // meme classeur que les autres leads
var SHEET_NAME = 'Leads Formulaire Article';

var HEADERS = [
  'Date & Heure', 'Prenom', 'Telephone', 'Email', 'Code Postal',
  'Silo', 'Position dans l\'article', 'URL de l\'article'
];

function doGet(e) {
  if (e && e.parameter && e.parameter.payload) {
    try {
      var d = JSON.parse(decodeURIComponent(e.parameter.payload));
      ecrireSheet(d);
      return ContentService
        .createTextOutput(JSON.stringify({status: 'ok', rows: getSheet().getLastRow()}))
        .setMimeType(ContentService.MimeType.JSON);
    } catch (err) {
      return ContentService
        .createTextOutput(JSON.stringify({status: 'error', msg: err.toString()}))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }
  return ContentService
    .createTextOutput('CME Leads Formulaire Article actif - ' + new Date().toLocaleString('fr-FR'))
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
  range.setFontWeight('bold').setFontColor('#1e3a8a')
       .setBackground('#eff6ff').setHorizontalAlignment('center');
  sheet.setFrozenRows(1);
  sheet.setColumnWidth(4, 200);
  sheet.setColumnWidth(8, 320);
}

function ecrireSheet(d) {
  var sheet = getSheet();
  var details = {};
  try { details = JSON.parse(d.details || '{}'); } catch (e) { details = {}; }
  sheet.appendRow([
    new Date(),
    d.prenom || '', d.telephone || '', d.email || '', d.code_postal || '',
    details.silo || '', details.position || '', d.source_page || ''
  ]);
}
