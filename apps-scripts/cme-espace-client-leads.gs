/**
 * CME — Leads Espace Client -> Google Sheets + Email
 * ============================================================
 * Recoit les leads crees depuis cme-client-api (Firestore), qu'ils
 * viennent du formulaire "Rendez-vous avec un expert" ou d'une
 * future fonctionnalite du portail. Ecrit dans un onglet dedie et
 * envoie une notification email.
 *
 * INSTALLATION :
 * 1. script.google.com -> Nouveau projet -> Coller ce code
 * 2. Deployer -> Nouveau deploiement -> Application Web
 *    Executer en tant que : Moi
 *    Qui a acces : Tout le monde
 * 3. Copier l'URL /exec generee, la mettre dans client-api/server.py
 *    (variable GAS_WEBHOOK_URL)
 * ============================================================
 */

var SPREADSHEET_ID = '1LBgHQPioaT0buv9rev5egywRDtE8hKIFHFVwjNqw00o'; // meme classeur
var SHEET_NAME = 'Leads Espace Client';
var DEST_EMAIL = 'contact@comprendre-mon-energie.fr';

var HEADERS = [
  'Date & Heure', 'Outil', 'Prenom', 'Nom', 'Email', 'Telephone',
  'Sujet', 'Message', 'Disponibilites', 'Montant estime (EUR)', 'UID compte'
];

function doGet(e) {
  if (e && e.parameter && e.parameter.payload) {
    try {
      var d = JSON.parse(decodeURIComponent(e.parameter.payload));
      ecrireSheet(d);
      envoyerEmail(d);
      return ContentService
        .createTextOutput(JSON.stringify({status: 'ok'}))
        .setMimeType(ContentService.MimeType.JSON);
    } catch (err) {
      return ContentService
        .createTextOutput(JSON.stringify({status: 'error', msg: err.toString()}))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }
  return ContentService
    .createTextOutput('CME Leads Espace Client actif - ' + new Date().toLocaleString('fr-FR'))
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
  range.setFontWeight('bold').setFontColor('#166534')
       .setBackground('#f0fdf4').setHorizontalAlignment('center');
  sheet.setFrozenRows(1);
  sheet.setColumnWidth(7, 200);
  sheet.setColumnWidth(8, 300);
}

function ecrireSheet(d) {
  var sheet = getSheet();
  var details = d.details || {};
  sheet.appendRow([
    new Date(),
    d.tool || '',
    d.prenom || '', d.nom || '', d.email || '', d.telephone || '',
    details.sujet || '', details.message || '', details.disponibilites || '',
    d.montant_estime || '', d.owner_uid || ''
  ]);
}

function envoyerEmail(d) {
  var details = d.details || {};
  var sujet = '📅 Nouvelle demande — ' + (d.tool || 'Espace Client') + ' — ' + (d.prenom || '') + ' ' + (d.nom || '');

  var corps = '<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:580px;margin:auto">'
    + '<div style="background:linear-gradient(135deg,#166534,#22c55e);color:#fff;padding:20px 24px;border-radius:10px 10px 0 0">'
    + '<h2 style="margin:0">📅 Nouvelle demande — Espace Client</h2>'
    + '<p style="margin:4px 0 0;opacity:.85;font-size:13px">' + new Date().toLocaleString('fr-FR') + '</p>'
    + '</div>'
    + '<div style="background:#fff;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 10px 10px;padding:20px 24px">'
    + '<h3 style="color:#166534;margin:0 0 12px">Contact</h3>'
    + '<table style="width:100%;border-collapse:collapse;margin-bottom:16px">'
    + '<tr><td style="padding:6px;color:#6b7280;width:150px">Nom complet</td><td style="padding:6px;font-weight:600">' + (d.prenom || '') + ' ' + (d.nom || '') + '</td></tr>'
    + '<tr><td style="padding:6px;color:#6b7280">Email</td><td style="padding:6px"><a href="mailto:' + (d.email || '') + '" style="color:#166534">' + (d.email || '') + '</a></td></tr>'
    + '<tr><td style="padding:6px;color:#6b7280">Telephone</td><td style="padding:6px"><a href="tel:' + (d.telephone || '') + '" style="color:#166534">' + (d.telephone || '') + '</a></td></tr>'
    + '</table>'
    + '<hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 16px">'
    + '<h3 style="color:#166534;margin:0 0 12px">Demande</h3>'
    + '<table style="width:100%;border-collapse:collapse">'
    + '<tr><td style="padding:5px;color:#6b7280">Sujet</td><td style="padding:5px;font-weight:600">' + (details.sujet || '-') + '</td></tr>'
    + '<tr><td style="padding:5px;color:#6b7280;vertical-align:top">Message</td><td style="padding:5px">' + (details.message || '-') + '</td></tr>'
    + '<tr><td style="padding:5px;color:#6b7280">Disponibilites</td><td style="padding:5px">' + (details.disponibilites || '-') + '</td></tr>'
    + '</table>'
    + '</div></body></html>';

  MailApp.sendEmail({
    to: DEST_EMAIL,
    subject: sujet,
    htmlBody: corps
  });
}
