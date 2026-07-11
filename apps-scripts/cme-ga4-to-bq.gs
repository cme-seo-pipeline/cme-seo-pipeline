/**
 * CME — Google Analytics 4 → BigQuery
 * Property ID : 528487832
 * ═══════════════════════════════════════════════════════════════
 * INSTALLATION (dans le MÊME projet Apps Script que gsc-to-bq.gs) :
 * 1. Apps Script → + Nouveau fichier → Nommer "ga4-to-bq"
 * 2. Coller ce code
 * 3. Dans appsscript.json, ajouter le scope GA4 :
 *    "https://www.googleapis.com/auth/analytics.readonly"
 * 4. Exécuter setupGA4() pour créer la table BQ
 * 5. Exécuter syncGA4Last90Days() pour le backfill
 * 6. Déclencheur : syncGA4Quotidien → Quotidien 03h30
 * ═══════════════════════════════════════════════════════════════
 */

var GA4_CFG = {
  PROPERTY_ID: '528487832',
  DOMAIN:      'https://www.comprendre-mon-energie.fr',
  PROJECT_ID:  'seo-data-hub-cme',
  DATASET_ID:  '01_raw',
  TABLE_ID:    'ga4_pages',
  BATCH_SIZE:  500
};

// ── Points d'entrée ───────────────────────────────────────────
function syncGA4Quotidien() {
  var d = new Date();
  d.setDate(d.getDate() - 1);
  var dateStr = Utilities.formatDate(d, 'UTC', 'yyyy-MM-dd');
  syncGA4Periode(dateStr, dateStr);
}

function syncGA4Last30Days() {
  var end   = new Date(); end.setDate(end.getDate() - 1);
  var start = new Date(end); start.setDate(start.getDate() - 29);
  syncGA4Periode(
    Utilities.formatDate(start, 'UTC', 'yyyy-MM-dd'),
    Utilities.formatDate(end,   'UTC', 'yyyy-MM-dd')
  );
}

function syncGA4Last90Days() {
  var end   = new Date(); end.setDate(end.getDate() - 1);
  var start = new Date(end); start.setDate(start.getDate() - 89);
  syncGA4Periode(
    Utilities.formatDate(start, 'UTC', 'yyyy-MM-dd'),
    Utilities.formatDate(end,   'UTC', 'yyyy-MM-dd')
  );
}

// ── Moteur de synchronisation ─────────────────────────────────
function syncGA4Periode(startDate, endDate) {
  Logger.log('=== CME GA4 Sync : ' + startDate + ' -> ' + endDate + ' ===');

  var rows = fetchGA4(startDate, endDate);
  Logger.log('Lignes GA4 brutes : ' + rows.length);
  if (!rows.length) { Logger.log('Aucune donnee.'); return; }

  var bqRows = rows.map(function(r) {
    var pagePath = r.dimensionValues[0].value;
    var date     = r.dimensionValues[1].value;
    var fullUrl  = GA4_CFG.DOMAIN + pagePath;
    var parsed   = parsePath(pagePath);
    var uid = Utilities.computeDigest(
      Utilities.DigestAlgorithm.MD5,
      date + '|' + pagePath
    ).map(function(b){return(b<0?b+256:b).toString(16).padStart(2,'0');}).join('');

    var mv = r.metricValues;
    return {
      insertId: uid,
      json: {
        date:                date,
        page_path:           pagePath,
        page_url:            fullUrl,
        silo:                parsed.silo,
        sous_silo:           parsed.sousSilo,
        sessions:            parseInt(mv[0].value) || 0,
        bounce_rate:         Math.round(parseFloat(mv[1].value) * 10000) / 10000,
        avg_session_duration:Math.round(parseFloat(mv[2].value) * 100) / 100,
        page_views:          parseInt(mv[3].value) || 0,
        new_users:           parseInt(mv[4].value) || 0,
        conversions:         parseInt(mv[5].value) || 0,
        synced_at:           new Date().toISOString()
      }
    };
  });

  var total = 0, errors = 0;
  for (var i = 0; i < bqRows.length; i += GA4_CFG.BATCH_SIZE) {
    var batch = bqRows.slice(i, i + GA4_CFG.BATCH_SIZE);
    if (insertGA4BQ(batch)) total += batch.length;
    else errors += batch.length;
  }
  Logger.log('Inseres : ' + total + ' | Erreurs : ' + errors);
}

// ── Appel API GA4 Data API v1beta ─────────────────────────────
function fetchGA4(startDate, endDate) {
  var token = ScriptApp.getOAuthToken();
  var url   = 'https://analyticsdata.googleapis.com/v1beta/properties/'
              + GA4_CFG.PROPERTY_ID + ':runReport';
  var all = [], offset = 0, limit = 10000;

  do {
    var payload = {
      dateRanges: [{ startDate: startDate, endDate: endDate }],
      dimensions: [
        { name: 'pagePath' },
        { name: 'date' }
      ],
      metrics: [
        { name: 'sessions' },
        { name: 'bounceRate' },
        { name: 'averageSessionDuration' },
        { name: 'screenPageViews' },
        { name: 'newUsers' },
        { name: 'conversions' }
      ],
      limit:  limit,
      offset: offset
    };

    var resp = UrlFetchApp.fetch(url, {
      method:             'post',
      contentType:        'application/json',
      headers:            { 'Authorization': 'Bearer ' + token },
      payload:            JSON.stringify(payload),
      muteHttpExceptions: true
    });

    if (resp.getResponseCode() !== 200) {
      Logger.log('Erreur GA4 ' + resp.getResponseCode() + ' : '
                 + resp.getContentText().substring(0, 300));
      break;
    }

    var data = JSON.parse(resp.getContentText());
    var rows = data.rows || [];
    all    = all.concat(rows);
    offset += rows.length;
    if (rows.length < limit) break;
  } while (rows.length === limit);

  return all;
}

// ── Extraction silo / sous-silo depuis le path ────────────────
var GA4_SILO_MAP = {
  'gaz':                                '1. Gaz',
  'renovation-energetique':             '2. Renovation Energetique',
  'aide-energetique':                   '3. Aide Energetique',
  'solaire':                            '4. Solaire',
  'electricite':                        '5. Electricite',
  'attestation-de-contrat-delectricite':'5. Electricite',
  'comprendre-sa-facture-delectricite': '5. Electricite',
  'comparateur-doffres-electricite':    '5. Electricite',
  'chauffage-gaz':                      '1. Gaz',
  'cheque-energie-2026':                '3. Aide Energetique',
  'aide-etat-thermostat-connecte':      '3. Aide Energetique',
  'solutions-pompe-a-chaleur':          '2. Renovation Energetique',
  'pompe-a-chaleur-piscine':            '2. Renovation Energetique',
  'installer-une-pompe-a-chaleur':      '2. Renovation Energetique',
  'seche-linge-pompe-a-chaleur':        '2. Renovation Energetique'
};

function parsePath(path) {
  var clean = path.replace(/^\//, '').replace(/\/$/, '');
  var parts = clean.split('/').filter(function(p){ return p.length > 0; });
  var slug  = parts[0] || '';
  var sub   = parts[1] || '';
  var silo  = GA4_SILO_MAP[slug] || detectSiloGA4(slug);
  return { silo: silo, sousSilo: sub };
}

function detectSiloGA4(slug) {
  if (!slug) return '';
  var s = slug.toLowerCase();
  if (s.includes('electr'))  return '5. Electricite';
  if (s.includes('gaz'))     return '1. Gaz';
  if (s.includes('solaire') || s.includes('photov')) return '4. Solaire';
  if (s.includes('aide') || s.includes('prime') || s.includes('cheque')) return '3. Aide Energetique';
  if (s.includes('renov') || s.includes('isol') || s.includes('chauf') || s.includes('pompe')) return '2. Renovation Energetique';
  return slug;
}

// ── Insertion BigQuery ────────────────────────────────────────
function insertGA4BQ(rows) {
  var url   = 'https://bigquery.googleapis.com/bigquery/v2/projects/'
              + GA4_CFG.PROJECT_ID + '/datasets/' + GA4_CFG.DATASET_ID
              + '/tables/' + GA4_CFG.TABLE_ID + '/insertAll';
  var token = ScriptApp.getOAuthToken();
  var resp  = UrlFetchApp.fetch(url, {
    method:             'post',
    contentType:        'application/json',
    headers:            { 'Authorization': 'Bearer ' + token },
    payload:            JSON.stringify({
      skipInvalidRows: false, ignoreUnknownValues: false, rows: rows
    }),
    muteHttpExceptions: true
  });
  if (resp.getResponseCode() !== 200) {
    Logger.log('Erreur BQ GA4 : ' + resp.getContentText().substring(0, 200));
    return false;
  }
  var r = JSON.parse(resp.getContentText());
  if (r.insertErrors && r.insertErrors.length > 0) {
    Logger.log('BQ errors : ' + JSON.stringify(r.insertErrors[0]));
    return false;
  }
  return true;
}

// ── Créer table BQ ────────────────────────────────────────────
function setupGA4() {
  var url   = 'https://bigquery.googleapis.com/bigquery/v2/projects/'
              + GA4_CFG.PROJECT_ID + '/datasets/' + GA4_CFG.DATASET_ID + '/tables';
  var token = ScriptApp.getOAuthToken();
  var resp  = UrlFetchApp.fetch(url, {
    method: 'post', contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + token },
    payload: JSON.stringify({
      tableReference: {
        projectId: GA4_CFG.PROJECT_ID,
        datasetId: GA4_CFG.DATASET_ID,
        tableId:   GA4_CFG.TABLE_ID
      },
      description: 'CME — Donnees GA4 par page (sync quotidien)',
      schema: { fields: [
        { name:'date',                 type:'DATE',      mode:'NULLABLE' },
        { name:'page_path',            type:'STRING',    mode:'NULLABLE' },
        { name:'page_url',             type:'STRING',    mode:'NULLABLE' },
        { name:'silo',                 type:'STRING',    mode:'NULLABLE' },
        { name:'sous_silo',            type:'STRING',    mode:'NULLABLE' },
        { name:'sessions',             type:'INTEGER',   mode:'NULLABLE' },
        { name:'bounce_rate',          type:'FLOAT',     mode:'NULLABLE' },
        { name:'avg_session_duration', type:'FLOAT',     mode:'NULLABLE' },
        { name:'page_views',           type:'INTEGER',   mode:'NULLABLE' },
        { name:'new_users',            type:'INTEGER',   mode:'NULLABLE' },
        { name:'conversions',          type:'INTEGER',   mode:'NULLABLE' },
        { name:'synced_at',            type:'TIMESTAMP', mode:'NULLABLE' }
      ]}
    }),
    muteHttpExceptions: true
  });
  var code = resp.getResponseCode();
  if (code === 200)      Logger.log('Table ga4_pages creee');
  else if (code === 409) Logger.log('Table deja existante');
  else Logger.log('Erreur : ' + code + ' — ' + resp.getContentText().substring(0,200));
}
