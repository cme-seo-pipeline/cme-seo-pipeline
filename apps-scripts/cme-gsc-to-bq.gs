/**
 * CME — Google Search Console → BigQuery
 * ═══════════════════════════════════════════════════════════════
 * INSTALLATION :
 * 1. script.google.com → Nouveau projet → Coller ce code
 * 2. Nommer "CME GSC Sync"
 * 3. Exécuter setup() une première fois (crée la table BQ)
 * 4. Exécuter syncLast30Days() pour le backfill initial
 * 5. Déclencheurs → Ajouter → syncQuotidien → Quotidien 03h00
 * ═══════════════════════════════════════════════════════════════
 */

// ── Configuration ──────────────────────────────────────────────
var CFG = {
  SITE_URL:   'https://www.comprendre-mon-energie.fr/',
  PROJECT_ID: 'seo-data-hub-cme',
  DATASET_ID: '01_raw',
  TABLE_ID:   'gsc_queries',
  GSC_LAG:    3,    // jours de délai GSC
  BATCH_SIZE: 500   // lignes par batch BQ
};

// Mapping slug URL → nom silo (clé = 1er segment après le domaine)
var SILO_MAP = {
  'gaz':                    '1. Gaz',
  'renovation-energetique': '2. Renovation Energetique',
  'aide-energetique':       '3. Aide Energetique',
  'solaire':                '4. Solaire',
  'electricite':            '5. Electricite'
};

// ── Point d'entrée quotidien ──────────────────────────────────
function syncQuotidien() {
  // Hier uniquement (évite les doublons avec backfill)
  var d = new Date();
  d.setDate(d.getDate() - CFG.GSC_LAG);
  var dateStr = formatDate(d);
  syncPeriode(dateStr, dateStr);
}

// ── Backfill 30 jours (lancer une fois manuellement) ─────────
function syncLast30Days() {
  var end = new Date();
  end.setDate(end.getDate() - CFG.GSC_LAG);
  var start = new Date(end);
  start.setDate(start.getDate() - 29);
  syncPeriode(formatDate(start), formatDate(end));
}

// ── Backfill 90 jours (historique complet) ────────────────────
function syncLast90Days() {
  var end = new Date();
  end.setDate(end.getDate() - CFG.GSC_LAG);
  var start = new Date(end);
  start.setDate(start.getDate() - 89);
  syncPeriode(formatDate(start), formatDate(end));
}

// ── Moteur de synchronisation ─────────────────────────────────
function syncPeriode(startDate, endDate) {
  Logger.log('=== CME GSC Sync : ' + startDate + ' → ' + endDate + ' ===');

  var rows = fetchGSC(startDate, endDate);
  Logger.log('Lignes GSC brutes : ' + rows.length);

  if (!rows.length) {
    Logger.log('Aucune donnée pour cette période.');
    return;
  }

  // Transformer + enrichir
  var bqRows = rows.map(function(r) {
    var query   = r.keys[0];
    var page    = r.keys[1];
    var parsed  = parseUrl(page);
    var uid     = Utilities.computeDigest(
                    Utilities.DigestAlgorithm.MD5,
                    endDate + '|' + query + '|' + page
                  ).map(function(b){return (b < 0 ? b+256 : b).toString(16).padStart(2,'0');}).join('');
    return {
      insertId: uid,
      json: {
        date:        endDate,
        query:       query,
        page:        page,
        clics:       r.clicks       || 0,
        impressions: r.impressions  || 0,
        ctr:         Math.round((r.ctr || 0) * 10000) / 10000,
        position:    Math.round((r.position || 0) * 100) / 100,
        silo:        parsed.silo,
        sous_silo:   parsed.sousSilo,
        synced_at:   new Date().toISOString()
      }
    };
  });

  // Insérer dans BQ par batches
  var total = 0, errors = 0;
  for (var i = 0; i < bqRows.length; i += CFG.BATCH_SIZE) {
    var batch = bqRows.slice(i, i + CFG.BATCH_SIZE);
    var ok = insertBQ(batch);
    if (ok) total += batch.length;
    else errors += batch.length;
  }

  Logger.log('✅ Insertées : ' + total + ' | ❌ Erreurs : ' + errors);
}

// ── Appel API Google Search Console ──────────────────────────
function fetchGSC(startDate, endDate) {
  var token = ScriptApp.getOAuthToken();
  var url   = 'https://www.googleapis.com/webmasters/v3/sites/'
              + encodeURIComponent(CFG.SITE_URL)
              + '/searchAnalytics/query';
  var all   = [];
  var start = 0;
  var limit = 5000;

  // Pagination : GSC retourne max 25000 lignes par appel
  do {
    var payload = {
      startDate:  startDate,
      endDate:    endDate,
      dimensions: ['query', 'page'],
      rowLimit:   limit,
      startRow:   start,
      dataState:  'all'
    };
    var resp = UrlFetchApp.fetch(url, {
      method:             'post',
      contentType:        'application/json',
      headers:            {'Authorization': 'Bearer ' + token},
      payload:            JSON.stringify(payload),
      muteHttpExceptions: true
    });
    if (resp.getResponseCode() !== 200) {
      Logger.log('Erreur GSC ' + resp.getResponseCode() + ' : ' + resp.getContentText().substring(0, 300));
      break;
    }
    var data = JSON.parse(resp.getContentText());
    var rows = data.rows || [];
    all = all.concat(rows);
    start += rows.length;
    if (rows.length < limit) break; // Dernière page
  } while (rows.length === limit);

  return all;
}

// ── Extraction silo / sous-silo depuis l'URL ─────────────────
function parseUrl(url) {
  var path = url
    .replace('https://www.comprendre-mon-energie.fr/', '')
    .replace('https://comprendre-mon-energie.fr/', '')
    .replace(/\/$/, '');
  var parts = path.split('/').filter(function(p) { return p.length > 0; });
  var siloSlug   = parts[0] || '';
  var sousSilo   = parts[1] || '';
  return {
    silo:     SILO_MAP[siloSlug] || siloSlug,
    sousSilo: sousSilo
  };
}

// ── Insertion BigQuery (streaming insert) ─────────────────────
function insertBQ(rows) {
  var url   = 'https://bigquery.googleapis.com/bigquery/v2/projects/'
              + CFG.PROJECT_ID + '/datasets/' + CFG.DATASET_ID
              + '/tables/' + CFG.TABLE_ID + '/insertAll';
  var token = ScriptApp.getOAuthToken();
  var resp  = UrlFetchApp.fetch(url, {
    method:             'post',
    contentType:        'application/json',
    headers:            {'Authorization': 'Bearer ' + token},
    payload:            JSON.stringify({
      skipInvalidRows:     false,
      ignoreUnknownValues: false,
      rows:                rows
    }),
    muteHttpExceptions: true
  });
  if (resp.getResponseCode() !== 200) {
    Logger.log('Erreur BQ : ' + resp.getContentText().substring(0, 200));
    return false;
  }
  var result = JSON.parse(resp.getContentText());
  if (result.insertErrors && result.insertErrors.length > 0) {
    Logger.log('BQ insert errors : ' + JSON.stringify(result.insertErrors[0]));
    return false;
  }
  return true;
}

// ── Créer la table BQ (lancer une fois via setup()) ──────────
function setup() {
  var url   = 'https://bigquery.googleapis.com/bigquery/v2/projects/'
              + CFG.PROJECT_ID + '/datasets/' + CFG.DATASET_ID + '/tables';
  var token = ScriptApp.getOAuthToken();
  var resp  = UrlFetchApp.fetch(url, {
    method:      'post',
    contentType: 'application/json',
    headers:     {'Authorization': 'Bearer ' + token},
    payload:     JSON.stringify({
      tableReference: {
        projectId: CFG.PROJECT_ID,
        datasetId: CFG.DATASET_ID,
        tableId:   CFG.TABLE_ID
      },
      description: 'CME — Données GSC par requête + page (sync quotidien)',
      schema: { fields: [
        {name:'date',        type:'DATE',      mode:'NULLABLE', description:'Date de la période'},
        {name:'query',       type:'STRING',    mode:'NULLABLE', description:'Requête GSC'},
        {name:'page',        type:'STRING',    mode:'NULLABLE', description:'URL indexée'},
        {name:'clics',       type:'INTEGER',   mode:'NULLABLE', description:'Nombre de clics'},
        {name:'impressions', type:'INTEGER',   mode:'NULLABLE', description:'Nombre d impressions'},
        {name:'ctr',         type:'FLOAT',     mode:'NULLABLE', description:'Taux de clic'},
        {name:'position',    type:'FLOAT',     mode:'NULLABLE', description:'Position moyenne'},
        {name:'silo',        type:'STRING',    mode:'NULLABLE', description:'Silo CME'},
        {name:'sous_silo',   type:'STRING',    mode:'NULLABLE', description:'Sous-silo CME'},
        {name:'synced_at',   type:'TIMESTAMP', mode:'NULLABLE', description:'Horodatage sync'}
      ]}
    }),
    muteHttpExceptions: true
  });
  var code = resp.getResponseCode();
  if (code === 200) Logger.log('✅ Table ' + CFG.TABLE_ID + ' créée');
  else if (code === 409) Logger.log('ℹ️  Table déjà existante');
  else Logger.log('❌ Erreur : ' + code + ' — ' + resp.getContentText().substring(0, 200));
}

// ── Utilitaire date ───────────────────────────────────────────
function formatDate(d) {
  return Utilities.formatDate(d, 'UTC', 'yyyy-MM-dd');
}

// ── Vérification santé (test rapide) ─────────────────────────
function healthCheck() {
  Logger.log('Token OK : ' + (ScriptApp.getOAuthToken() ? 'oui' : 'non'));
  Logger.log('Site : ' + CFG.SITE_URL);
  var yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 4);
  var rows = fetchGSC(formatDate(yesterday), formatDate(yesterday));
  Logger.log('Lignes GSC hier : ' + rows.length + ' (test 1 jour)');
}
