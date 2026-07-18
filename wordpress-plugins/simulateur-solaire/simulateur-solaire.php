<?php
/**
 * Plugin Name: CME Simulateur Solaire
 * Plugin URI:  https://www.comprendre-mon-energie.fr
 * Description: Simulateur PV v2.4 — vert logo, carte France satellite, formulaire devis RGPD
 * Version:     3.8.0
 * Author:      CME
 */
if(!defined('ABSPATH'))exit;

// ── Proxy PVGIS (évite CORS du navigateur) ───────────────────────────────────
add_action('wp_ajax_cme_pvgis','cme_pvgis_proxy');
add_action('wp_ajax_nopriv_cme_pvgis','cme_pvgis_proxy');
function cme_pvgis_proxy(){
  $lat   =floatval($_POST['lat']   ??0);
  $lon   =floatval($_POST['lon']   ??0);
  $kw    =floatval($_POST['kw']    ??0);
  $aspect=intval  ($_POST['aspect']??0);
  $angle =intval  ($_POST['angle'] ??30);
  if(!$lat||!$lon||!$kw){wp_send_json_error(['msg'=>'Params manquants']);return;}
  $url='https://re.jrc.ec.europa.eu/api/v5_2/PVcalc'
    .'?lat='.number_format($lat,6,'.','')
    .'&lon='.number_format($lon,6,'.','')
    .'&peakpower='.number_format($kw,3,'.','')
    .'&loss=14&aspect='.$aspect.'&angle='.$angle
    .'&outputformat=json&pvtechchoice=crystSi&mountingplace=building&raddatabase=PVGIS-SARAH2';
  $resp=wp_remote_get($url,['timeout'=>20,'sslverify'=>false]);
  if(is_wp_error($resp)){wp_send_json_error(['msg'=>$resp->get_error_message()]);return;}
  $data=json_decode(wp_remote_retrieve_body($resp),true);
  if(empty($data['outputs'])){wp_send_json_error(['msg'=>'PVGIS indisponible','raw'=>substr(wp_remote_retrieve_body($resp),0,200)]);return;}
  wp_send_json_success($data);
}

// ── Proxy logo CME (base64 pour jsPDF) ───────────────────────────────────────
add_action('wp_ajax_cme_logo_b64','cme_logo_b64');
add_action('wp_ajax_nopriv_cme_logo_b64','cme_logo_b64');
function cme_logo_b64(){
  $path=ABSPATH.'wp-content/uploads/2026/03/cropped-logo-officiel-comprendre-mon-energie-observatoire.png';
  if(file_exists($path)){
    $b64=base64_encode(file_get_contents($path));
    wp_send_json_success(['b64'=>'data:image/png;base64,'.$b64]);
  } else {
    $resp=wp_remote_get('https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/03/cropped-logo-officiel-comprendre-mon-energie-observatoire.png',['timeout'=>10]);
    if(!is_wp_error($resp)){
      $b64=base64_encode(wp_remote_retrieve_body($resp));
      wp_send_json_success(['b64'=>'data:image/png;base64,'.$b64]);
    } else {
      wp_send_json_error(['msg'=>'Logo non disponible']);
    }
  }
}

// ── URL Google Apps Script (définie dans wp-config.php) ──────────────────────

// ── Handler AJAX WordPress ────────────────────────────────────────────────────
add_action('wp_ajax_cme_submit_devis','cme_handle_devis');
add_action('wp_ajax_nopriv_cme_submit_devis','cme_handle_devis');
function cme_handle_devis(){
  if(!check_ajax_referer('cme_devis_nonce','nonce',false)){
    wp_send_json_error(['msg'=>'Nonce invalide']);return;
  }
  $raw     = wp_unslash(isset($_POST['payload'])?$_POST['payload']:'');
  $data    = json_decode($raw,true);
  if(!$data){wp_send_json_error(['msg'=>'Payload invalide']);return;}

  $prenom  = sanitize_text_field($data['prenom']  ?? '');
  $nom     = sanitize_text_field($data['nom']     ?? '');
  $email   = sanitize_email    ($data['email']    ?? '');
  $tel     = sanitize_text_field($data['telephone']?? '');
  $adr     = sanitize_text_field($data['adresse'] ?? '');
  $sf      = intval($data['surface']              ?? 0);
  $ori     = sanitize_text_field($data['orientation'] ?? '');
  $ch      = sanitize_text_field($data['chauffage']   ?? '');
  $nb      = intval($data['nb_panneaux']          ?? 0);
  $kwc     = sanitize_text_field($data['kwc']     ?? '');
  $prod    = intval($data['production']           ?? 0);
  $eco     = intval($data['economie']             ?? 0);
  $budget  = intval($data['budget']               ?? 0);
  $roi     = intval($data['roi']                  ?? 0);
  $co2     = intval($data['co2']                  ?? 0);
  $dest    = 'contact@comprendre-mon-energie.fr';

  // ── Email via WordPress wp_mail() ─────────────────────────────────────────
  $sujet = '☀️ Nouveau devis solaire — '.$prenom.' '.$nom;
  $corps = '<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:580px;margin:auto">
    <div style="background:linear-gradient(135deg,#052e16,#16a34a);color:#fff;padding:20px 24px;border-radius:10px 10px 0 0">
      <h2 style="margin:0">☀️ Nouveau devis solaire</h2>
      <p style="margin:4px 0 0;opacity:.8;font-size:13px">'.date('d/m/Y H:i').'</p>
    </div>
    <div style="background:#fff;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 10px 10px;padding:20px 24px">
      <h3 style="color:#16a34a;margin:0 0 12px">👤 Contact</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
        <tr><td style="padding:6px;color:#6b7280;width:150px">Nom complet</td><td style="padding:6px;font-weight:600">'.$prenom.' '.$nom.'</td></tr>
        <tr><td style="padding:6px;color:#6b7280">Email</td><td style="padding:6px"><a href="mailto:'.$email.'" style="color:#16a34a">'.$email.'</a></td></tr>
        <tr><td style="padding:6px;color:#6b7280">Téléphone</td><td style="padding:6px"><a href="tel:'.$tel.'" style="color:#16a34a">'.$tel.'</a></td></tr>
        <tr><td style="padding:6px;color:#6b7280">Adresse</td><td style="padding:6px">'.($adr?:'—').'</td></tr>
      </table>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 16px">
      <h3 style="color:#16a34a;margin:0 0 12px">⚡ Simulation</h3>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:5px;color:#6b7280">Surface habitable</td><td style="padding:5px;font-weight:600">'.$sf.' m²</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Orientation</td><td style="padding:5px;font-weight:600">'.$ori.'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Chauffage</td><td style="padding:5px;font-weight:600">'.$ch.'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Eau chaude</td><td style="padding:5px;font-weight:600">'.sanitize_text_field($data['eau_chaude']??'').'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Cuisson</td><td style="padding:5px;font-weight:600">'.sanitize_text_field($data['cuisson']??'').'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Énergies actuelles</td><td style="padding:5px;font-weight:600">'.sanitize_text_field($data['energies']??'').'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Habitants</td><td style="padding:5px;font-weight:600">'.(intval($data['habitants']??0)).'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Pente du toit</td><td style="padding:5px;font-weight:600">'.(intval($data['pente']??30)).'°</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Construction</td><td style="padding:5px;font-weight:600">'.(intval($data['annee_construction']??2005)).'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Panneaux</td><td style="padding:5px;font-weight:600">'.$nb.' × 400 Wc = '.$kwc.' kWc</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Production</td><td style="padding:5px;font-weight:600">'.number_format($prod,0,',',' ').' kWh/an</td></tr>
        <tr style="background:#f0fdf4"><td style="padding:8px;color:#16a34a;font-weight:600">Économies</td><td style="padding:8px;font-weight:700;color:#16a34a;font-size:16px">'.number_format($eco,0,',',' ').' €/an</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Budget estimé</td><td style="padding:5px;font-weight:600">'.number_format($budget,0,',',' ').' €</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Retour invest.</td><td style="padding:5px;font-weight:600">'.$roi.' ans</td></tr>
        <tr><td style="padding:5px;color:#6b7280">CO₂ évité</td><td style="padding:5px;font-weight:600">'.number_format($co2,0,',',' ').' kg/an</td></tr>
      </table>
    </div>
  </body></html>';

  $headers = ['Content-Type: text/html; charset=UTF-8','From: Simulateur Solaire <noreply@comprendre-mon-energie.fr>'];
  $mail_ok = wp_mail($dest,$sujet,$corps,$headers);

  // ── Google Sheets via GAS (optionnel) ─────────────────────────────────────
  $gas_url = defined('CME_APPS_SCRIPT_URL') && CME_APPS_SCRIPT_URL ? CME_APPS_SCRIPT_URL : 'https://script.google.com/macros/s/AKfycbyQHpJCRLdQZKHDxRNzV3pIHVDQgGuaRKXzlBZfFxpgmVzzPz4YQs8BKww0QMTORB7YGQ/exec';
  $gas_result = 'tentative';
  if($gas_url){
    $url = $gas_url.'?payload='.rawurlencode($raw);
    $resp = wp_remote_get($url,['timeout'=>20,'blocking'=>true,'sslverify'=>false]);
    $gas_result = is_wp_error($resp)?'erreur:'.$resp->get_error_message():wp_remote_retrieve_body($resp);
  }

  wp_remote_post('https://cme-tracking-api-217943559750.europe-west1.run.app/api/log-lead', array(
    'timeout' => 8, 'blocking' => false, 'sslverify' => false,
    'headers' => array('Content-Type' => 'application/json'),
    'body' => json_encode(array(
      'tool' => 'solaire', 'prenom' => $prenom, 'nom' => $nom, 'email' => $email,
      'telephone' => $tel, 'adresse' => $adr, 'montant_estime' => $budget,
      'economie_estimee' => $eco,
      'details' => array('surface'=>$sf,'orientation'=>$ori,'chauffage'=>$ch,'nb_panneaux'=>$nb,'kwc'=>$kwc,'production'=>$prod,'roi'=>$roi,'co2'=>$co2),
      'source_page' => 'devis-panneau-solaire',
      'source_post_id' => sanitize_text_field($data['src_post'] ?? '')
    ))
  ));

  wp_send_json_success([
    'status'     => 'ok',
    'email_sent' => $mail_ok,
    'gas'        => $gas_result
  ]);
}

add_shortcode('simulateur_solaire','cme_ss24_sc');
function cme_ss24_sc(){
$uid='ss'.uniqid();
  wp_enqueue_script('jspdf-cme','https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',[],null,true);
$gas_url=defined('CME_APPS_SCRIPT_URL')?esc_js(CME_APPS_SCRIPT_URL):'';
$ajax_url=esc_js(admin_url('admin-ajax.php'));
$nonce=wp_create_nonce('cme_devis_nonce');
$enedis_nonce=wp_create_nonce('cme_enedis_nonce');
// Vérifier les constantes directement (sans dépendre du plugin Enedis)
$enedis_configured=(defined('CME_ENEDIS_CLIENT_ID')&&!empty(CME_ENEDIS_CLIENT_ID)
  &&defined('CME_ENEDIS_CLIENT_SECRET')&&!empty(CME_ENEDIS_CLIENT_SECRET))?'1':'';
ob_start();?>
<style>
/* ── Variables couleur (vert logo) ───────────────────────────── */
#<?php echo $uid;?>{
  --g1:#052e16;--g2:#166534;--g3:#16a34a;--g4:#15803d;
  --gb:#f0fdf4;--gbl:#bbf7d0;--gbm:#86efac;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  width:100%;max-width:1400px;margin:0 auto;background:#f1f5f9;
}
#<?php echo $uid;?> *{box-sizing:border-box;-webkit-text-size-adjust:100%}
/* ── Hero ─────────────────────────────────────────────────────── */
#<?php echo $uid;?> .ss-hero{background:linear-gradient(135deg,var(--g1) 0%,var(--g2) 55%,var(--g3) 100%);color:#fff;padding:2.25rem 2rem 2rem;display:flex;align-items:center;gap:2rem;flex-wrap:wrap}
#<?php echo $uid;?> .hero-text{flex:1;min-width:200px}
#<?php echo $uid;?> .hero-title{font-size:clamp(20px,3vw,28px);font-weight:800;margin:0 0 6px}
#<?php echo $uid;?> .hero-sub{font-size:clamp(13px,1.5vw,15px);opacity:.8;margin:0 0 12px;line-height:1.5}
#<?php echo $uid;?> .hbadge{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:20px;padding:4px 12px;font-size:12px;margin-right:6px;margin-bottom:4px;display:inline-block}
/* ── Layout 2 cols ────────────────────────────────────────────── */
#<?php echo $uid;?> .ss-body{display:grid;grid-template-columns:1fr;gap:0}
@media(min-width:860px){#<?php echo $uid;?> .ss-body{grid-template-columns:62% 38%}}
#<?php echo $uid;?> .ss-left{padding:1.25rem;display:flex;flex-direction:column;gap:12px}
#<?php echo $uid;?> .ss-right{padding:1.25rem 1.25rem 1.25rem 0;display:flex;flex-direction:column;gap:12px}
@media(max-width:859px){#<?php echo $uid;?> .ss-right{padding:0 1.25rem 1.25rem}}
@media(min-width:860px){#<?php echo $uid;?> .ss-right{position:sticky;top:0;align-self:start;max-height:100vh;overflow-y:auto}}
/* ── Cards ────────────────────────────────────────────────────── */
#<?php echo $uid;?> .sc{background:#fff;border-radius:14px;padding:1.25rem;box-shadow:0 1px 4px rgba(0,0,0,.06)}
#<?php echo $uid;?> .stitle{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;color:#111827;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #f3f4f6}
#<?php echo $uid;?> label{font-size:13px;color:#6b7280;display:block;margin-bottom:6px;font-weight:500}
#<?php echo $uid;?> .hint{font-size:12px;color:#9ca3af;margin-top:5px;line-height:1.4}
/* ── Adresse ──────────────────────────────────────────────────── */
#<?php echo $uid;?> .addr-row{display:flex;gap:8px}
#<?php echo $uid;?> .inp-wrap{flex:1;position:relative}
#<?php echo $uid;?> .addr-inp{width:100%;border:1.5px solid #e5e7eb;border-radius:10px;padding:0 14px;height:52px;font-size:16px;background:#f9fafb;color:#111827;outline:none;font-family:inherit;-webkit-appearance:none;transition:border .15s;display:block}
#<?php echo $uid;?> .addr-inp:focus{border-color:var(--g3);background:#fff;box-shadow:0 0 0 3px rgba(22,163,74,.1)}
#<?php echo $uid;?> .gps-btn{width:52px;height:52px;border:1.5px solid #e5e7eb;border-radius:10px;background:#f9fafb;font-size:18px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:all .15s}
#<?php echo $uid;?> .gps-btn:hover{border-color:var(--g3);background:var(--gb)}
/* ── Autocomplete ─────────────────────────────────────────────── */
#<?php echo $uid;?> .ac-drop{display:none;position:absolute;top:56px;left:0;right:0;background:#fff;border:1.5px solid var(--g3);border-radius:12px;z-index:99999;max-height:260px;overflow-y:auto;box-shadow:0 8px 28px rgba(22,163,74,.18)}
#<?php echo $uid;?> .ac-drop.open{display:block}
#<?php echo $uid;?> .ac-item{padding:11px 14px;cursor:pointer;border-bottom:1px solid #f3f4f6;transition:background .1s}
#<?php echo $uid;?> .ac-item:last-child{border-bottom:none}
#<?php echo $uid;?> .ac-item:hover{background:var(--gb)}
#<?php echo $uid;?> .ac-name{font-size:14px;color:#111827;font-weight:500}
#<?php echo $uid;?> .ac-ctx{font-size:11px;color:#6b7280;margin-top:2px}
/* ── Carte Leaflet ────────────────────────────────────────────── */
#<?php echo $uid;?> .map-box{height:220px;border-radius:12px;overflow:hidden;border:1px solid #e5e7eb;background:#e2e8f0;position:relative;margin-top:14px}
#<?php echo $uid;?> .map-loading{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:13px;color:#6b7280;gap:8px;background:#e2e8f0}
#<?php echo $uid;?> .map-spin{width:24px;height:24px;border:2.5px solid #e5e7eb;border-top-color:var(--g3);border-radius:50%;animation:sp .6s linear infinite}
/* ── Inputs ───────────────────────────────────────────────────── */
#<?php echo $uid;?> input[type=number]{border:1.5px solid #e5e7eb;border-radius:10px;padding:0 8px 0 14px;height:52px;font-size:16px;background:#f9fafb;color:#111827;width:100%;outline:none;font-family:inherit;-moz-appearance:textfield;transition:border .15s}
#<?php echo $uid;?> input[type=number]:focus{border-color:var(--g3);background:#fff;box-shadow:0 0 0 3px rgba(22,163,74,.1)}
#<?php echo $uid;?> input[type=number]::-webkit-inner-spin-button{-webkit-appearance:inner-spin-button;opacity:1;width:40px;height:52px;cursor:pointer;background:#f1f5f9;border-left:1px solid #e5e7eb}
#<?php echo $uid;?> .g2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
/* ── Toggles verts ────────────────────────────────────────────── */
#<?php echo $uid;?> .tog{display:flex;gap:8px}
#<?php echo $uid;?> .tbtn{flex:1;height:52px;border:1.5px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:14px;cursor:pointer;font-family:inherit;transition:all .15s;font-weight:500}
#<?php echo $uid;?> .tbtn.on{border-color:var(--g3);background:var(--g3);color:#fff;font-weight:600}
/* ── Stepper ──────────────────────────────────────────────────── */
#<?php echo $uid;?> .stepper{display:flex;align-items:center;border:1.5px solid #e5e7eb;border-radius:10px;overflow:hidden;background:#fff;height:52px}
#<?php echo $uid;?> .step-btn{width:52px;height:100%;border:none;background:transparent;font-size:22px;cursor:pointer;color:#374151;flex-shrink:0;transition:background .15s}
#<?php echo $uid;?> .step-btn:hover{background:var(--gb);color:var(--g4)}
#<?php echo $uid;?> .step-val{flex:1;text-align:center;font-size:18px;font-weight:700;color:#111827}
/* ── Slider vert ──────────────────────────────────────────────── */
#<?php echo $uid;?> .slval{font-size:26px;font-weight:800;color:var(--g3);text-align:center;margin-bottom:8px;letter-spacing:-1px}
#<?php echo $uid;?> .sinfo{font-size:12px;color:#6b7280;text-align:center;margin-top:6px;min-height:18px}
#<?php echo $uid;?> input[type=range]{width:100%;height:6px;-webkit-appearance:none;appearance:none;background:#e5e7eb;border-radius:3px;outline:none;cursor:pointer}
#<?php echo $uid;?> input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:24px;height:24px;border-radius:50%;background:var(--g3);cursor:pointer;border:3px solid #fff;box-shadow:0 1px 6px rgba(22,163,74,.4)}
#<?php echo $uid;?> input[type=range]::-moz-range-thumb{width:24px;height:24px;border-radius:50%;background:var(--g3);cursor:pointer;border:3px solid #fff}
#<?php echo $uid;?> .smarks{display:flex;justify-content:space-between;font-size:11px;color:#9ca3af;margin-top:6px}
/* ── Compass couleur unique ───────────────────────────────────── */
#<?php echo $uid;?> .compass{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}
#<?php echo $uid;?> .dbtn{height:54px;border:1.5px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:12px;cursor:pointer;font-family:inherit;transition:all .15s;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;font-weight:500}
#<?php echo $uid;?> .dbtn:hover{border-color:var(--gbm);background:var(--gb);color:var(--g4)}
#<?php echo $uid;?> .dbtn.on{border-color:var(--g3);background:var(--g3);color:#fff;font-weight:700;box-shadow:0 2px 8px rgba(22,163,74,.35)}
#<?php echo $uid;?> .dpct{font-size:10px;opacity:.7}
#<?php echo $uid;?> .ctr{height:54px;display:flex;align-items:center;justify-content:center;font-size:26px}
/* ── Options boutons verts ────────────────────────────────────── */
#<?php echo $uid;?> .opts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px}
#<?php echo $uid;?> .obtn{min-height:48px;border:1.5px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:13px;cursor:pointer;font-family:inherit;transition:all .15s;display:flex;align-items:center;justify-content:center;gap:6px;font-weight:500;padding:8px;text-align:center;line-height:1.3}
#<?php echo $uid;?> .obtn:hover{border-color:var(--gbm);background:var(--gb);color:var(--g4)}
#<?php echo $uid;?> .obtn.on{border-color:var(--g3);background:var(--gb);color:var(--g4);font-weight:600}
/* ── CTA principal ────────────────────────────────────────────── */
#<?php echo $uid;?> .cta-btn{width:100%;height:60px;border:none;border-radius:14px;background:linear-gradient(135deg,var(--g4),var(--g3));color:#fff;font-size:17px;font-weight:700;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:10px;box-shadow:0 4px 20px rgba(22,163,74,.4);transition:opacity .15s;margin-top:4px}
#<?php echo $uid;?> .cta-btn:hover{opacity:.9}
#<?php echo $uid;?> .cta-btn:disabled{opacity:.7;cursor:not-allowed}
/* ── Panneau droit ────────────────────────────────────────────── */
#<?php echo $uid;?> .ss-prev{background:#fff;border-radius:14px;padding:1.25rem;box-shadow:0 1px 4px rgba(0,0,0,.06)}
#<?php echo $uid;?> .prev-title{font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.07em;margin-bottom:12px}
#<?php echo $uid;?> .prev-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
#<?php echo $uid;?> .prev-card{background:#f8fafc;border-radius:10px;padding:10px;text-align:center}
#<?php echo $uid;?> .prev-val{font-size:17px;font-weight:700;color:var(--g4)}
#<?php echo $uid;?> .prev-lbl{font-size:11px;color:#6b7280;margin-top:2px}
#<?php echo $uid;?> .recap{background:#fff;border-radius:14px;padding:1.25rem;box-shadow:0 1px 4px rgba(0,0,0,.06)}
#<?php echo $uid;?> .recap-title{font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px}
#<?php echo $uid;?> .ri{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #f3f4f6}
#<?php echo $uid;?> .ri:last-child{border-bottom:none}
#<?php echo $uid;?> .ri-lbl{font-size:12px;color:#6b7280;flex:1}
#<?php echo $uid;?> .ri-val{font-size:12px;font-weight:600;color:#111827;text-align:right}
#<?php echo $uid;?> .ri-empty{color:#d1d5db;font-style:italic;font-weight:400}
/* ── Résultats ────────────────────────────────────────────────── */
#<?php echo $uid;?> .results{display:none;padding:1.25rem}
#<?php echo $uid;?> .results.show{display:block;animation:si .5s ease}
@keyframes si{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
#<?php echo $uid;?> .res-hero{background:linear-gradient(135deg,#0f172a 0%,var(--g1) 30%,var(--g2) 65%,var(--g3) 100%);border-radius:16px;padding:1.75rem;color:#fff;margin-bottom:12px}
#<?php echo $uid;?> .res-hero svg{display:block;margin:0 auto 16px}
#<?php echo $uid;?> .res-title{font-size:20px;font-weight:800;text-align:center;margin-bottom:6px}
#<?php echo $uid;?> .res-sub{font-size:13px;opacity:.7;text-align:center}
#<?php echo $uid;?> .res-list{list-style:none;padding:0;margin:16px 0 0}
#<?php echo $uid;?> .res-list li{display:flex;align-items:flex-start;gap:12px;padding:12px 0;border-bottom:1px solid rgba(255,255,255,.1)}
#<?php echo $uid;?> .res-list li:last-child{border-bottom:none}
#<?php echo $uid;?> .rli{font-size:20px;flex-shrink:0;margin-top:2px}
#<?php echo $uid;?> .rll{font-size:12px;opacity:.7;line-height:1.3}
#<?php echo $uid;?> .rlv{font-size:16px;font-weight:700;line-height:1.2;margin-top:2px}
#<?php echo $uid;?> .res-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
@media(max-width:480px){#<?php echo $uid;?> .res-cards{grid-template-columns:1fr 1fr}}
#<?php echo $uid;?> .rcard{background:#fff;border-radius:12px;padding:14px 10px;text-align:center;border:1px solid #f3f4f6}
#<?php echo $uid;?> .rcard-ico{font-size:22px;margin-bottom:4px}
#<?php echo $uid;?> .rcard-val{font-size:16px;font-weight:700;color:#111827}
#<?php echo $uid;?> .rcard.eco .rcard-val{color:var(--g3)}
#<?php echo $uid;?> .rcard.sol .rcard-val{color:#f59e0b}
#<?php echo $uid;?> .rcard-lbl{font-size:11px;color:#6b7280;margin-top:3px;line-height:1.3}
/* ── CTA2 devis ───────────────────────────────────────────────── */
#<?php echo $uid;?> .cta2{background:linear-gradient(135deg,var(--g4),var(--g3));border-radius:16px;padding:1.25rem;text-align:center;margin-bottom:12px}
#<?php echo $uid;?> .cta2 h3{font-size:16px;font-weight:700;color:#fff;margin:0 0 6px}
#<?php echo $uid;?> .cta2 p{font-size:13px;color:rgba(255,255,255,.85);margin:0 0 14px;line-height:1.4}
#<?php echo $uid;?> .cta2-btn{height:48px;padding:0 28px;border-radius:10px;background:#fff;color:var(--g4);font-size:15px;font-weight:700;cursor:pointer;border:none;font-family:inherit;transition:all .15s}
#<?php echo $uid;?> .cta2-btn:hover{background:var(--gb)}
/* ── Modal overlay ────────────────────────────────────────────── */
#<?php echo $uid;?> .modal-ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:999999;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(4px)}
#<?php echo $uid;?> .modal-ov.open{display:flex;animation:mf .2s ease}
@keyframes mf{from{opacity:0}to{opacity:1}}
#<?php echo $uid;?> .modal-box{background:#fff;border-radius:20px;width:100%;max-width:500px;max-height:92vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.35);position:relative;animation:ms .3s ease}
@keyframes ms{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}
@media(max-width:500px){#<?php echo $uid;?> .modal-ov{padding:0;align-items:flex-end}#<?php echo $uid;?> .modal-box{border-radius:20px 20px 0 0;max-height:95vh}}
#<?php echo $uid;?> .modal-head{background:linear-gradient(135deg,var(--g1),var(--g2),var(--g3));color:#fff;padding:1.4rem 1.5rem;border-radius:20px 20px 0 0;text-align:center}
#<?php echo $uid;?> .modal-head h3{font-size:18px;font-weight:700;margin:0 0 4px}
#<?php echo $uid;?> .modal-head p{font-size:13px;opacity:.8;margin:0}
#<?php echo $uid;?> .modal-close{position:absolute;top:14px;right:14px;width:32px;height:32px;border:none;background:rgba(255,255,255,.2);color:#fff;font-size:18px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center}
#<?php echo $uid;?> .modal-summ{background:#f8fafc;padding:14px 1.5rem;border-bottom:1px solid #e5e7eb}
#<?php echo $uid;?> .ms-label{font-size:11px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px}
#<?php echo $uid;?> .ms-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
#<?php echo $uid;?> .ms-card{background:#fff;border-radius:8px;padding:8px 10px;border:1px solid #e5e7eb}
#<?php echo $uid;?> .ms-card span{font-size:11px;color:#6b7280;display:block}
#<?php echo $uid;?> .ms-card strong{font-size:14px;font-weight:700;color:var(--g4)}
#<?php echo $uid;?> .modal-form{padding:1.25rem 1.5rem 1.5rem}
#<?php echo $uid;?> .mfrow{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}
#<?php echo $uid;?> .mfi{width:100%;border:1.5px solid #e5e7eb;border-radius:10px;padding:0 14px;height:48px;font-size:15px;background:#f9fafb;color:#111827;outline:none;font-family:inherit;transition:border .15s;display:block;margin-bottom:10px}
#<?php echo $uid;?> .mfi:focus{border-color:var(--g3);background:#fff;box-shadow:0 0 0 3px rgba(22,163,74,.1)}
#<?php echo $uid;?> .mfi:last-of-type{margin-bottom:0}
#<?php echo $uid;?> .rgpd{display:flex;align-items:flex-start;gap:10px;cursor:pointer;margin:12px 0;font-size:13px;color:#374151;line-height:1.5;user-select:none}
#<?php echo $uid;?> .rgpd input[type=checkbox]{width:18px;height:18px;flex-shrink:0;margin-top:2px;accent-color:var(--g3);cursor:pointer}
#<?php echo $uid;?> .rgpd a{color:var(--g3);text-decoration:underline}
#<?php echo $uid;?> .mferr{font-size:13px;color:#dc2626;margin-bottom:10px;padding:8px 12px;background:#fef2f2;border-radius:8px;border:1px solid #fecaca;display:none}
#<?php echo $uid;?> .modal-sub{width:100%;height:52px;border:none;border-radius:12px;background:linear-gradient(135deg,var(--g4),var(--g3));color:#fff;font-size:16px;font-weight:700;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:8px;box-shadow:0 4px 16px rgba(22,163,74,.35);transition:opacity .15s}
#<?php echo $uid;?> .modal-sub:hover{opacity:.9}
#<?php echo $uid;?> .modal-sub:disabled{opacity:.7;cursor:not-allowed}
#<?php echo $uid;?> .modal-ok{text-align:center;padding:2rem 1.5rem}
#<?php echo $uid;?> .ok-ico{width:64px;height:64px;background:var(--g3);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:28px;color:#fff}
#<?php echo $uid;?> .modal-ok h4{font-size:18px;font-weight:700;color:#111827;margin:0 0 8px}
#<?php echo $uid;?> .modal-ok p{font-size:14px;color:#6b7280;margin:0;line-height:1.5}
/* ── Misc ─────────────────────────────────────────────────────── */
#<?php echo $uid;?> .info-grn{background:var(--gb);border:1px solid var(--gbl);border-radius:8px;padding:9px 12px;font-size:13px;color:var(--g4);margin-top:8px;display:none}
#<?php echo $uid;?> .addr-status{font-size:12px;color:#6b7280;margin-top:5px;display:none}
#<?php echo $uid;?> select{border:1.5px solid #e5e7eb;border-radius:10px;padding:0 14px;height:52px;font-size:16px;background:#f9fafb;color:#111827;width:100%;outline:none;font-family:inherit;-webkit-appearance:none;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center;padding-right:36px;transition:border .15s}
#<?php echo $uid;?> select:focus{border-color:var(--g3);background-color:#fff}
#<?php echo $uid;?> .aide-row{display:flex;align-items:flex-start;gap:10px;padding:10px 0;border-bottom:1px solid #f3f4f6}
#<?php echo $uid;?> .aide-row:last-of-type{border-bottom:none}
#<?php echo $uid;?> .aide-ico{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0;margin-top:1px}
#<?php echo $uid;?> .aide-nom{font-size:13px;font-weight:600;color:#111827;margin-bottom:2px}
#<?php echo $uid;?> .aide-det{font-size:11px;color:#6b7280;line-height:1.4}
#<?php echo $uid;?> .aide-cond{font-size:11px;color:#16a34a;font-weight:500;margin-top:2px}
#<?php echo $uid;?> .aide-cond.no{color:#9ca3af}
#<?php echo $uid;?> .aide-amt{font-size:14px;font-weight:700;text-align:right;min-width:90px;flex-shrink:0;margin-top:2px}
#<?php echo $uid;?> .budget-summ{background:#f0fdf4;border-radius:10px;padding:14px;margin-top:8px;border:1px solid #bbf7d0}
#<?php echo $uid;?> .bs-row{display:flex;justify-content:space-between;font-size:13px;padding:3px 0}
#<?php echo $uid;?> .bs-net{display:flex;justify-content:space-between;align-items:baseline;margin-top:8px;padding-top:8px;border-top:1px solid #bbf7d0}
#<?php echo $uid;?> .dpe-row{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}
#<?php echo $uid;?> .dpe-btn{width:44px;height:44px;border-radius:8px;border:2.5px solid transparent;font-size:16px;font-weight:800;cursor:pointer;font-family:inherit;transition:all .15s;color:#fff;flex-shrink:0;display:flex;align-items:center;justify-content:center;text-align:center;line-height:1;padding:0}
#<?php echo $uid;?> .dpe-btn.on{border-color:#111;transform:scale(1.18);box-shadow:0 3px 10px rgba(0,0,0,.3);z-index:1;position:relative}
#<?php echo $uid;?> .dpe-info{font-size:12px;margin-top:8px;padding:8px 12px;border-radius:8px;border:1px solid #e5e7eb;background:#f9fafb;color:#374151;line-height:1.4}
#<?php echo $uid;?> .cop-wrap{margin-top:12px;padding:12px;background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0}
#<?php echo $uid;?> .linky-card{border:1.5px solid #bbf7d0;border-radius:12px;padding:14px;background:#f0fdf4;margin-top:12px;transition:all .3s}
#<?php echo $uid;?> .linky-card.connected{border-color:#16a34a;background:#dcfce7}
#<?php echo $uid;?> .linky-card.error{border-color:#fca5a5;background:#fef2f2}
#<?php echo $uid;?> .linky-title{font-size:13px;font-weight:600;color:#065f46;display:flex;align-items:center;gap:8px;margin-bottom:8px}
#<?php echo $uid;?> .linky-sub{font-size:12px;color:#6b7280;line-height:1.4;margin-bottom:10px}
#<?php echo $uid;?> .linky-btn{height:40px;padding:0 18px;border:none;border-radius:10px;background:var(--g3);color:#fff;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:opacity .15s;display:flex;align-items:center;gap:8px}
#<?php echo $uid;?> .linky-btn:hover{opacity:.85}
#<?php echo $uid;?> .linky-btn:disabled{opacity:.6;cursor:not-allowed}
#<?php echo $uid;?> .linky-status{font-size:13px;font-weight:600;color:#16a34a;margin-top:8px;display:none}
#<?php echo $uid;?> .linky-data{font-size:12px;color:#374151;margin-top:4px;line-height:1.5;display:none}
#<?php echo $uid;?> .linky-badge{display:inline-block;background:#16a34a;color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;margin-left:6px;vertical-align:middle}
#<?php echo $uid;?> .pdf-btn{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;height:52px;border-radius:12px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);color:#fff;font-size:15px;font-weight:700;cursor:pointer;border:none;font-family:inherit;transition:opacity .15s;margin-top:16px;margin-bottom:20px}
#<?php echo $uid;?> .pdf-btn:hover{opacity:.88}
#<?php echo $uid;?> .pdf-btn:disabled{opacity:.6;cursor:not-allowed}
#<?php echo $uid;?> .spin{display:inline-block;width:18px;height:18px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:sp .6s linear infinite}
#<?php echo $uid;?> .new-sim{width:100%;height:44px;border:1px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:13px;cursor:pointer;font-family:inherit;margin-bottom:12px;transition:all .15s}
#<?php echo $uid;?> .fnote{font-size:11px;color:#9ca3af;line-height:1.6;margin-bottom:8px}
@keyframes sp{to{transform:rotate(360deg)}}
@media(max-width:440px){#<?php echo $uid;?> .g2,#<?php echo $uid;?> .opts,#<?php echo $uid;?> .mfrow{grid-template-columns:1fr}#<?php echo $uid;?> .ss-left,#<?php echo $uid;?> .ss-right{padding:1rem}}
</style>
<div id="<?php echo $uid;?>"><p style="color:#9ca3af;font-size:14px;padding:1rem">⏳ Chargement...</p></div>
<script>
(function(){
'use strict';
var UID='<?php echo $uid;?>',
GEO='https://api-adresse.data.gouv.fr',
TRACK='https://cme-tracking-api-217943559750.europe-west1.run.app',
GAS_URL='<?php echo $gas_url;?>',
AJAX_URL='<?php echo $ajax_url;?>',
CME_NONCE='<?php echo $nonce;?>',
ENEDIS_NONCE='<?php echo $enedis_nonce;?>',
ENEDIS_OK='<?php echo $enedis_configured;?>';

/* ── Données ──────────────────────────────────────────────────── */
var IRRAD={'02':1100,'08':1140,'09':1450,'10':1180,'11':1520,'12':1390,'13':1620,'14':1110,'15':1300,'16':1330,'17':1350,'18':1220,'19':1290,'21':1270,'22':1090,'23':1250,'24':1380,'25':1230,'26':1420,'27':1120,'28':1170,'29':1100,'30':1520,'31':1480,'32':1470,'33':1400,'34':1560,'35':1110,'36':1240,'37':1220,'38':1380,'39':1250,'40':1430,'41':1210,'42':1310,'43':1350,'44':1150,'45':1200,'46':1380,'47':1400,'48':1420,'49':1180,'50':1100,'51':1170,'52':1190,'53':1130,'54':1170,'55':1160,'57':1180,'58':1260,'59':1020,'60':1120,'61':1130,'62':1010,'63':1290,'64':1380,'65':1440,'66':1580,'67':1200,'68':1220,'69':1340,'70':1220,'71':1290,'72':1160,'73':1320,'74':1330,'75':1180,'76':1080,'77':1200,'78':1190,'79':1220,'80':1090,'81':1490,'82':1460,'83':1620,'84':1580,'85':1200,'86':1240,'87':1250,'88':1180,'89':1220,'90':1210,'91':1185,'92':1180,'93':1175,'94':1190,'95':1185,'2A':1650,'2B':1640};
var ORI={'N':{l:'Nord',c:.45},'NE':{l:'Nord-Est',c:.65},'E':{l:'Est',c:.80},'SE':{l:'Sud-Est',c:.96},'S':{l:'Plein Sud',c:1},'SO':{l:'Sud-Ouest',c:.96},'O':{l:'Ouest',c:.80},'NO':{l:'Nord-Ouest',c:.65}};
var CH_LABELS={'elec':'Électrique','gaz':'Gaz','pac':'PAC','fioul':'Fioul','bois':'Bois'};

/* ── État ─────────────────────────────────────────────────────── */
var S={adresse:'',cp:'',lat:null,lng:null,statut:'proprio',habitants:2,surface:100,orientation:'S',pente:30,energies:['elec'],chauffage:'elec',eau:'elec',cuisson:'elec',pvgis_prod:null,pvgis_irrad:null,pvgis_monthly:null,annee_construction:2005,linky_kwh:null,linky_pdl:null,linky_kva:null,linky_tarif:null,linky_profile:null,dpe:'D',dpe_confirmed:false,cop:3.2,has_ve:false,km_ve:15000,vmc:'none'};

/* ── Helpers ──────────────────────────────────────────────────── */
function getDept(cp){if(!cp||cp.length<2)return null;return cp.substring(0,2)==='97'?cp.substring(0,3):cp.substring(0,2);}
function icf(d){d=Math.min(90,Math.max(0,parseInt(d)||30));if(d<=15)return .85+(d/15)*.12;if(d<=35)return .97+((d-15)/20)*.03;if(d<=60)return 1-((d-35)/25)*.14;return .86-((d-60)/30)*.21;}
function calcPrime(k){k=parseFloat(k)||0;if(k<=3)return Math.round(k*220);if(k<=9)return Math.round(3*220+(k-3)*120);if(k<=36)return Math.round(3*220+6*120+(k-9)*80);return Math.round(3*220+6*120+27*80+(k-36)*60);}
function $g(id){return document.getElementById(UID+'-'+id);}
function mk(t,c,x){var d=document.createElement(t);if(c)d.className=c;if(x!=null)d.textContent=x;return d;}
function ap(p,c){if(p&&c)p.appendChild(c);return p;}

function calcAll(){
  var dept=getDept(S.cp),irrad=IRRAD[dept]||1200;
  var oc=(ORI[S.orientation]||ORI.S).c,ic=icf(S.pente);
  var n=parseInt(S.habitants)||2,sf=parseInt(S.surface)||100;
  // Consommation : Linky (données réelles) en priorité, sinon DPE+COP
  if(S.linky_kwh&&S.linky_kwh>0){
    var conso=S.linky_kwh; // Données Enedis réelles
  } else {
  // Consommation avec DPE + COP (formule calibrée sur données ADEME)
  var besoin=(DPE_THERM[S.dpe]||190)*sf; // kWh thermiques chauffage
  var c_chauf=S.chauffage==='elec'?besoin:S.chauffage==='pac'?Math.round(besoin/(S.cop||3.2)):0;
  var c_ecs=S.eau==='elec'?n*800:S.eau==='pac'?n*250:0;
  var c_cuis=S.cuisson==='elec'||S.cuisson==='induction'?n*300:S.cuisson==='mixte'?n*150:0;
  var c_ve=S.has_ve?(S.km_ve||15000)*0.18:0;
  var c_vmc=S.vmc==='simple'?sf*3:S.vmc==='double'?sf*5:0;
  var conso=Math.round(c_chauf+c_ecs+c_cuis+n*500+sf*5+c_ve+c_vmc);
  } // fin else Linky
  var st=Math.round(sf*.30);
  var nb,kwc;
  if(S.linky_kwh&&S.linky_kwh>0&&S.pvgis_irrad&&S.pvgis_irrad>0){
    // Sizing optimal : conso réelle Linky / (irradiation PVGIS × pertes)
    var opt_kwc=S.linky_kwh/(S.pvgis_irrad*oc*ic*.80);
    var nb_opt=Math.ceil(opt_kwc/.4);
    var nb_roof=Math.max(2,Math.floor(st/1.73));
    nb=Math.min(nb_opt,nb_roof); // plafonné par la surface de toit
    kwc=nb*.4;
  } else {
    nb=Math.max(2,Math.floor(st/1.73));kwc=nb*.4;
  }
  var prod=S.pvgis_prod&&S.pvgis_prod>0?S.pvgis_prod:Math.round(kwc*irrad*oc*ic*.80);
  if(S.pvgis_irrad&&S.pvgis_irrad>0)irrad=S.pvgis_irrad;
  var ratio=Math.min(.82,conso>0?Math.min(.82,prod/conso*.75):.70);
  var ka=Math.round(prod*ratio),ks=Math.round(prod*(1-ratio));
  var budget=Math.round(kwc*2750),prime=calcPrime(kwc),eco=Math.round(ka*.19398),rev=Math.round(ks*.1301);
  return{nb:nb,surf_toit:st,kwc:kwc.toFixed(2),prod:prod,conso:Math.round(conso),eco:eco,rev:rev,roi:Math.round(Math.max(0,budget-prime)/(eco+rev||1)),co2:Math.round(prod*.238),reduc:conso>0?Math.min(100,Math.round(ka/conso*100)):0,budget:budget,prime:prime,irrad:irrad};
}

/* ── Carte Leaflet + ESRI satellite ───────────────────────────── */
var lMaps={};
function loadLeaflet(cb){
  if(window.L){cb();return;}
  if(!document.querySelector('link[href*="leaflet"]')){var lk=document.createElement('link');lk.rel='stylesheet';lk.href='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';document.head.appendChild(lk);}
  var s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
  s.onload=function(){setTimeout(cb,60);};document.head.appendChild(s);
}
function initMap(el,lat,lng,zoom,cb){
  if(!el||!window.L)return;
  if(el._lmap){try{el._lmap.remove();}catch(e){}}el.innerHTML='';
  var m=window.L.map(el,{center:[lat,lng],zoom:zoom,scrollWheelZoom:false});
  window.L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{attribution:'© Esri WorldImagery',maxZoom:19}).addTo(m);
  el._lmap=m;setTimeout(function(){m.invalidateSize();if(cb)cb(m);},150);
}
function placeMarker(m,lat,lng,label){
  if(!window.L||!m)return;
  if(m._marker){try{m.removeLayer(m._marker);}catch(e){}}
  var ico=window.L.divIcon({html:'<div style="width:18px;height:18px;background:#16a34a;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.5)"></div>',iconSize:[18,18],iconAnchor:[9,9],className:''});
  m._marker=window.L.marker([lat,lng],{icon:ico}).addTo(m).bindPopup(label||'Votre adresse').openPopup();
}
// Carte France par défaut (zoom 5) puis zoom sur adresse
function showFrance(boxes){
  boxes.forEach(function(el){
    if(!el)return;
    el.innerHTML='<div class="map-loading"><div class="map-spin"></div><span>Chargement carte...</span></div>';
  });
  loadLeaflet(function(){
    boxes.forEach(function(el){
      if(!el)return;
      el.innerHTML='';
      initMap(el,46.5,2.3,5);
    });
  });
}
function showMap(lat,lng,label){
  var boxes=[$g('map-d'),$g('map-m')];
  boxes.forEach(function(el){
    if(!el)return;
    if(el._lmap){el._lmap.setView([lat,lng],16);placeMarker(el._lmap,lat,lng,label);}
    else{
      el.innerHTML='<div class="map-loading"><div class="map-spin"></div><span>Carte satellite...</span></div>';
      loadLeaflet(function(){el.innerHTML='';initMap(el,lat,lng,16,function(m){placeMarker(m,lat,lng,label);});});
    }
  });
}

/* ── Prévisualisation en direct ───────────────────────────────── */
function updatePrev(){
  var R=calcAll();
  var pv={nb:R.nb+' panneaux',kwc:R.kwc+' kWc',eco:R.eco.toLocaleString('fr-FR')+'€/an',roi:R.roi+' ans'};
  Object.keys(pv).forEach(function(k){var el=$g('p-'+k);if(el)el.textContent=pv[k];});
  var yr=S.annee_construction||2005,yrA=2026-yr,yrL=yr<1975?'Avant 1975 ('+yrA+' ans)':String(yr)+' ('+yrA+' ans)';
  var chLbl=CH_LABELS[S.chauffage]||(S.chauffage);
  if(S.chauffage==='pac')chLbl='PAC — COP '+(S.cop||3.2);
  var rv={adr:S.adresse?(S.adresse.length>30?S.adresse.substring(0,30)+'…':S.adresse):'—',sf:S.surface?S.surface+' m²':'—',hab:(S.habitants>=5?'5+':String(S.habitants))+' habitant'+(S.habitants>1?'s':''),annee:yrL,ori:(ORI[S.orientation]||ORI.S).l,pente:S.pente+'°',ch:chLbl,dpe:S.dpe?('Classe '+S.dpe+' — '+(DPE_THERM[S.dpe]||190)+' kWh/m²'):'—',vmc:({'none':'Naturelle','simple':'Simple flux','double':'Double flux'}[S.vmc]||'—'),ve:S.has_ve?(S.km_ve||15000).toLocaleString('fr-FR')+' km/an':'Non',linky:S.linky_kwh&&S.linky_kwh>0?S.linky_kwh.toLocaleString('fr-FR')+' kWh · '+(S.linky_tarif||'')+(S.linky_kva?' · '+S.linky_kva+' kVA':''):null};
  Object.keys(rv).forEach(function(k){var el=$g('r-'+k);if(el){var v=rv[k];if(v===null||v===undefined){el.style.display='none';el.parentElement.style.display='none';}else{el.parentElement.style.display='';el.textContent=v;el.className='ri-val'+(v==='—'?' ri-empty':'');}}});
}

/* ── Autocomplete adresse ──────────────────────────────────────── */
var acT;
function setupAddr(inp,drop,irrEl,stEl){
  inp.addEventListener('input',function(){
    clearTimeout(acT);var q=inp.value.trim();
    if(q.length<3){drop.className='ac-drop';drop.innerHTML='';return;}
    acT=setTimeout(function(){
      fetch(GEO+'/search/?q='+encodeURIComponent(q)+'&limit=6&autocomplete=1')
        .then(function(r){return r.json();}).then(function(d){
          var feats=(d.features||[]).slice(0,5);drop.innerHTML='';
          if(!feats.length){drop.className='ac-drop';return;}
          feats.forEach(function(f){
            var p=f.properties,it=mk('div','ac-item');
            ap(it,mk('div','ac-name',p.label));ap(it,mk('div','ac-ctx',p.context||''));
            it.addEventListener('mousedown',function(e){
              e.preventDefault();
              S.adresse=p.label;S.cp=p.postcode||'';inp.value=p.label;drop.className='ac-drop';drop.innerHTML='';
              if(f.geometry&&f.geometry.coordinates){S.lng=f.geometry.coordinates[0];S.lat=f.geometry.coordinates[1];showMap(S.lat,S.lng,p.label);}
              var dept=getDept(S.cp);if(dept&&IRRAD[dept]&&irrEl){irrEl.textContent='☀️ '+p.city+' : '+IRRAD[dept]+' kWh/m²/an';irrEl.style.display='block';}
              updatePrev();debouncedPVGIS();
            });
            ap(drop,it);
          });drop.className='ac-drop open';
        }).catch(function(){drop.className='ac-drop';});
    },280);
  });
  inp.addEventListener('blur',function(){setTimeout(function(){drop.className='ac-drop';},180);});
  inp.addEventListener('keydown',function(e){if(e.key==='Escape')drop.className='ac-drop';});
}
function doGPS(inp,irrEl,stEl){
  if(!navigator.geolocation){stEl.textContent='Géolocalisation non disponible';stEl.style.display='block';return;}
  stEl.textContent='📡 Localisation...';stEl.style.display='block';
  navigator.geolocation.getCurrentPosition(function(pos){
    S.lat=pos.coords.latitude;S.lng=pos.coords.longitude;
    fetch(GEO+'/reverse/?lat='+S.lat+'&lon='+S.lng).then(function(r){return r.json();}).then(function(d){
      stEl.style.display='none';
      if(d.features&&d.features[0]){var p=d.features[0].properties;S.adresse=p.label;S.cp=p.postcode||'';inp.value=p.label;adSt.style.display='none';adI.style.borderColor='';showMap(S.lat,S.lng,p.label);var dept=getDept(S.cp);if(dept&&IRRAD[dept]&&irrEl){irrEl.textContent='☀️ '+p.city+' : '+IRRAD[dept]+' kWh/m²/an';irrEl.style.display='block';}updatePrev();debouncedPVGIS();}
    }).catch(function(){stEl.textContent='Erreur';});
  },function(){stEl.textContent='Accès refusé';stEl.style.display='block';});
}

/* ── SVG maison ────────────────────────────────────────────────── */
function makeSVG(){return '<svg width="200" height="110" viewBox="0 0 200 110" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="sg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#fef3c7"/><stop offset="100%" stop-color="#fcd34d"/></linearGradient></defs><circle cx="168" cy="24" r="15" fill="url(#sg)"/><line x1="168" y1="4" x2="168" y2="1" stroke="#fcd34d" stroke-width="2.5" stroke-linecap="round"/><line x1="168" y1="44" x2="168" y2="47" stroke="#fcd34d" stroke-width="2.5" stroke-linecap="round"/><line x1="147" y1="24" x2="144" y2="24" stroke="#fcd34d" stroke-width="2.5" stroke-linecap="round"/><line x1="189" y1="24" x2="192" y2="24" stroke="#fcd34d" stroke-width="2.5" stroke-linecap="round"/><rect x="18" y="68" width="114" height="42" rx="2" fill="#d1fae5"/><polygon points="8,68 75,22 142,68" fill="#052e16"/><rect x="36" y="41" width="21" height="13" rx="2" fill="#4ade80" opacity=".9"/><rect x="59" y="35" width="21" height="13" rx="2" fill="#16a34a"/><rect x="82" y="41" width="21" height="13" rx="2" fill="#4ade80" opacity=".9"/><line x1="46" y1="41" x2="46" y2="54" stroke="#fff" stroke-width=".7" opacity=".5"/><line x1="36" y1="47" x2="57" y2="47" stroke="#fff" stroke-width=".7" opacity=".5"/><line x1="69" y1="35" x2="69" y2="48" stroke="#fff" stroke-width=".7" opacity=".5"/><line x1="59" y1="41" x2="80" y2="41" stroke="#fff" stroke-width=".7" opacity=".5"/><line x1="92" y1="41" x2="92" y2="54" stroke="#fff" stroke-width=".7" opacity=".5"/><line x1="82" y1="47" x2="103" y2="47" stroke="#fff" stroke-width=".7" opacity=".5"/><rect x="64" y="88" width="20" height="22" rx="2" fill="#94a3b8"/><rect x="25" y="79" width="16" height="13" rx="1" fill="#6ee7b7" opacity=".8"/><rect x="100" y="79" width="16" height="13" rx="1" fill="#6ee7b7" opacity=".8"/><rect x="0" y="107" width="200" height="4" rx="2" fill="#16a34a" opacity=".5"/></svg>';}

/* ── Construction formulaire ───────────────────────────────────── */
function svgI(p,s){s=s||18;return '<svg width="'+s+'" height="'+s+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'+p+'</svg>';}
var SI={loc:'<path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/>',home:'<path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9,22 9,12 15,12 15,22"/>',bolt:'<polygon points="13,2 3,14 12,14 11,22 21,10 12,10 13,2"/>'};
function mkTit(ico,txt){var d=mk('div','stitle');d.innerHTML=svgI(SI[ico])+' '+txt;return d;}

/* ── API PVGIS ───────────────────────────────────────────────────────────── */
var pvgisT=null;
function debouncedPVGIS(){clearTimeout(pvgisT);pvgisT=setTimeout(callPVGIS,900);}
function callPVGIS(){
  if(!S.lat||!S.lng)return;
  var R=calcAll(),kwc=parseFloat(R.kwc)||0;if(kwc<=0)return;
  var ASP={'S':0,'SE':-45,'E':-90,'NE':-135,'N':180,'NO':135,'O':90,'SO':45};
  var aspect=ASP[S.orientation]!==undefined?ASP[S.orientation]:0;
  var angle=Math.min(90,Math.max(0,parseInt(S.pente)||30));
  var el=$g('pvgis-st');
  if(el){el.textContent='⏳ Calcul satellite PVGIS...';el.style.color='var(--text-secondary)';}
  // Proxy WordPress (évite CORS — PVGIS bloque les appels directs depuis le navigateur)
  var pfd=new FormData();
  pfd.append('action','cme_pvgis');
  pfd.append('lat',S.lat.toFixed(6));
  pfd.append('lon',S.lng.toFixed(6));
  pfd.append('kw',kwc.toFixed(3));
  pfd.append('aspect',aspect);
  pfd.append('angle',angle);
  fetch(AJAX_URL,{method:'POST',body:pfd})
    .then(function(r){return r.json();})
    .then(function(resp){
      if(resp.success&&resp.data&&resp.data.outputs&&resp.data.outputs.totals&&resp.data.outputs.totals.fixed){
        var f=resp.data.outputs.totals.fixed;
        S.pvgis_prod=Math.round(f['E_y']||0);
        S.pvgis_irrad=Math.round(f['H(i)_y']||0);
        S.pvgis_monthly=(resp.data.outputs.monthly&&resp.data.outputs.monthly.fixed)||null;
        if(el){el.textContent='☀️ Source : PVGIS — JRC/Commission Européenne';el.style.color='var(--text-success)';}
        updatePrev();
      } else {
        console.warn('PVGIS:',resp);if(el)el.textContent='';
      }
    })
    .catch(function(err){console.warn('PVGIS proxy:',err);if(el)el.textContent='';});
}
/* ── calcAides ─────────────────────────────────────────────────────────── */

/* ── Table aides régionales par département ─────────────────────────────────── */
var REG_DEPT={
  '22':'BR','29':'BR','35':'BR','56':'BR',
  '44':'PL','49':'PL','53':'PL','72':'PL','85':'PL',
  '14':'NM','27':'NM','50':'NM','61':'NM','76':'NM',
  '02':'HF','59':'HF','60':'HF','62':'HF','80':'HF',
  '08':'GE','10':'GE','51':'GE','52':'GE','54':'GE','55':'GE','57':'GE','67':'GE','68':'GE','88':'GE',
  '75':'IF','77':'IF','78':'IF','91':'IF','92':'IF','93':'IF','94':'IF','95':'IF',
  '18':'CV','28':'CV','36':'CV','37':'CV','41':'CV','45':'CV',
  '21':'BF','25':'BF','39':'BF','58':'BF','70':'BF','71':'BF','89':'BF','90':'BF',
  '01':'AR','03':'AR','07':'AR','15':'AR','26':'AR','38':'AR','42':'AR','43':'AR','63':'AR','69':'AR','73':'AR','74':'AR',
  '16':'NA','17':'NA','19':'NA','23':'NA','24':'NA','33':'NA','40':'NA','47':'NA','64':'NA','79':'NA','86':'NA','87':'NA',
  '09':'OC','11':'OC','12':'OC','30':'OC','31':'OC','32':'OC','34':'OC','46':'OC','48':'OC','65':'OC','66':'OC','81':'OC','82':'OC',
  '04':'PA','05':'PA','06':'PA','13':'PA','83':'PA','84':'PA',
  '2A':'CO','2B':'CO'
};
var AIDES_REG={
  'BR':{reg:'Bretagne',prog:'Breizh Énergies',min:500,max:1500,url:'https://www.bretagne.bzh'},
  'PL':{reg:'Pays de la Loire',prog:'Énergie Pays de la Loire',min:400,max:1000,url:'https://www.paysdelaloire.fr'},
  'NM':{reg:'Normandie',prog:'Aide Énergie Normandie',min:300,max:800,url:'https://www.normandie.fr'},
  'HF':{reg:'Hauts-de-France',prog:'Energif Hauts-de-France',min:400,max:1200,url:'https://www.hautsdefrance.fr'},
  'GE':{reg:'Grand Est',prog:'Grand Est Énergie',min:300,max:1000,url:'https://www.grandest.fr'},
  'IF':{reg:'Île-de-France',prog:null,min:0,max:0,url:'https://www.iledefrance.fr'},
  'CV':{reg:'Centre-Val de Loire',prog:'Aide Énergie CVL',min:300,max:800,url:'https://www.regioncentre-valdeloire.fr'},
  'BF':{reg:'Bourgogne-Franche-Comté',prog:'BFC Énergie',min:300,max:800,url:'https://www.bourgognefranchecomte.fr'},
  'AR':{reg:'Auvergne-Rhône-Alpes',prog:'AURA Autoconsommation',min:500,max:1500,url:'https://www.auvergnerhonealpes.fr'},
  'NA':{reg:'Nouvelle-Aquitaine',prog:'NA Énergie',min:500,max:2000,url:'https://www.nouvelle-aquitaine.fr'},
  'OC':{reg:'Occitanie',prog:'Chèque Occitanie Énergie',min:500,max:2000,url:'https://www.laregion.fr'},
  'PA':{reg:'Région PACA',prog:'PACA Solaire',min:700,max:2500,url:'https://www.maregionsud.fr'},
  'CO':{reg:'Corse',prog:'ADEC Solaire',min:800,max:3000,url:'https://www.adec.corsica'}
};
function calcAides(R){
  var dept=getDept(S.cp)||'75';
  var kwc=parseFloat(R.kwc)||0;
  var age=2026-(S.annee_construction||2005);
  var proprio=S.statut==='proprio';
  var lgt_ok=age>=2;
  var tva_gain=lgt_ok&&kwc<=36?Math.round(R.budget*10/120):0;
  var cPrime=kwc<=3?'220€/kWc':kwc<=9?'Tranches 220→120€/kWc':'Tranches 120→80€/kWc';
  var cTva=lgt_ok&&kwc<=36?'Incluse dans la facture installateur RGE':'Non éligible';
  var cPtz=proprio&&lgt_ok?'Via votre banque (ANAH) — éligible':'Non éligible';
  var dTva=lgt_ok?'Logement de '+age+' ans · Installation ≤36 kWc':'Non éligible ('+(age<2?'logement < 2 ans':'> 36 kWc')+')';
  var dPtz=proprio&&lgt_ok?'Logement de '+age+' ans · Jusqu’à 50 000€ à 0%':'Non éligible ('+(proprio?'logement < 2 ans':'locataire')+')';
  return[
    {id:'prime',nom:'Prime autoconsommation',montant:R.prime,eligible:true,type:'subvention',
     detail:'Versée par EDF OA · Tarif S1 2026 · Mise à jour trimestrielle',cond:cPrime},
    {id:'tva',nom:'TVA réduite à 10%',montant:tva_gain,eligible:lgt_ok&&kwc<=36,type:'reduction',
     detail:dTva,cond:cTva},
    {id:'ecoPtz',nom:'Éco-PTZ taux zéro',montant:proprio&&lgt_ok?Math.min(50000,R.budget):0,eligible:proprio&&lgt_ok,type:'pret',
     detail:dPtz,cond:cPtz},
    (function(){
      var rc=REG_DEPT[dept],ar=rc?AIDES_REG[rc]:null;
      var moy=ar&&ar.max>0?Math.round((ar.min+ar.max)/2):0;
      var nom=ar?ar.reg+' — '+(ar.prog||'Aides locales'):'Aides régionales & locales';
      var det=ar&&ar.max>0?'∼ '+ar.min.toLocaleString('fr-FR')+' à '+ar.max.toLocaleString('fr-FR')+'€ · Sous conditions de ressources · Montants indicatifs 2026':'Programmes variables selon votre collectivité';
      var cond=ar&&ar.prog?'Organisme : '+ar.prog+' · France Rénov’ (0 800 321 321)':'France Rénov’ · SARE (0 800 321 321)';
      return {id:'local',nom:nom,montant:moy,eligible:null,type:'variable',detail:det,cond:cond};
    })()
  ];
}
function estimDPE(yr){
  return yr<1948?'G':yr<1975?'F':yr<1989?'E':yr<2001?'D':yr<2011?'D':yr<2021?'C':'B';
}
/* ── DPE + COP ─────────────────────────────────────────────────────────────── */
var DPE_THERM={A:35,B:70,C:120,D:190,E:280,F:390,G:550}; // kWh thermiques/m²/an
var DPE_COL={A:'#00a84f',B:'#51b848',C:'#bcd630',D:'#f9c000',E:'#f07900',F:'#e73a1b',G:'#c00'};
var DPE_LBL={A:'Excellente énergétique',B:'Très bonne',C:'Bonne',D:'Moyenne (la plus courante)',E:'Mauvaise',F:'Très mauvaise',G:'Passoire thermique'};

/* -- ROI chart SVG epure (zero texte sur courbes) --------------------------- */
function buildROIChart(R,netBudget){
  var YEARS=25,W=680,H=220,PL=60,PR=16,PT=12,PB=32;
  var CW=W-PL-PR,CH=H-PT-PB;
  var SCN=[{r:.03,c:'#3b82f6'},{r:.05,c:'#16a34a'},{r:.07,c:'#f59e0b'}];
  var eco=R.eco||0,rev=R.rev||0;
  function cumul(rate,yr){var t=0;for(var y=1;y<=yr;y++){t+=(eco*Math.pow(1+rate,y-1)+rev)*Math.pow(.995,y-1);}return Math.round(t);}
  var maxV=cumul(.07,25);
  var step=maxV<15000?2000:maxV<35000?5000:maxV<70000?10000:20000;
  maxV=Math.ceil(maxV/step)*step||10000;
  function xs(y){return PL+(y/YEARS)*CW;}
  function ys(v){return PT+CH-Math.min(1,Math.max(0,v/maxV))*CH;}
  var svg='<svg width="100%" viewBox="0 0 '+W+' '+H+'" xmlns="http://www.w3.org/2000/svg" style="display:block">';
  // Fond
  svg+='<rect x="'+PL+'" y="'+PT+'" width="'+CW+'" height="'+CH+'" fill="#fafafa" rx="3"/>';
  // Grille horizontale + labels Y
  var nb=Math.round(maxV/step);
  for(var i=0;i<=nb;i++){var gv=step*i,gy=ys(gv);
    svg+='<line x1="'+PL+'" y1="'+gy+'" x2="'+(W-PR)+'" y2="'+gy+'" stroke="'+(i===0?'#e5e7eb':'#f3f4f6')+'" stroke-width="'+(i===0?1:.7)+'"/>';
    var lbl=gv>=1000?(gv/1000)+'k€':gv+'€';
    svg+='<text x="'+(PL-6)+'" y="'+(gy+4)+'" text-anchor="end" font-size="10" fill="#9ca3af">'+lbl+'</text>';
  }
  // Jalons X (5, 10, 15, 20, 25)
  [5,10,15,20,25].forEach(function(yr){var gx=xs(yr);
    svg+='<line x1="'+gx+'" y1="'+PT+'" x2="'+gx+'" y2="'+(PT+CH)+'" stroke="#f3f4f6" stroke-width=".7" stroke-dasharray="2,4"/>';
    svg+='<text x="'+gx+'" y="'+(PT+CH+14)+'" text-anchor="middle" font-size="10" fill="#9ca3af">'+yr+'</text>';
  });
  svg+='<text x="'+PL+'" y="'+(PT+CH+14)+'" text-anchor="middle" font-size="10" fill="#9ca3af">0</text>';
  // Ligne seuil
  if(netBudget>0&&netBudget<maxV){var by=ys(netBudget);
    svg+='<line x1="'+PL+'" y1="'+by+'" x2="'+(W-PR)+'" y2="'+by+'" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="6,4"/>';}
  // Courbes + traits verticaux de rentabilite (pas de chevauchement possible)
  SCN.forEach(function(s){var pts=[],ryr=null;
    for(var y=0;y<=YEARS;y++){var val=y===0?0:cumul(s.r,y);pts.push(xs(y)+','+ys(val));if(ryr===null&&val>=netBudget&&netBudget>0)ryr=y;}
    svg+='<polyline points="'+pts.join(' ')+'" fill="none" stroke="'+s.c+'" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>';
    if(ryr!==null&&ryr>0){
      var mx=xs(ryr),my=ys(netBudget);
      // Petit trait vertical (au lieu d'un cercle) : jamais de chevauchement visuel
      svg+='<line x1="'+mx+'" y1="'+(my-6)+'" x2="'+mx+'" y2="'+(my+6)+'" stroke="'+s.c+'" stroke-width="2.5" stroke-linecap="round"/>';
    }
  });
  // Axes
  svg+='<line x1="'+PL+'" y1="'+PT+'" x2="'+PL+'" y2="'+(PT+CH)+'" stroke="#d1d5db" stroke-width="1.2"/>';
  svg+='<line x1="'+PL+'" y1="'+(PT+CH)+'" x2="'+(W-PR)+'" y2="'+(PT+CH)+'" stroke="#d1d5db" stroke-width="1.2"/>';
  svg+='</svg>';
  return svg;
}

/* -- Fallback HTML imprimable si jsPDF indisponible ------------------------- */
function genererHTMLImpression(S,R,aidesData,netBudget){
  var pri_g=(aidesData.find(function(a){return a.id==='prime';})||{montant:0}).montant||0;
  var tva_a=aidesData.find(function(a){return a.id==='tva';})||{montant:0,eligible:false};
  var tva_g=tva_a&&tva_a.eligible?tva_a.montant:0;
  function f(n){var s=Math.round(n||0).toString();return s.replace(/\B(?=(\d{3})+(?!\d))/g,'\u202f');}
  var d=new Date().toLocaleDateString('fr-FR');
  return'<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>Estimation Solaire CME</title><style>'
  +'@page{size:A4;margin:18mm}body{font-family:Arial,sans-serif;font-size:11pt;color:#111;}'
  +'.hd{background:#16a34a;color:#fff;padding:14px 20px;border-radius:8px;margin-bottom:18px}'
  +'.hd h1{margin:0;font-size:18pt}.hd p{margin:4px 0 0;font-size:9pt;opacity:.85}'
  +'.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}'
  +'.kpi-box{border:2px solid #16a34a;border-radius:6px;padding:8px;text-align:center}'
  +'.kpi-val{font-size:16pt;font-weight:700;color:#16a34a}.kpi-lbl{font-size:8pt;color:#666}'
  +'.sec{margin:14px 0}.sec-h{background:#f0fdf4;border-left:4px solid #16a34a;padding:6px 10px;font-weight:700;font-size:10pt;margin-bottom:8px}'
  +'table{width:100%;border-collapse:collapse;font-size:9.5pt}'
  +'td{padding:4px 6px;border-bottom:1px solid #f3f4f6}'
  +'td:first-child{color:#6b7280;width:45%}td:last-child{font-weight:600}'
  +'.net{background:#f0fdf4;border:2px solid #16a34a;border-radius:6px;padding:10px;text-align:center;margin:10px 0}'
  +'.net strong{font-size:14pt;color:#16a34a}.ft{margin-top:20px;border-top:1px solid #e5e7eb;padding-top:8px;font-size:8pt;color:#9ca3af;text-align:center}'
  +'@media print{.no-print{display:none}}'
  +'</style></head><body>'
  +'<div class="hd"><h1>☀️ Estimation Solaire Personnalisée</h1><p>'+S.adresse+' &nbsp;|&nbsp; Genere le '+d+'</p></div>'
  +'<div class="kpi">'
  +'<div class="kpi-box"><div class="kpi-val">'+R.nb+'</div><div class="kpi-lbl">panneaux</div></div>'
  +'<div class="kpi-box"><div class="kpi-val">'+f(R.prod)+'</div><div class="kpi-lbl">kWh/an produits</div></div>'
  +'<div class="kpi-box"><div class="kpi-val">'+f(netBudget)+'€</div><div class="kpi-lbl">budget net</div></div>'
  +'<div class="kpi-box"><div class="kpi-val">'+R.roi+' ans</div><div class="kpi-lbl">retour invest.</div></div>'
  +'</div>'
  +'<div class="sec"><div class="sec-h">Installation photovoltaïque</div><table>'
  +'<tr><td>Adresse</td><td>'+S.adresse+'</td></tr>'
  +'<tr><td>Puissance installée</td><td>'+R.kwc+' kWc ('+R.nb+' panneaux 400 Wc)</td></tr>'
  +'<tr><td>Production annuelle</td><td>'+f(R.prod)+' kWh/an</td></tr>'
  +'<tr><td>Irradiation</td><td>'+f(R.irrad)+' kWh/m²/an'+(S.pvgis_irrad?' (PVGIS satellite)':' (estimation)'+'</td></tr>')
  +'<tr><td>Orientation / Pente</td><td>'+(S.orientation||'S')+' / '+(S.pente||30)+'°</td></tr>'
  +'<tr><td>DPE</td><td>Classe '+(S.dpe||'D')+'</td></tr>'
  +'</table></div>'
  +'<div class="sec"><div class="sec-h">Analyse financière</div><table>'
  +'<tr><td>Budget installation TTC</td><td>'+f(R.budget)+'€</td></tr>'
  +'<tr><td>Prime autoconsommation</td><td>- '+f(pri_g)+'€</td></tr>'
  +(tva_g?'<tr><td>TVA réduite 10%</td><td>- '+f(tva_g)+'€</td></tr>':'')
  +'<tr><td>Economies autoconso.</td><td>'+f(R.eco)+'€/an</td></tr>'
  +'<tr><td>Revenus revente surplus</td><td>'+f(R.rev)+'€/an</td></tr>'
  +'<tr><td>CO₂ évité</td><td>'+f(R.co2)+' kg/an</td></tr>'
  +'</table>'
  +'<div class="net"><strong>Budget net après aides : '+f(netBudget)+'€</strong></div></div>'
  +'<div class="ft">comprendre-mon-energie.fr &nbsp;|&nbsp; contact@comprendre-mon-energie.fr &nbsp;|&nbsp; 61 rue de Lyon 75012 Paris</div>'
  +'<div class="no-print" style="margin-top:16px;text-align:center">'
  +'<button onclick="window.print()" style="padding:10px 24px;background:#16a34a;color:#fff;border:none;border-radius:8px;font-size:13px;cursor:pointer">'
  +'💾 Enregistrer en PDF</button></div>'
  +'</body></html>';
}

/* ── Génération PDF 360° ─────────────────────────────────────────────────── */
/* Formateur nombre PDF — evite les espaces insecables de fr-FR */
function fmtNum(n){
  if(n===null||n===undefined||isNaN(n))return '-';
  var s=Math.round(n).toString();
  return s.replace(/\B(?=(\d{3})+(?!\d))/g,' '); /* espace fine */
}
var PDF_LEGAL = [
  'POLITIQUE DE CONFIDENTIALITE (RGPD)',
  '',
  'Comprendre Mon Energie s\'engage en faveur de la protection de vos donnees personnelles.',
  'En application du RGPD, nous vous communiquons les conditions dans lesquelles vos donnees',
  'personnelles sont traitees par nos soins.',
  '',
  'DONNEES COLLECTEES : coordonnees (nom, prenom, telephone, email), preferences,',
  'informations techniques et de localisation. Aucune donnee sensible n\'est collectee.',
  '',
  'FONDEMENTS JURIDIQUES : consentement (art. 6.1.a RGPD), execution d\'un contrat,',
  'interet legittime (art. 6.1.e RGPD), obligation legale.',
  '',
  'DUREE DE CONSERVATION : 3 ans a compter de la collecte, sauf obligations legales.',
  'Donnees contractuelles : duree de la relation commerciale + 5 ou 10 ans selon le cas.',
  '',
  'VOS DROITS : rectification, effacement, limitation, portabilite, opposition,',
  'retrait du consentement, plainte aupres de la CNIL.',
  'Contact DPO : contact@comprendre-mon-energie.fr',
  'CNIL - 3 Place de Fontenoy - TSA 80715 - 75334 Paris Cedex 07',
  '',
  'MENTIONS LEGALES',
  '',
  'Editeur : Comprendre Mon Energie',
  'Capital : 5 000 EUR | ICE : 003941396000038',
  'Siege social : 61 rue de Lyon - 75012 Paris',
  'Directeur de la publication : Blal Oussama',
  'Email : contact@comprendre-mon-energie.fr',
  'Site : https://www.comprendre-mon-energie.fr',
  '',
  'Hebergeur : O2switch - Clermont-Ferrand - Capital 100 000 EUR',
  'Tel : +33 4 44 44 60 40 | support@o2switch.fr',
  '',
  'POLITIQUE DE COOKIES',
  '',
  'Les cookies sont de petits fichiers texte enregistres sur votre appareil lors de la',
  'visite du site. Ils facilitent votre experience en sauvegardant vos preferences.',
  '',
  'Types utilises :',
  '- Cookies strictement necessaires (fonctionnement du site - PHPSESSID)',
  '- Cookies de performance (Google Analytics : _ga, _gid, _gat)',
  '  _ga : 2 ans | _gid : 1 jour | _gat : 1 minute',
  '',
  'Vous pouvez gerer vos preferences de cookies a tout moment sur notre site.',
  '',
  'Version complete : https://www.comprendre-mon-energie.fr/politique-de-cookies-ue/',
  'Politique de confidentialite : https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/'
];

async function genererPDF(S, R, aidesData, netBudget) {
  // Attendre que jsPDF soit disponible (charge par WordPress)
  var _jspdfWait = 0;
  while (!window.jspdf && _jspdfWait < 80) {
    await new Promise(function(r){ setTimeout(r, 100); });
    _jspdfWait++;
  }
  if (!window.jspdf) {
    // Fallback : charger depuis CDN si wp_enqueue n'a pas fonctionne
    await new Promise(function(resolve, reject) {
      var s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
      var t = setTimeout(function(){ reject(new Error('CDN timeout')); }, 10000);
      s.onload = function(){ clearTimeout(t); resolve(); };
      s.onerror = function(){ clearTimeout(t); reject(new Error('CDN erreur')); };
      document.head.appendChild(s);
    });
  }
  if (!window.jspdf) throw new Error('jsPDF non disponible');

  var jsPDF = window.jspdf.jsPDF;
  var doc = new jsPDF({ unit:'mm', format:'a4', orientation:'portrait' });
  var PW=210, PH=297, MAR=15, CW=180;
  var GRN=[22,163,74], DRK=[17,24,39], GRY=[107,114,128], LGT=[243,244,246];
  var tva_a=aidesData.find(function(a){return a.id==='tva';})||{montant:0,eligible:false};
  var pri_a=aidesData.find(function(a){return a.id==='prime';})||{montant:0};
  var tva_g=tva_a&&tva_a.eligible?tva_a.montant:0;
  var pri_g=pri_a?pri_a.montant:0;
  var today = new Date().toLocaleDateString('fr-FR');
  var pageNum = 0;

  // Charger le logo
  var logoB64 = null, logoW = 42, logoH = 14;
  try {
    var fd = new FormData(); fd.append('action','cme_logo_b64');
    var lr = await fetch(AJAX_URL, {method:'POST', body:fd});
    var ld = await lr.json();
    if (ld.success) {
      logoB64 = ld.data.b64;
      // Calculer les dimensions proportionnelles
      await new Promise(function(res){
        var tmpI = new Image();
        tmpI.onload = function(){
          if(tmpI.naturalWidth > 0) logoH = logoW * tmpI.naturalHeight / tmpI.naturalWidth;
          res();
        };
        tmpI.onerror = res;
        tmpI.src = logoB64;
      });
    }
  } catch(e) {}

  function newPage(titre) {
    if (pageNum > 0) doc.addPage();
    pageNum++;
    // Header vert
    doc.setFillColor.apply(doc, GRN); doc.rect(0,0,PW,22,'F');
    if (logoB64) {
      try {
        // Logo capé à 13mm de haut pour tenir dans le header de 22mm
        var lW = Math.min(logoW, 24);
        var lH = Math.min(logoH, 10);
        var lY = (22 - lH) / 2;
        doc.setFillColor(255,255,255);
        doc.roundedRect(MAR-2, lY-2, lW+4, lH+4, 2, 2, 'F');
        doc.addImage(logoB64,'PNG',MAR,lY,lW,lH);
      } catch(e) {
        doc.setTextColor(255,255,255); doc.setFontSize(10); doc.setFont('helvetica','bold');
        doc.text('CME',MAR,12);
      }
    } else {
      doc.setTextColor(255,255,255); doc.setFontSize(10); doc.setFont('helvetica','bold');
      doc.text('Comprendre Mon Energie',MAR,12);
    }
    if (titre) {
      doc.setTextColor(255,255,255); doc.setFontSize(10); doc.setFont('helvetica','bold');
      doc.text(titre, PW-MAR, 13, {align:'right'});
    }
    // Footer (agrandi)
    doc.setFillColor(GRN[0],GRN[1],GRN[2]); doc.rect(0,PH-14,PW,14,'F');
    doc.setTextColor(255,255,255); doc.setFontSize(8.5); doc.setFont('helvetica','normal');
    doc.text('comprendre-mon-energie.fr  |  contact@comprendre-mon-energie.fr  |  61 rue de Lyon 75012 Paris', PW/2, PH-6, {align:'center'});
    doc.text('Page '+pageNum, PW-MAR, PH-6, {align:'right'});
    return 30; // Y de départ après header
  }

  function txt(str, x, y, opts) { doc.text(str||'', x, y, opts||{}); return y; }
  function sectTitle(label, y) {
    doc.setFillColor.apply(doc, LGT); doc.rect(MAR, y-5, CW, 9, 'F');
    doc.setDrawColor.apply(doc, GRN); doc.rect(MAR, y-5, 3, 9, 'F');
    doc.setTextColor.apply(doc, GRN); doc.setFontSize(10); doc.setFont('helvetica','bold');
    doc.text(label, MAR+6, y+1);
    return y + 8;
  }
  function row(lbl, val, y, bold) {
    doc.setTextColor(107,114,128); doc.setFontSize(8.5); doc.setFont('helvetica','normal');
    var lbl2 = doc.splitTextToSize(String(lbl||''), 68);
    doc.text(lbl2, MAR+4, y);
    doc.setTextColor(17,24,39); doc.setFontSize(8.5); doc.setFont('helvetica', bold?'bold':'normal');
    var val2 = doc.splitTextToSize(String(val||'-'), 88);
    doc.text(val2, MAR+76, y);
    var lines = Math.max(lbl2.length, val2.length);
    return y + lines * 5 + 1;
  }
  function bigKPI(label, val, unit, x, y, col) {
    var c = col||GRN;
    var bW=72, bH=30;
    doc.setFillColor(255,255,255);
    doc.setDrawColor(c[0],c[1],c[2]);
    doc.setLineWidth(0.8);
    doc.roundedRect(x, y, bW, bH, 3, 3, 'FD');
    var cx = x + bW/2;
    doc.setTextColor(c[0],c[1],c[2]);
    doc.setFontSize(15); doc.setFont('helvetica','bold');
    doc.text(String(val||''), cx, y+11, {align:'center', maxWidth:bW-8});
    doc.setTextColor(107,114,128);
    doc.setFontSize(8); doc.setFont('helvetica','normal');
    doc.text(String(unit||''), cx, y+18, {align:'center', maxWidth:bW-8});
    doc.setFontSize(8); doc.setFont('helvetica','bold');
    doc.setTextColor(17,24,39);
    doc.text(String(label||''), cx, y+26, {align:'center', maxWidth:bW-8});
    return y+bH+5;
  }

  // ════════════ PAGE 1 — COUVERTURE ════════════
  doc.setFillColor.apply(doc, GRN); doc.rect(0,0,PW,PH,'F');
  // Bande blanche centrale
  doc.setFillColor(255,255,255); doc.roundedRect(MAR, 40, CW, 168, 5, 5, 'F');
  // Logo sur fond vert
  if (logoB64) {
    try {
      var covLogoW = 30;
      var covLogoH = Math.min(14, covLogoW * logoH / logoW);
      var covLogoX = PW/2 - covLogoW/2;
      doc.setFillColor(255,255,255);
      doc.roundedRect(covLogoX-4, 4, covLogoW+8, covLogoH+8, 3, 3, 'F');
      doc.addImage(logoB64,'PNG',covLogoX,8,covLogoW,covLogoH);
    } catch(e) {}
  }
  doc.setTextColor(255,255,255); doc.setFontSize(22); doc.setFont('helvetica','bold');
  doc.text('Estimation Solaire', PW/2, 34, {align:'center'});
  // Contenu bande blanche
  doc.setTextColor.apply(doc, GRN); doc.setFontSize(14); doc.setFont('helvetica','bold');
  doc.text('Personnalisee', PW/2, 55, {align:'center'});
  doc.setDrawColor.apply(doc, GRN); doc.setLineWidth(0.5); doc.line(MAR+10,59,PW-MAR-10,59);
  if (S.adresse) {
    doc.setTextColor.apply(doc, DRK); doc.setFontSize(11); doc.setFont('helvetica','normal');
    var adrLines = doc.splitTextToSize(S.adresse, CW-20);
    doc.text(adrLines, PW/2, 67, {align:'center'});
  }
  doc.setTextColor.apply(doc, GRY); doc.setFontSize(9);
  doc.text('Document genere le '+today, PW/2, 80, {align:'center'});
  // 4 KPIs
  // KPI centrés : 4 boites 40mm avec espacement uniforme dans 180mm
  // KPI 2x2 - blocs plus etroits, centres
  var bX1=MAR+18, bX2=MAR+18+72+10;
  var bY1=98, bY2=bY1+35;
  bigKPI('Panneaux installes', String(R.nb)+' panneaux', '400 Wc chacun', bX1, bY1, GRN);
  bigKPI('Production annuelle', fmtNum(R.prod||0)+' kWh', 'par an', bX2, bY1, [37,99,235]);
  bigKPI('Budget net', fmtNum(netBudget||0)+' EUR', 'apres aides', bX1, bY2, [245,158,11]);
  bigKPI('Retour invest.', String(R.roi||'?')+' ans', 'amortissement', bX2, bY2, [239,68,68]);
  // Source production sous les 4 blocs
  doc.setTextColor(107,114,128); doc.setFontSize(7.5); doc.setFont('helvetica','normal');
  doc.text('Source production: '+(S.pvgis_irrad&&S.pvgis_irrad>0?'PVGIS - JRC Commission Europeenne':'Estimation departementale'), PW/2, bY2+40, {align:'center'});
  // Footer etendu couverture — inclut sources + contact (evite chevauchement KPI)
  doc.setFillColor(255,255,255); doc.rect(0,PH-34,PW,34,'F');
  doc.setDrawColor(GRN[0],GRN[1],GRN[2]); doc.setLineWidth(0.3);
  doc.line(MAR+10,PH-34,PW-MAR-10,PH-34);
  doc.setTextColor(107,114,128); doc.setFontSize(7.5);
  doc.text('Source production: '+(S.pvgis_irrad&&S.pvgis_irrad>0?'PVGIS - JRC Commission Europeenne':'Estimation departementale'), PW/2, PH-26, {align:'center'});
  if (S.linky_kwh&&S.linky_kwh>0) {
    doc.setTextColor(GRN[0],GRN[1],GRN[2]); doc.setFontSize(7.5); doc.setFont('helvetica','bold');
    doc.text('Donnees Linky Enedis integrees - Consommation reelle : '+fmtNum(S.linky_kwh||0)+' kWh/an', PW/2, PH-20, {align:'center'});
  }
  doc.setTextColor(GRN[0],GRN[1],GRN[2]); doc.setFontSize(8); doc.setFont('helvetica','normal');
  doc.text('www.comprendre-mon-energie.fr', PW/2, PH-12, {align:'center'});
  doc.setTextColor(107,114,128);
  doc.text('contact@comprendre-mon-energie.fr  -  61 rue de Lyon 75012 Paris', PW/2, PH-6, {align:'center'});
  pageNum = 1;

  // ════════════ PAGE 2 — INSTALLATION ════════════
  var y = newPage('Votre Installation');
  y = sectTitle('LOCALISATION & TOITURE', y);
  y = row('Adresse', S.adresse||'-', y);
  y = row('Irradiation', (R.irrad||'-')+' kWh/m\xb2/an', y);
  y = row('Source', S.pvgis_irrad&&S.pvgis_irrad>0?'PVGIS satellite (JRC)':'Estimation departementale', y);
  y = row('Surface habitable', (S.surface||'-')+' m\xb2', y);
  y = row('Orientation', (function(){var O={S:'Sud',SE:'Sud-Est',E:'Est',NE:'Nord-Est',N:'Nord',NO:'Nord-Ouest',O:'Ouest',SO:'Sud-Ouest'};return O[S.orientation]||S.orientation;})(), y);
  y = row('Pente du toit', (S.pente||30)+'\xb0', y);
  y = row('DPE', 'Classe '+(S.dpe||'D')+' - Besoin thermique : '+({A:35,B:70,C:120,D:190,E:280,F:390,G:550}[S.dpe]||190)+' kWh/m\xb2/an', y);
  y = row('Annee construction', String(S.annee_construction||2005), y);
  y += 4;
  y = sectTitle('INSTALLATION PHOTOVOLTAIQUE', y);
  y = row('Nombre de panneaux', R.nb+' panneaux de 400 Wc', y, true);
  y = row('Puissance totale installee', R.kwc+' kWc', y, true);
  y = row('Production annuelle estimee', (R.prod||0)+' kWh/an', y, true);
  y = row('Surface panneaux', Math.round(R.nb*1.73)+' m\xb2 approximativement', y);
  y = row('Technologie', 'Silicium cristallin monocristallin', y);
  y = row('Degradation annuelle', '0.5% (performance ratio 80%)', y);
  y = row('Montage', 'Integre en toiture / surimpose', y);
  y += 4;
  y = sectTitle('RENDEMENT ECONOMIQUE ANNUEL', y);
  y = row('Economies autoconsommation', fmtNum(R.eco||0)+' \u20ac/an', y, true);
  y = row('Revenus revente surplus', fmtNum(R.rev||0)+' \u20ac/an', y, true);
  y = row('Total economies + revenus', fmtNum((R.eco||0)+(R.rev||0))+' \u20ac/an', y, true);
  y = row('CO2 evite', (R.co2||0)+' kg/an equivalent', y);

  // ════════════ PAGE 3 — ANALYSE FINANCIÈRE ════════════
  y = newPage('Analyse Financiere');
  y = sectTitle('BUDGET INSTALLATION', y);
  y = row('Budget TTC initial', fmtNum(R.budget||0)+' \u20ac', y, true);
  y = row('  Inclut', 'Fourniture panneaux + onduleur + pose + raccordement', y);
  y += 4;
  y = sectTitle('AIDES & DEDUCTIONS APPLICABLES', y);
  y = row('Prime autoconsommation (EDF OA)', '-'+fmtNum(pri_g||0)+' \u20ac', y, true);
  y = row('  Versee par', 'EDF Obligation d\'Achat apres mise en service', y);
  if (tva_g > 0) {
    y = row('TVA reduite a 10%', '-'+fmtNum(tva_g||0)+' \u20ac', y, true);
    y = row('  Eligibilite', 'Logement >= 2 ans, installation <= 36 kWc', y);
  }
  var eco_ptz = aidesData.find(function(a){return a.id==='ecoPtz';})||{};
  if (eco_ptz.eligible) {
    y = row('Eco-PTZ (pret taux zero)', 'Jusqu a 50 000 \u20ac de pret', y, true);
    y = row('  Condition', 'Proprietaire - via votre banque - taux 0%', y);
  }
  var aid_local = aidesData.find(function(a){return a.id==='local';})||{};
  if (aid_local.montant > 0) {
    y = row('Aides regionales', '~'+fmtNum(aid_local.montant)+' EUR (estimation)', y, true);
    y = row('  Organisme', aid_local.nom||'Votre region - france-renov.gouv.fr', y);
  }
  y += 6;
  doc.setFillColor(220,252,231); doc.setDrawColor.apply(doc, GRN);
  doc.setLineWidth(0.5); doc.roundedRect(MAR, y-4, CW, 16, 3, 3, 'FD');
  doc.setTextColor.apply(doc, DRK); doc.setFontSize(12); doc.setFont('helvetica','bold');
  doc.text('BUDGET NET APRES AIDES : '+fmtNum(netBudget||0)+' \u20ac', PW/2, y+6, {align:'center'});
  y += 22;
  y = sectTitle('RETOUR SUR INVESTISSEMENT', y);
  var eco_total = (R.eco||0)+(R.rev||0);
  [{r:0.03,l:'+3%/an'},{r:0.05,l:'+5%/an'},{r:0.07,l:'+7%/an'}].forEach(function(s){
    var cum=0,yr=0;
    while(cum<(netBudget||0)&&yr<30){yr++;cum+=(eco_total*Math.pow(1+s.r,yr-1))*Math.pow(.995,yr-1);}
    var g25=0;for(var i=1;i<=25;i++)g25+=(eco_total*Math.pow(1+s.r,i-1))*Math.pow(.995,i-1);
    y = row('Scenario hausse electricite '+s.l, 'Rentable en '+(yr>0&&yr<30?yr+' ans':'>25 ans')+' | Gain 25 ans : '+fmtNum(Math.round(g25))+'\u20ac', y);
  });

  // ════════════ PAGE 4 — PROFIL ENERGETIQUE ════════════
  y = newPage('Profil Energetique');
  y = sectTitle('VOTRE LOGEMENT', y);
  y = row('Statut', S.statut==='proprio'?'Proprietaire':'Locataire', y);
  y = row('Habitants', String(S.habitants||2), y);
  y = row('Consommation estimee', (R.conso||0)+' kWh/an', y, S.linky_kwh&&S.linky_kwh>0);
  if (S.linky_kwh&&S.linky_kwh>0) {
    y = row('Consommation reelle (Linky)', fmtNum(S.linky_kwh)+' kWh/an', y, true);
    y = row('PDL Enedis', S.linky_pdl||'-', y);
    if (S.linky_kva) y = row('Puissance souscrite', S.linky_kva+' kVA', y);
    if (S.linky_tarif) y = row('Tarif', S.linky_tarif, y);
  }
  y += 4;
  y = sectTitle('VOS USAGES ENERGETIQUES', y);
  var CH={elec:'Electrique',gaz:'Gaz',pac:'Pompe a chaleur',fioul:'Fioul',bois:'Bois'};
  var EAU={elec:'Chauffe-eau electrique',gaz:'Chauffe-eau gaz',solaire:'Solaire thermique',pac:'Thermodynamique'};
  var CUI={elec:'Cuisine electrique',induction:'Induction',gaz:'Cuisine gaz',mixte:'Mixte'};
  y = row('Mode de chauffage', (CH[S.chauffage]||S.chauffage)+(S.chauffage==='pac'?' (COP '+(S.cop||3.2)+')':''), y);
  y = row('Eau chaude sanitaire', EAU[S.eau]||S.eau, y);
  y = row('Cuisson', CUI[S.cuisson]||S.cuisson, y);
  y = row('VMC', {'none':'Naturelle','simple':'Simple flux (+3 kWh/m\xb2)','double':'Double flux (+5 kWh/m\xb2)'}[S.vmc]||'-', y);
  y = row('Vehicule electrique', S.has_ve?'Oui - '+(S.km_ve||15000)+' km/an (+'+fmtNum(Math.round((S.km_ve||15000)*0.18))+' kWh/an)':'Non', y);
  y += 4;
  y = sectTitle('CONTEXTE REGIONAL', y);
  y = row('Irradiation satellite PVGIS', (R.irrad||'-')+' kWh/m\xb2/an', y);
  y = row('Taux autoconsommation estime', Math.min(90,Math.round(((R.eco||0)/Math.max(1,(R.eco||0)+(R.rev||0)))*100))+'%', y);
  y = row('CO2 evite sur 25 ans', fmtNum(Math.round((R.co2||0)*25/1000))+' tonnes CO2', y);
  y += 4;
  doc.setFillColor.apply(doc, LGT); doc.roundedRect(MAR, y-3, CW, 30, 3, 3, 'F');
  doc.setTextColor.apply(doc, GRY); doc.setFontSize(8); doc.setFont('helvetica','italic');
  var note='Les projections de ce document sont basees sur les donnees de votre simulation a la date du '+today+'. Les resultats reels peuvent varier selon l\'evolution des prix de l\'electricite, les conditions meteorologiques et l\'entretien de l\'installation. Ce document est fourni a titre informatif et ne constitue pas un contrat ou un devis.';
  var noteLines = doc.splitTextToSize(note, CW-8);
  doc.text(noteLines, MAR+4, y+4);

  // ════════════ PAGE 5 — MENTIONS LÉGALES ════════════
  y = newPage('Mentions Legales & Confidentialite');
  doc.setTextColor.apply(doc, DRK); doc.setFontSize(8); doc.setFont('helvetica','normal');
  var legalY = y;
  PDF_LEGAL.forEach(function(line) {
    if (legalY > PH-20) {
      // Nouvelle page si debordement
      legalY = newPage('Mentions Legales (suite)');
    }
    if (line.startsWith('POLITIQUE') || line.startsWith('MENTIONS') || line.startsWith('VOS DROITS')) {
      legalY = sectTitle(line, legalY);
    } else if (line === '') {
      legalY += 3;
    } else {
      doc.setTextColor.apply(doc, line.startsWith('-')?GRY:DRK);
      doc.setFont('helvetica', line.startsWith('  ')?'italic':'normal');
      var lines = doc.splitTextToSize(line, CW);
      doc.text(lines, MAR+4, legalY);
      legalY += lines.length * 4.5;
    }
  });

  // Telecharger le PDF directement via blob URL
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
}
function buildForm(root){
  // Hero
  var hero=mk('div','ss-hero');
  hero.innerHTML='<div class="hero-text"><h2 class="hero-title">☀️ Simulateur solaire photovoltaïque</h2><p class="hero-sub">Estimez votre installation personnalisée en 2 minutes — résultat immédiat et gratuit</p><div><span class="hbadge">✓ Sans engagement</span><span class="hbadge">✓ Devis inclus</span><span class="hbadge">✓ Certifié RGE</span></div></div>';
  ap(root,hero);

  var body=mk('div','ss-body'),left=mk('div','ss-left'),right=mk('div','ss-right');

  /* ── GAUCHE ── */
  // S1: Logement
  var s1=mk('div','sc');ap(s1,mkTit('loc','Votre logement'));
  ap(s1,mk('label',null,'Adresse'));
  var arow=mk('div','addr-row'),iw=mk('div','inp-wrap');
  var adI=mk('input','addr-inp');adI.type='text';adI.placeholder='Ex: 10 rue de la Paix, 75001 Paris...';adI.setAttribute('autocomplete','off');adI.setAttribute('spellcheck','false');adI.value=S.adresse||'';
  var drop=mk('div','ac-drop');ap(iw,adI);ap(iw,drop);
  var gpsB=mk('button','gps-btn');gpsB.type='button';gpsB.innerHTML='📍';gpsB.title='Ma position';
  ap(arow,iw);ap(arow,gpsB);ap(s1,arow);
  var adSt=mk('div','addr-status');ap(s1,adSt);
  var irrBdg=mk('div','info-grn');ap(s1,irrBdg);
  // Carte mobile
  var mapM=mk('div','map-box');mapM.id=UID+'-map-m';ap(s1,mapM);
  setupAddr(adI,drop,irrBdg,adSt);
  gpsB.addEventListener('click',function(){doGPS(adI,irrBdg,adSt);});

  // ── Linky — Connexion compteur Enedis ─────────────────────────────────────
  var linkyCard=mk('div','linky-card');
  var linkyTit=mk('div','linky-title');
  linkyTit.innerHTML='⚡️ Données réelles Linky <span style="font-size:11px;color:#16a34a;font-weight:400;margin-left:auto">Optionnel</span>';
  ap(linkyCard,linkyTit);
  ap(linkyCard,mk('div','linky-sub','Connectez votre compteur Enedis pour remplacer les estimations par votre consommation réelle des 12 derniers mois.'));
  var linkyBtn2=mk('button','linky-btn');linkyBtn2.type='button';
  linkyBtn2.innerHTML='🔗 Connecter mon Linky';
  var linkySt=mk('div','linky-status');
  var linkyDat=mk('div','linky-data');
  // Token stocké en mémoire (session)
  var enedisSession={token_key:null,pdl:null,kwh:null};

  linkyBtn2.addEventListener('click',function(){
    // Pas de blocage frontend — le backend valide les credentials
    // (ENEDIS_OK peut etre vide a cause du cache opcode, ce n'est pas bloquant)
    linkyBtn2.disabled=true;
    linkyBtn2.innerHTML='<span class="spin"></span><span style="margin-left:8px">Ouverture Enedis...</span>';
    // Étape 1 : récupérer l’URL OAuth
    var fd1=new FormData();fd1.append('action','cme_enedis_init');fd1.append('nonce',ENEDIS_NONCE);
    fetch(AJAX_URL,{method:'POST',body:fd1})
      .then(function(r){return r.json();})
      .then(function(d){
        if(!d.success){linkyBtn2.disabled=false;linkyBtn2.innerHTML='🔗 Connecter mon Linky';linkySt.textContent='❌ '+d.data.msg;linkySt.style.color='#dc2626';linkySt.style.display='block';return;}
        var state=d.data.state;
        // Étape 2 : ouvrir popup Enedis
        var popup=window.open(d.data.url,'enedis_auth','width=900,height=700,scrollbars=yes,resizable=yes');
        linkyBtn2.innerHTML='⏳ Autorisation en cours...';
        // Étape 3 : écouter le callback
        function msgHandler(e){
          if(e.origin!==window.location.origin)return;
          if(e.data.type==='enedis_code'&&e.data.state===state){
            window.removeEventListener('message',msgHandler);
            if(popup&&!popup.closed)popup.close();
            echangerCode(e.data.code,state);
          } else if(e.data.type==='enedis_error'){
            window.removeEventListener('message',msgHandler);
            linkyBtn2.disabled=false;linkyBtn2.innerHTML='🔗 Connecter mon Linky';
            linkySt.textContent='❌ Refusé : '+e.data.error;linkySt.style.color='#dc2626';linkySt.style.display='block';
          }
        }
        window.addEventListener('message',msgHandler);
        // Détection fermeture popup sans autorisation
        var checkClose=setInterval(function(){
          if(popup&&popup.closed){clearInterval(checkClose);window.removeEventListener('message',msgHandler);linkyBtn2.disabled=false;linkyBtn2.innerHTML='🔗 Connecter mon Linky';}
        },800);
      })
      .catch(function(){linkyBtn2.disabled=false;linkyBtn2.innerHTML='🔗 Connecter mon Linky';linkySt.textContent='❌ Erreur réseau';linkySt.style.color='#dc2626';linkySt.style.display='block';});
  });

  function echangerCode(code,state){
    linkyBtn2.innerHTML='⏳ Récupération des données...';
    // Étape 4 : échanger le code contre un token
    var fd2=new FormData();fd2.append('action','cme_enedis_token');fd2.append('nonce',ENEDIS_NONCE);fd2.append('code',code);fd2.append('state',state);
    fetch(AJAX_URL,{method:'POST',body:fd2})
      .then(function(r){return r.json();})
      .then(function(d){
        if(!d.success){linkyBtn2.disabled=false;linkyBtn2.innerHTML='🔗 Connecter mon Linky';linkySt.textContent='❌ Token: '+d.data.msg;linkySt.style.color='#dc2626';linkySt.style.display='block';return;}
        enedisSession.token_key=d.data.token_key;
        enedisSession.pdl=d.data.pdl;
        // Étape 5 : récupérer la consommation
        var fd3=new FormData();fd3.append('action','cme_enedis_data');fd3.append('nonce',ENEDIS_NONCE);fd3.append('token_key',d.data.token_key);fd3.append('pdl',d.data.pdl);
        fetch(AJAX_URL,{method:'POST',body:fd3})
          .then(function(r){return r.json();})
          .then(function(dd){
            linkyBtn2.disabled=false;
            if(!dd.success){linkyBtn2.innerHTML='🔗 Connecter mon Linky';linkySt.textContent='❌ Données: '+dd.data.msg;linkySt.style.color='#dc2626';linkySt.style.display='block';return;}
            // ✔ Données premium Linky reçues
            S.linky_kwh=dd.data.annual_kwh||0;
            S.linky_pdl=dd.data.pdl;
            S.linky_kva=dd.data.puissance_kva||9;
            S.linky_tarif=dd.data.tarif||'Base';
            S.linky_profile=dd.data.load_profile||null;
            linkyCard.className='linky-card connected';
            linkyBtn2.innerHTML='✔ Linky connecté';linkyBtn2.style.background='#15803d';
            // Affichage résumé premium
            linkySt.innerHTML='✔ <strong>'+S.linky_kwh.toLocaleString('fr-FR')+'</strong> kWh/an réels';
            linkySt.style.color='#16a34a';linkySt.style.display='block';
            var extras='PDL : '+S.linky_pdl;
            if(S.linky_kva)extras+=' . '+S.linky_kva+' kVA';
            if(S.linky_tarif)extras+=' . Tarif '+S.linky_tarif;
            if(dd.data.has_load_curve)extras+=' . Courbe de charge disponible';
            linkyDat.textContent=extras;linkyDat.style.display='block';
            // PDL fige - confirme le bon compte
            var pdlEl=$g('linky-pdl');
            if(pdlEl&&S.linky_pdl){pdlEl.innerHTML='🔒 PDL : <strong>'+S.linky_pdl+'</strong>';pdlEl.style.display='flex';}
            debouncedPVGIS();updatePrev();
          });
      });
  }
  var pdlBox=mk('div');pdlBox.id=UID+'-linky-pdl';
  pdlBox.style.cssText='display:none;margin-top:10px;padding:10px 14px;background:#f9fafb;border:1.5px solid #e5e7eb;border-radius:8px;align-items:center;gap:8px;font-size:13px;font-family:monospace;font-weight:700;color:#111827';
  ap(linkyCard,linkyBtn2);ap(linkyCard,linkySt);ap(linkyCard,linkyDat);ap(linkyCard,pdlBox);ap(s1,linkyCard);

  // Statut
  var stW=mk('div');stW.style.marginTop='14px';ap(stW,mk('label',null,'Vous êtes'));
  var tog=mk('div','tog');
  var bP=mk('button','tbtn'+(S.statut==='proprio'?' on':''),'🏠 Propriétaire');
  var bL=mk('button','tbtn'+(S.statut==='locataire'?' on':''),'🔑 Locataire');
  bP.addEventListener('click',function(){S.statut='proprio';bP.className='tbtn on';bL.className='tbtn';updatePrev();});
  bL.addEventListener('click',function(){S.statut='locataire';bL.className='tbtn on';bP.className='tbtn';updatePrev();});
  ap(tog,bP);ap(tog,bL);ap(stW,tog);ap(s1,stW);

  // Habitants + Surface
  var gH=mk('div','g2');gH.style.marginTop='14px';
  var hW=mk('div');ap(hW,mk('label',null,'Habitants'));
  var step=mk('div','stepper');
  var sm=mk('button','step-btn','−');sm.type='button';
  var sv=mk('div','step-val',S.habitants>=5?'5+':String(S.habitants));
  var sp2=mk('button','step-btn','+');sp2.type='button';
  sm.addEventListener('click',function(){if(S.habitants>1){S.habitants--;sv.textContent=S.habitants>=5?'5+':String(S.habitants);updatePrev();}});
  sp2.addEventListener('click',function(){if(S.habitants<6){S.habitants++;sv.textContent=S.habitants>=5?'5+':String(S.habitants);updatePrev();}});
  ap(step,sm);ap(step,sv);ap(step,sp2);ap(hW,step);ap(gH,hW);
  var sfW=mk('div');ap(sfW,mk('label',null,'Surface habitable (m²)'));
  var sfI=document.createElement('input');sfI.type='number';sfI.value=S.surface;sfI.min=20;sfI.max=500;sfI.step=5;
  sfI.addEventListener('input',function(){S.surface=parseInt(sfI.value)||100;S.pvgis_prod=null;S.pvgis_irrad=null;updatePrev();});
  ap(sfW,sfI);ap(gH,sfW);ap(s1,gH);
  var acW=mk('div');acW.style.marginTop='14px';
  ap(acW,mk('label',null,'Année de construction'));
  var acS=document.createElement('select');
  [['2025','Neuf / moins de 2 ans'],['2018','2018 — 2024'],['2010','2010 — 2017'],
   ['2000','2000 — 2009'],['1990','1990 — 1999'],['1975','1975 — 1989'],['1960','Avant 1975']
  ].forEach(function(o){var op=document.createElement('option');op.value=o[0];op.textContent=o[1];if(parseInt(o[0])===S.annee_construction)op.selected=true;acS.appendChild(op);});
  acS.onchange=function(){
    S.annee_construction=parseInt(acS.value)||2005;
    // Toujours re-estimer le DPE depuis l'année de construction
    S.dpe=estimDPE(S.annee_construction);
    S.dpe_confirmed=false;
    var dRow=$g('dpe-row'),dNote=$g('dpe-note'),dInfo=$g('dpe-info');
    if(dRow){dRow.querySelectorAll('.dpe-btn').forEach(function(x){x.className='dpe-btn';});dRow.querySelectorAll('.dpe-btn').forEach(function(x){if(x.textContent.trim()===S.dpe)x.className='dpe-btn on';});}
    if(dInfo)dInfo.textContent='Classe '+S.dpe+' . Besoin thermique : '+(DPE_THERM[S.dpe]||190)+' kWh/m²/an';
    if(dNote){dNote.textContent='📊 Classe '+S.dpe+' estimée depuis votre logement de '+S.annee_construction+' . Cliquez pour modifier';dNote.style.background='#eff6ff';dNote.style.borderColor='#bfdbfe';}
    updatePrev();
  };
  ap(acW,acS);
  ap(acW,mk('div','hint','Détermine votre éligibilité TVA 10% et Éco-PTZ'));
  ap(s1,acW);

  // DPE — Classe énergétique (auto-estimation + confirmation)
  var dpeW=mk('div');dpeW.style.marginTop='14px';
  ap(dpeW,mk('label',null,'Classe énergétique DPE'));
  // Auto-estimer si pas encore confirmé par l'utilisateur
  if(!S.dpe_confirmed)S.dpe=estimDPE(S.annee_construction||2005);
  var dpeRow=mk('div','dpe-row');dpeRow.id=UID+'-dpe-row';
  var dpeInfo=mk('div','dpe-info');dpeInfo.id=UID+'-dpe-info';
  function majDpeInfo(cls){
    dpeInfo.textContent='Classe '+cls+' . Besoin thermique : '+(DPE_THERM[cls]||190)+' kWh/m²/an';
  }
  majDpeInfo(S.dpe);
  var dpeNote=mk('div');dpeNote.id=UID+'-dpe-note';
  dpeNote.style.cssText='margin-top:8px;font-size:12px;padding:8px 10px;border-radius:8px;border:1px solid #bbf7d0;background:#f0fdf4;color:#065f46;line-height:1.4';
  function majDpeNote(){
    if(S.dpe_confirmed){dpeNote.textContent='✓ Classe '+S.dpe+' sélectionnée — '+(DPE_LBL[S.dpe]||'');dpeNote.style.background='#f0fdf4';dpeNote.style.borderColor='#86efac';}
    else{dpeNote.textContent='📊 Classe '+S.dpe+' estimée depuis votre logement de '+(S.annee_construction||2005)+' . Cliquez sur une classe si vous connaissez votre DPE réel';dpeNote.style.background='#eff6ff';dpeNote.style.borderColor='#bfdbfe';}
  }
  majDpeNote();
  ['A','B','C','D','E','F','G'].forEach(function(cls){
    var b=mk('button','dpe-btn'+(S.dpe===cls?' on':''),cls);
    b.type='button';b.style.background=DPE_COL[cls];b.style.color=cls==='D'?'#333':'#fff';
    b.addEventListener('click',function(){
      S.dpe=cls;S.dpe_confirmed=true;
      dpeRow.querySelectorAll('.dpe-btn').forEach(function(x){x.className='dpe-btn';});
      b.className='dpe-btn on';
      majDpeInfo(cls);majDpeNote();updatePrev();debouncedPVGIS();
    });
    ap(dpeRow,b);
  });
  ap(dpeW,dpeRow);ap(dpeW,dpeInfo);ap(dpeW,dpeNote);
  ap(s1,dpeW);ap(left,s1);

  // S2: Toiture
  var s2=mk('div','sc');ap(s2,mkTit('home','Votre toiture'));
  ap(s2,mk('label',null,'Orientation'));
  var cmp=mk('div','compass');
  [['NO','N','NE'],['O',null,'E'],['SO','S','SE']].forEach(function(row){
    row.forEach(function(d){
      if(!d){ap(cmp,mk('div','ctr','☀️'));return;}
      var o=ORI[d],b=mk('button','dbtn'+(S.orientation===d?' on':''));b.type='button';b.setAttribute('data-d',d);
      ap(b,mk('span',null,o.l));ap(b,mk('span','dpct',Math.round(o.c*100)+'%'));
      b.addEventListener('click',function(){cmp.querySelectorAll('.dbtn').forEach(function(x){x.className='dbtn';});b.className='dbtn on';S.orientation=d;updatePrev();debouncedPVGIS();});
      ap(cmp,b);
    });
  });
  ap(s2,cmp);ap(s2,mk('div','hint','☀️ Plein Sud = rendement optimal . Est/Ouest = bon rendement'));
  var pW=mk('div');pW.style.marginTop='14px';ap(pW,mk('label',null,'Pente du toit'));
  var pv=mk('div','slval',S.pente+'°');ap(pW,pv);
  var psl=document.createElement('input');psl.type='range';psl.min=0;psl.max=90;psl.step=5;psl.value=S.pente;
  var pinf=mk('div','sinfo','Rendement : '+Math.round(icf(S.pente)*100)+'%'+(S.pente>=25&&S.pente<=40?' ✓ Optimal':''));
  psl.addEventListener('input',function(){S.pente=parseInt(psl.value);pv.textContent=S.pente+'°';var c=icf(S.pente);pinf.textContent='Rendement : '+Math.round(c*100)+'%'+(S.pente>=25&&S.pente<=40?' ✓ Optimal':'');updatePrev();debouncedPVGIS();});
  ap(pW,psl);var pm=mk('div','smarks');['0°','15°','30° ✓','45°','60°','90°'].forEach(function(m){ap(pm,mk('span',null,m));});ap(pW,pm);ap(pW,pinf);ap(s2,pW);ap(left,s2);

  // S3: Usages
  var s3=mk('div','sc');ap(s3,mkTit('bolt','Vos usages énergétiques'));
  ap(s3,mk('div','hint','⚡ Ces données impactent directement votre consommation estimée et le calcul de retour sur investissement.'));
  function mkOpts(lbl,items,key,multi){
    var w=mk('div');w.style.marginTop='14px';if(lbl)ap(w,mk('label',null,lbl));
    var opts=mk('div','opts');
    items.forEach(function(e){
      var on=multi?S[key].indexOf(e[0])>-1:S[key]===e[0];
      var b=mk('button','obtn'+(on?' on':''),e[1]);b.type='button';
      b.addEventListener('click',function(){
        if(multi){var i=S[key].indexOf(e[0]);if(i>-1)S[key].splice(i,1);else S[key].push(e[0]);b.className='obtn'+(S[key].indexOf(e[0])>-1?' on':'');}
        else{S[key]=e[0];opts.querySelectorAll('.obtn').forEach(function(x){x.className='obtn';});b.className='obtn on';}
        updatePrev();
      });ap(opts,b);
    });ap(w,opts);return w;
  }
  ap(s3,mkOpts('Vos énergies',[['elec','⚡ Électricité'],['gaz','🔥 Gaz'],['fioul','🛢 Fioul'],['bois','🪵 Bois']],'energies',true));
  // Chauffage avec COP conditionnel
  var chW=mk('div');chW.style.marginTop='14px';ap(chW,mk('label',null,'Mode de chauffage'));
  var chOpts2=mk('div','opts');
  var copWrap=mk('div','cop-wrap');
  copWrap.style.display=S.chauffage==='pac'?'block':'none';
  ap(copWrap,mk('label',null,'COP de votre pompe à chaleur'));
  var copSel=document.createElement('select');
  [[2.5,'2.5 — Air/Air (ancienne)'],[3.0,'3.0 — Air/Eau standard'],[3.2,'3.2 — Air/Eau récent'],[3.5,'3.5 — Air/Eau haute efficacité'],[4.0,'4.0 — Géothermique'],[4.5,'4.5 — Géothermique haute perf.']].forEach(function(o){
    var op=document.createElement('option');op.value=o[0];op.textContent=o[1];
    if(parseFloat(o[0])===(S.cop||3.2))op.selected=true;copSel.appendChild(op);
  });
  copSel.onchange=function(){S.cop=parseFloat(copSel.value)||3.2;updatePrev();};
  ap(copWrap,copSel);
  ap(copWrap,mk('div','hint','Air/Air : 2.5–3.5 . Air/Eau : 3.0–4.0 . Géothermique : 4.0–5.0'));
  [['elec','⚡ Électrique'],['gaz','🔥 Gaz'],['pac','🌡️ Pompe à chaleur'],['fioul','🛢 Fioul'],['bois','🪵 Bois']].forEach(function(e){
    var b=mk('button','obtn'+(S.chauffage===e[0]?' on':''),e[1]);b.type='button';
    b.addEventListener('click',function(){
      S.chauffage=e[0];chOpts2.querySelectorAll('.obtn').forEach(function(x){x.className='obtn';});b.className='obtn on';
      copWrap.style.display=e[0]==='pac'?'block':'none';updatePrev();
    });ap(chOpts2,b);
  });
  ap(chW,chOpts2);ap(s3,chW);ap(s3,copWrap);
  ap(s3,mkOpts('Eau chaude',[['elec','⚡ Chauffe-eau'],['gaz','🔥 Gaz'],['solaire','☀️ Solaire'],['pac','🌡️ Thermo.']],'eau',false));
  ap(s3,mkOpts('Cuisson',[['elec','⚡ Électrique'],['induction','🔵 Induction'],['gaz','🔥 Gaz'],['mixte','↔️ Mixte']],'cuisson',false));

  // Véhicule électrique
  var veW=mk('div');veW.style.marginTop='14px';
  ap(veW,mk('label',null,'🚗 Véhicule électrique (rechargé à domicile)'));
  var veTog=mk('div','tog');
  var veNo=mk('button','tbtn'+(S.has_ve?'':' on'),'Non');
  var veYes=mk('button','tbtn'+(S.has_ve?' on':''),'🔋 Oui, je recharge chez moi');
  var veKmW=mk('div');veKmW.style.cssText='margin-top:10px;display:'+(S.has_ve?'block':'none');
  ap(veKmW,mk('label',null,'Kilomètres parcourus par an'));
  var veKmI=document.createElement('input');veKmI.type='number';veKmI.value=S.km_ve||15000;veKmI.min=1000;veKmI.max=80000;veKmI.step=1000;
  veKmI.addEventListener('input',function(){S.km_ve=parseInt(veKmI.value)||15000;updatePrev();});
  ap(veKmW,veKmI);
  ap(veKmW,mk('div','hint','~ 18 kWh/100 km . 15 000 km/an > +2 700 kWh/an'));
  veNo.addEventListener('click',function(){S.has_ve=false;veNo.className='tbtn on';veYes.className='tbtn';veKmW.style.display='none';updatePrev();});
  veYes.addEventListener('click',function(){S.has_ve=true;veYes.className='tbtn on';veNo.className='tbtn';veKmW.style.display='block';updatePrev();});
  ap(veTog,veNo);ap(veTog,veYes);ap(veW,veTog);ap(veW,veKmW);ap(s3,veW);

  // VMC
  var vmcW=mk('div');vmcW.style.marginTop='14px';
  ap(vmcW,mk('label',null,'💨 Ventilation (VMC)'));
  ap(vmcW,mkOpts(null,[['none','Aucune / naturelle'],['simple','Simple flux'],['double','Double flux']],'vmc',false));
  ap(vmcW,mk('div','hint','Simple flux : +3 kWh/m² . Double flux : +5 kWh/m² (mais économise sur le chauffage)'));
  ap(s3,vmcW);

  ap(left,s3);

  // CTA
  var ctaBtn=mk('button','cta-btn');ctaBtn.innerHTML='<span>Voir mon estimation ></span>';
  ctaBtn.addEventListener('click',function(){
    // Adresse obligatoire : code postal ou coordonnées GPS requis
    if(!S.cp||S.cp.length<5){
      adSt.textContent='⚠️ Sélectionnez votre adresse dans la liste ou utilisez la géolocalisation 📍';
      adSt.style.display='block';
      adSt.style.color='#dc2626';
      adSt.style.fontWeight='500';
      adI.style.borderColor='#dc2626';
      adI.focus();
      document.getElementById(UID).scrollIntoView({behavior:'smooth',block:'start'});
      return;
    }
    adSt.style.display='none';adI.style.borderColor='';
    ctaBtn.innerHTML='<span class="spin"></span><span style="margin-left:8px">Calcul...</span>';
    ctaBtn.disabled=true;
    setTimeout(function(){showResults();ctaBtn.innerHTML='<span>Voir mon estimation ></span>';ctaBtn.disabled=false;},900);
  });
  ap(left,ctaBtn);

  /* ── DROITE ── */
  // Carte desktop
  var mapD=mk('div','map-box');mapD.id=UID+'-map-d';ap(right,mapD);
  // Aperçu
  var prev=mk('div','ss-prev');ap(prev,mk('div','prev-title','⚡ Aperçu en direct'));
  var pg=mk('div','prev-grid');
  function mkPV(id,lbl){var c=mk('div','prev-card');var v=mk('div','prev-val','—');v.id=UID+'-p-'+id;ap(c,v);ap(c,mk('div','prev-lbl',lbl));ap(pg,c);}
  mkPV('nb','Panneaux');mkPV('kwc','Puissance');mkPV('eco','Économies/an');mkPV('roi','Retour invest.');
  var pvSt=mk('div');pvSt.id=UID+'-pvgis-st';pvSt.style.cssText='font-size:11px;margin-top:8px;min-height:14px;font-weight:500;padding:0 2px';ap(prev,pvSt);
  ap(prev,pg);ap(right,prev);
  // Récap
  var recap=mk('div','recap');ap(recap,mk('div','recap-title','📋 Récapitulatif'));
  [['adr','📍 Adresse'],['sf','📏 Surface'],['hab','👥 Habitants'],['annee','🏗️ Construction'],['dpe','🏷️ DPE'],['ori','🧭 Orientation'],['pente','🔺 Pente toit'],['ch','🔥 Chauffage'],['vmc','💨 VMC'],['ve','🚗 Véhicule'],['linky','⚡ Linky']].forEach(function(r){var row=mk('div','ri');ap(row,mk('div','ri-lbl',r[1]));var v=mk('div','ri-val ri-empty','—');v.id=UID+'-r-'+r[0];ap(row,v);ap(recap,row);});
  ap(right,recap);

  ap(body,left);ap(body,right);ap(root,body);

  // Init carte France par défaut
  setTimeout(function(){showFrance([$g('map-d'),$g('map-m')]);},200);
  updatePrev();
}

/* ── Résultats ─────────────────────────────────────────────────── */
var _R=null;
function showResults(){
  var el=document.getElementById(UID+'-res');if(!el)return;
  _R=calcAll();el.innerHTML='';el.className='results show';
  var hero=mk('div','res-hero');hero.innerHTML=makeSVG();
  var titleEl=mk('div','res-title');titleEl.innerHTML='Votre estimation solaire personnalisée'+linky_badge;ap(hero,titleEl);
  var dept=getDept(S.cp);var linky_badge=S.linky_kwh&&S.linky_kwh>0?'<span style="background:#16a34a;color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;margin-left:8px">⚡ Linky</span>':'';
  var linky_src=S.linky_kwh&&S.linky_kwh>0?'⚡ Données Linky Enedis . '+S.linky_kwh.toLocaleString('fr-FR')+' kWh/an réels':'';
  var pvgis_src=S.pvgis_irrad&&S.pvgis_irrad>0?'📡 PVGIS . '+_R.irrad+' kWh/m²':'Estimation par département';
  var src_txt=linky_src?(linky_src+' . '+pvgis_src):(S.pvgis_irrad&&S.pvgis_irrad>0?'Production PVGIS satellite : '+_R.prod.toLocaleString('fr-FR')+' kWh/an . Irradiation : '+_R.irrad+' kWh/m²':'Ensoleillement estimé : '+(dept&&IRRAD[dept]?IRRAD[dept]:_R.irrad)+' kWh/m²/an');ap(hero,mk('div','res-sub',src_txt));
  var ul=mk('ul','res-list');
  [{ico:'🔆',l:'Panneaux recommandés',v:_R.nb+' panneaux de 400 Wc'},
   {ico:'📐',l:'Surface toit utilisée',v:_R.surf_toit+' m²'},
   {ico:'⚡',l:'Production annuelle',v:_R.prod.toLocaleString('fr-FR')+' kWh/an'},
   {ico:'💶',l:'Économies sur votre facture',v:_R.eco.toLocaleString('fr-FR')+'€/an (−'+_R.reduc+'%)'},
   {ico:'📈',l:'Gain revente surplus',v:_R.rev.toLocaleString('fr-FR')+'€/an'},
  ].forEach(function(it){var li=mk('li');ap(li,mk('div','rli',it.ico));var inf=mk('div');ap(inf,mk('div','rll',it.l));ap(inf,mk('div','rlv',it.v));ap(li,inf);ap(ul,li);});
  ap(hero,ul);ap(el,hero);
  var cards=mk('div','res-cards');
  [{cls:'sol',ico:'⚡',v:_R.kwc+' kWc',l:'Puissance'},{cls:'',ico:'💰',v:_R.budget.toLocaleString('fr-FR')+'€',l:'Budget TTC'},{cls:'eco',ico:'🎁',v:_R.prime.toLocaleString('fr-FR')+'€',l:'Prime autoconso.'},{cls:'',ico:'⏰',v:_R.roi+' ans',l:'ROI'},{cls:'eco',ico:'🌿',v:_R.co2.toLocaleString('fr-FR')+' kg',l:'CO2 évité/an'},{cls:'eco',ico:'🔋',v:_R.conso.toLocaleString('fr-FR')+' kWh',l:'Votre conso.'},
  ].forEach(function(it){var c=mk('div','rcard '+it.cls);ap(c,mk('div','rcard-ico',it.ico));ap(c,mk('div','rcard-val',it.v));ap(c,mk('div','rcard-lbl',it.l));ap(cards,c);});
  ap(el,cards);
  // CTA devis > ouvre modal
  // Section Aides
  var aidesData=calcAides(_R);
  var aSc=mk('div','sc');aSc.style.marginBottom='12px';
  ap(aSc,mkTit('bolt','Aides & Financement disponibles'));
  aidesData.forEach(function(a){
    var row=mk('div','aide-row');
    var ico=mk('div','aide-ico');
    ico.textContent=a.eligible===null?'ℹ':a.eligible?'✓':'✗';
    ico.style.background=a.eligible===null?'#f3f4f6':a.eligible?'#d1fae5':'#f3f4f6';
    ico.style.color=a.eligible===null?'#6b7280':a.eligible?'#065f46':'#9ca3af';
    var info=mk('div');info.style.cssText='flex:1;min-width:0';
    ap(info,mk('div','aide-nom',a.nom));
    ap(info,mk('div','aide-det',a.detail));
    var condEl=mk('div','aide-cond'+(a.eligible?'':' no'),a.cond);ap(info,condEl);
    var amt=mk('div','aide-amt');
    if(a.eligible&&a.montant>0){amt.textContent=a.type==='pret'?'Prêt : '+a.montant.toLocaleString('fr-FR')+'€':'−'+a.montant.toLocaleString('fr-FR')+'€';amt.style.color=a.type==='pret'?'#1d4ed8':'#16a34a';}
    else if(a.eligible===null){amt.textContent=a.montant>0?'~'+fmtNum(a.montant)+'€':'Variable';amt.style.color='#6b7280';}
    else{amt.textContent='—';amt.style.color='#9ca3af';}
    ap(row,ico);ap(row,info);ap(row,amt);ap(aSc,row);
  });
  var tva_a=aidesData.find(function(a){return a.id==='tva';});
  var pri_a=aidesData.find(function(a){return a.id==='prime';});
  var tva_g=tva_a&&tva_a.eligible?tva_a.montant:0;
  var pri_g=pri_a?pri_a.montant:0;
  var net=_R.budget-pri_g-tva_g;
  var bS=mk('div','budget-summ');
  [['Budget TTC initial',_R.budget.toLocaleString('fr-FR')+'€','#6b7280'],
   pri_g>0?['Prime autoconsommation','−'+pri_g.toLocaleString('fr-FR')+'€','#16a34a']:null,
   tva_g>0?['Économie TVA 10%','−'+tva_g.toLocaleString('fr-FR')+'€','#16a34a']:null,
  ].filter(Boolean).forEach(function(r){
    var row=mk('div','bs-row');
    var l=mk('span',null,r[0]);l.style.color=r[2];
    var v=mk('span',null,r[1]);v.style.fontWeight='600';
    ap(row,l);ap(row,v);ap(bS,row);
  });
  var nR=mk('div','bs-net');
  var nl=mk('div',null,'Budget net après aides');nl.style.cssText='font-size:13px;font-weight:700;color:#16a34a';
  var nv=mk('div',null,net.toLocaleString('fr-FR')+'€');nv.style.cssText='font-size:19px;font-weight:800;color:#16a34a';
  ap(nR,nl);ap(nR,nv);ap(bS,nR);ap(aSc,bS);ap(el,aSc);

  // ── Graphique ROI 25 ans ─────────────────────────────────────────────────
  var roiSc=mk('div','sc');roiSc.style.marginBottom='12px';
  ap(roiSc,mkTit('chart','Retour sur investissement — Projections 25 ans'));

  // Chart SVG épuré
  var roiD=mk('div');roiD.innerHTML=buildROIChart(_R,net);ap(roiSc,roiD);

  // Légende horizontale (HTML, propre)
  var roiLeg=mk('div');roiLeg.style.cssText='display:flex;gap:18px;margin:8px 0 14px;flex-wrap:wrap;align-items:center';
  [{l:'Hausse +3%/an',c:'#3b82f6'},{l:'Hausse +5%/an',c:'#16a34a'},{l:'Hausse +7%/an',c:'#f59e0b'}].forEach(function(s){
    var it=mk('div');it.style.cssText='display:flex;align-items:center;gap:6px;font-size:12px;color:#374151;font-weight:600';
    it.innerHTML='<span style="width:22px;height:3px;background:'+s.c+';display:inline-block;border-radius:2px"></span>'+s.l;ap(roiLeg,it);});
  if(net>0){var rl=mk('div');rl.style.cssText='display:flex;align-items:center;gap:6px;font-size:12px;color:#dc2626;font-weight:600';
    rl.innerHTML='<span style="width:22px;height:0;border-top:2px dashed #dc2626;display:inline-block"></span>Coût net';ap(roiLeg,rl);}
  ap(roiSc,roiLeg);

  // 3 cartes détail par scénario
  var roiCards=mk('div');roiCards.style.cssText='display:grid;grid-template-columns:repeat(3,1fr);gap:10px';
  [{rate:.03,label:'+3% / an',col:'#3b82f6'},{rate:.05,label:'+5% / an',col:'#16a34a'},{rate:.07,label:'+7% / an',col:'#f59e0b'}].forEach(function(s){
    var eco2=_R.eco||0,rev2=_R.rev||0,cum=0,yr=0;
    while(cum<net&&yr<30){yr++;cum+=(eco2*Math.pow(1+s.rate,yr-1)+rev2)*Math.pow(.995,yr-1);}
    var g25=0;for(var y=1;y<=25;y++)g25+=(eco2*Math.pow(1+s.rate,y-1)+rev2)*Math.pow(.995,y-1);g25=Math.round(g25);
    var card=mk('div');card.style.cssText='background:#fff;border-radius:12px;padding:14px 10px;border:1.5px solid '+s.col+'40;text-align:center';
    var hd=mk('div',null,'Hausse élec. '+s.label);hd.style.cssText='font-size:11px;font-weight:700;color:'+s.col+';text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px';
    var rv=mk('div',null,yr>0&&yr<30?yr+' ans':'>25 ans');rv.style.cssText='font-size:26px;font-weight:800;color:#111827;line-height:1';
    var rl2=mk('div',null,'pour rentabiliser');rl2.style.cssText='font-size:11px;color:#9ca3af;margin:2px 0 10px';
    var sep=mk('div');sep.style.cssText='height:1px;background:#f3f4f6;margin:8px 0';
    var gv=mk('div',null,g25.toLocaleString('fr-FR')+'€');gv.style.cssText='font-size:15px;font-weight:700;color:'+s.col;
    var gl=mk('div',null,'gain total en 25 ans');gl.style.cssText='font-size:11px;color:#9ca3af';
    ap(card,hd);ap(card,rv);ap(card,rl2);ap(card,sep);ap(card,gv);ap(card,gl);ap(roiCards,card);
  });
  ap(roiSc,roiCards);ap(el,roiSc);

  var cta2

  // Bouton PDF
  var pdfBtn=mk('button','pdf-btn');pdfBtn.type='button';
  pdfBtn.innerHTML='📄 Télécharger mon estimation PDF';
  pdfBtn.addEventListener('click',function(){
    pdfBtn.innerHTML='⏳ Génération du PDF en cours...';pdfBtn.disabled=true;
    genererPDF(S, _R, aidesData, net).then(function(){
      pdfBtn.innerHTML='✅ PDF téléchargé ! 📄';
      setTimeout(function(){pdfBtn.innerHTML='📄 Télécharger mon estimation PDF';pdfBtn.disabled=false;},3000);
    }).catch(function(err){
      console.error('[CME PDF] Erreur:', err.message||err);
      pdfBtn.innerHTML='❌ Erreur PDF — F12 console pour détail';
      pdfBtn.disabled=false;
      setTimeout(function(){pdfBtn.innerHTML='📄 Télécharger mon estimation PDF';},4000);
    });
  });
  ap(el,pdfBtn);

  var cta2=mk('div','cta2');ap(cta2,mk('h3',null,'🌞 Obtenez votre devis gratuit'));
  ap(cta2,mk('p',null,'Un installateur certifié RGE analyse votre simulation et vous répond sous 48h — sans engagement'));
  var cb=mk('button','cta2-btn','Demander un devis gratuit >');cb.addEventListener('click',openModal);ap(cta2,cb);ap(el,cta2);
  ap(el,mk('div','fnote','* Estimations non contractuelles — performance ratio 80%, autoconsommation 75%, surplus 0,1301€/kWh, prime arrêté S1 2026.'));
  var nr=mk('button','new-sim','🔄 Nouvelle simulation');nr.addEventListener('click',function(){el.innerHTML='';el.className='results';window.scrollTo({top:document.getElementById(UID).offsetTop-10,behavior:'smooth'});});ap(el,nr);
  el.scrollIntoView({behavior:'smooth',block:'start'});
}

/* ── Modal devis ───────────────────────────────────────────────── */
function buildModal(root){
  var ov=mk('div','modal-ov');ov.id=UID+'-modal';
  var box=mk('div','modal-box');
  // Header
  var head=mk('div','modal-head');head.innerHTML='<h3>🌞 Demander un devis gratuit</h3><p>Remplissez vos coordonnées — réponse sous 48h</p>';
  var cls=mk('button','modal-close','×');cls.addEventListener('click',closeModal);ap(head,cls);ap(box,head);
  // Résumé simulation
  var summ=mk('div','modal-summ');ap(summ,mk('div','ms-label','Votre simulation'));
  var msg=mk('div','ms-grid');
  [{id:'nb',l:'Panneaux'},{id:'eco',l:'Économies/an'},{id:'budget',l:'Budget estimé'},{id:'roi',l:'Retour invest.'}].forEach(function(it){
    var c=mk('div','ms-card');ap(c,mk('span',null,it.l));var v=mk('strong');v.id=UID+'-ms-'+it.id;ap(c,v);ap(msg,c);
  });
  ap(summ,msg);ap(box,summ);
  // Formulaire
  var form=mk('div','modal-form');form.id=UID+'-mform';
  var row1=mk('div','mfrow');
  var fPrn=mk('input','mfi');fPrn.id=UID+'-f-prn';fPrn.type='text';fPrn.placeholder='Prénom *';
  var fNom=mk('input','mfi');fNom.id=UID+'-f-nom';fNom.type='text';fNom.placeholder='Nom *';
  fPrn.style.marginBottom='0';fNom.style.marginBottom='0';
  ap(row1,fPrn);ap(row1,fNom);ap(form,row1);
  var fMail=mk('input','mfi');fMail.id=UID+'-f-mail';fMail.type='email';fMail.placeholder='Email *';
  var fTel=mk('input','mfi');fTel.id=UID+'-f-tel';fTel.type='tel';fTel.placeholder='Téléphone *';
  ap(form,mk('div',null,''));// spacer
  var sp1=mk('div');sp1.style.marginTop='10px';ap(sp1,fMail);ap(form,sp1);
  var sp2=mk('div');sp2.style.marginTop='10px';ap(sp2,fTel);ap(form,sp2);
  // RGPD
  var rgpd=mk('label','rgpd');
  var chk=document.createElement('input');chk.type='checkbox';chk.id=UID+'-f-rgpd';
  var txt=mk('span');
  txt.innerHTML='J\'accepte la <a href="https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/" target="_blank" rel="noopener">politique de confidentialité</a> et consens au traitement de mes données pour recevoir un devis';
  ap(rgpd,chk);ap(rgpd,txt);ap(form,rgpd);
  // Erreur
  var err=mk('div','mferr','⚠️ Merci de remplir tous les champs et d\'accepter la politique de confidentialité.');err.id=UID+'-f-err';ap(form,err);
  // Submit
  var sub=mk('button','modal-sub','Envoyer ma demande >');sub.id=UID+'-f-sub';
  sub.addEventListener('click',submitDevis);ap(form,sub);
  ap(box,form);
  // Fermer sur click overlay
  ov.addEventListener('click',function(e){if(e.target===ov)closeModal();});
  ap(ov,box);ap(root,ov);
}
function openModal(){
  var R=_R||calcAll();
  var ms={nb:R.nb+' panneaux',eco:R.eco.toLocaleString('fr-FR')+'€/an',budget:R.budget.toLocaleString('fr-FR')+'€',roi:R.roi+' ans'};
  Object.keys(ms).forEach(function(k){var el=$g('ms-'+k);if(el)el.textContent=ms[k];});
  var ov=$g('modal');if(ov){ov.className='modal-ov open';document.body.style.overflow='hidden';}
}
function closeModal(){var ov=$g('modal');if(ov){ov.className='modal-ov';document.body.style.overflow='';}}
function submitDevis(){
  var prn=($g('f-prn')||{}).value||'',nom=($g('f-nom')||{}).value||'';
  var mail=($g('f-mail')||{}).value||'',tel=($g('f-tel')||{}).value||'';
  var rgpd=$g('f-rgpd')&&$g('f-rgpd').checked;
  var err=$g('f-err');
  if(!prn.trim()||!nom.trim()||!mail.trim()||!tel.trim()||!rgpd){if(err)err.style.display='block';return;}
  if(err)err.style.display='none';
  var sub=$g('f-sub');if(sub){sub.innerHTML='<span class="spin"></span><span style="margin-left:8px">Envoi en cours...</span>';sub.disabled=true;}
  var R=_R||calcAll();
  var data={
    // Contact
    prenom:prn.trim(),nom:nom.trim(),email:mail.trim(),telephone:tel.trim(),
    // Logement
    adresse:S.adresse,surface:S.surface,
    annee_construction:S.annee_construction||2005,
    statut:S.statut==='proprio'?'Propriétaire':'Locataire',
    habitants:S.habitants,
    // Toiture
    orientation:(ORI[S.orientation]||ORI.S).l,
    pente:S.pente,
    // Usages
    energies:S.energies.join(', '),
    chauffage:CH_LABELS[S.chauffage]||S.chauffage,
    eau_chaude:{'elec':'Chauffe-eau électrique','gaz':'Chauffe-eau gaz','solaire':'Solaire thermique','pac':'Thermodynamique'}[S.eau]||S.eau,
    cuisson:{'elec':'Cuisine électrique','induction':'Induction','gaz':'Cuisine gaz','mixte':'Mixte'}[S.cuisson]||S.cuisson,
    // Résultats simulation
    nb_panneaux:R.nb,kwc:R.kwc,production:R.prod,
    economie:R.eco,budget:R.budget,roi:R.roi,co2:R.co2,
    // Source calcul
    pvgis_utilise:S.pvgis_prod&&S.pvgis_prod>0?'Oui (satellite)':'Non (estimation)',
    timestamp:new Date().toISOString(),
    src_post:new URLSearchParams(window.location.search).get('src_post')||''
  };
  // Log tracking BigQuery
  fetch(TRACK+'/api/log-clic',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tool:'simulateur-solaire-v24',offre_id:'devis-formulaire',energie:'solaire',kwh:R.prod,prix_annuel:R.budget,economie:R.eco,user_agent:navigator.userAgent.slice(0,120)})}).catch(function(){});
  // Envoi via WordPress AJAX (PHP > GAS côté serveur, bypass CORS/CSP)
  var fd=new FormData();
  fd.append('action','cme_submit_devis');
  fd.append('nonce',CME_NONCE);
  fd.append('payload',JSON.stringify(data));
  fetch(AJAX_URL,{method:'POST',body:fd})
    .then(function(r){return r.json();})
    .then(function(res){
      console.log('✅ Devis CME — email:'+res.data.email_sent+' | GAS:'+res.data.gas);
      showSuccess();
    })
    .catch(function(err){console.warn('❌ Erreur AJAX:',err);showSuccess();});
}
function showSuccess(){
  var form=$g('mform');
  if(form){
    var prn=($g('f-prn')||{}).value||'';
    var nom=($g('f-nom')||{}).value||'';
    var mail=($g('f-mail')||{}).value||'';
    var tel=($g('f-tel')||{}).value||'';
    var lienCompte='https://espace-client-217943559750.europe-west1.run.app/register?prenom='
      +encodeURIComponent(prn)+'&nom='+encodeURIComponent(nom)+'&email='+encodeURIComponent(mail)+'&telephone='+encodeURIComponent(tel);
    form.innerHTML='<div class="modal-ok"><div class="ok-ico">✓</div><h4>Demande envoyée !</h4><p>Nous vous contactons sous 48h à l\'adresse<br><strong>'+mail+'</strong><br><br>Vérifiez vos spams si vous ne recevez pas notre email.</p>'
      +'<a href="'+lienCompte+'" target="_blank" style="display:inline-block;margin-top:16px;background:#16a34a;color:#fff;font-weight:600;padding:12px 24px;border-radius:10px;text-decoration:none;font-size:14px">Créer mon espace client &rarr;</a>'
      +'<p style="font-size:12px;color:#9ca3af;margin-top:8px">Suivez l\'avancement de votre dossier en ligne</p></div>';
  }
  setTimeout(closeModal,8000);
}

/* ── Init ──────────────────────────────────────────────────────── */
function render(){
  var root=document.getElementById(UID);if(!root)return;root.innerHTML='';
  buildForm(root);
  var res=mk('div','results');res.id=UID+'-res';ap(root,res);
  buildModal(root);
}
render();
})();
</script>
<?php
$html = ob_get_clean();
  // Extraire le <script>...</script> et le deplacer en wp_footer
  // (evite que wpautop/wptexturize casse un script de 80k+ caracteres)
  if (preg_match('/<script>(.*?)<\/script>/s', $html, $m)) {
    $html = preg_replace('/<script>.*?<\/script>/s', '', $html, 1);
    global $cme_ss24_footer_scripts;
    if (!isset($cme_ss24_footer_scripts)) $cme_ss24_footer_scripts = array();
    $cme_ss24_footer_scripts[] = $m[1];
    if (!has_action('wp_footer', 'cme_ss24_print_footer_scripts')) {
      add_action('wp_footer', 'cme_ss24_print_footer_scripts', 99);
    }
  }
  return $html;
}

function cme_ss24_print_footer_scripts(){
  global $cme_ss24_footer_scripts;
  if (empty($cme_ss24_footer_scripts)) return;
  $i = 0;
  foreach ($cme_ss24_footer_scripts as $js) {
    $i++;
    // Encodage base64 : le payload devient du TEXTE OPAQUE pour tout minifieur/
    // combineur JS (LiteSpeed, Autoptimize, WP Rocket, Cloudflare Rocket Loader).
    // Ces outils ne parsent que les <script> de type JS executable ; un
    // type="text/plain" contenant du base64 est totalement ignore et ne peut
    // donc plus jamais etre corrompu, meme si les reglages d'optimisation
    // changent ou sont reinitialises plus tard.
    $b64 = base64_encode($js);
    echo '<script type="text/plain" id="cme-ss24-payload-'.$i.'" data-no-optimize="1" data-noptimize="1" data-cfasync="false">'.$b64.'</script>'."\n";
    echo '<script id="cme-ss24-loader-'.$i.'" data-no-optimize="1" data-noptimize="1" data-cfasync="false">'
        .'(function(){var e=document.getElementById("cme-ss24-payload-'.$i.'");if(!e)return;'
        .'var c=decodeURIComponent(escape(atob(e.textContent||e.innerText)));'
        .'var s=document.createElement("script");s.text=c;document.body.appendChild(s);})();'
        .'</script>'."\n";
  }
}
