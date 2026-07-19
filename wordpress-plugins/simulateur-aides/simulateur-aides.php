<?php
/**
 * Plugin Name: CME Simulateur Aides Rénovation
 * Plugin URI:  https://www.comprendre-mon-energie.fr
 * Description: Simulateur d'éligibilité MaPrimeRénov' + CEE + Éco-PTZ + TVA réduite + aides locales
 * Version:     1.0.1
 * Author:      CME
 */
if(!defined('ABSPATH'))exit;

// ── Proxy logo CME (base64 pour jsPDF) — identique au solaire ────────────────
if(!function_exists('cme_aid_logo_b64')):
add_action('wp_ajax_cme_aid_logo_b64','cme_aid_logo_b64');
add_action('wp_ajax_nopriv_cme_aid_logo_b64','cme_aid_logo_b64');
function cme_aid_logo_b64(){
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
endif;

// ── Reglages admin — URL Google Sheets (leads aides) ──────────────────────────
if(!function_exists('cme_aid_get_gas_url')):
function cme_aid_get_gas_url(){
  $db_url = get_option('cme_aid_gas_url','');
  if($db_url) return $db_url;
  return (defined('CME_AID_APPS_SCRIPT_URL') && CME_AID_APPS_SCRIPT_URL) ? CME_AID_APPS_SCRIPT_URL : '';
}
endif;

add_action('admin_menu', function(){
  add_options_page('CME Aides - Reglages','CME Simulateur Aides','manage_options','cme-aid-settings','cme_aid_settings_page');
});
add_action('admin_init', function(){
  register_setting('cme_aid_group','cme_aid_gas_url', array('sanitize_callback'=>'esc_url_raw'));
});
function cme_aid_settings_page(){
  $url = cme_aid_get_gas_url();
  $ok  = !empty($url);
  ?>
  <div class="wrap">
    <h1>CME Simulateur Aides - Reglages Google Sheets</h1>
    <?php if($ok): ?>
    <div class="notice notice-success"><p><strong>OK</strong> - URL configuree : <code><?php echo esc_html($url); ?></code></p></div>
    <?php else: ?>
    <div class="notice notice-error"><p><strong>URL manquante</strong> - Remplissez le champ ci-dessous.</p></div>
    <?php endif; ?>
    <form method="post" action="options.php">
      <?php settings_fields('cme_aid_group'); ?>
      <table class="form-table">
        <tr><th>URL Apps Script (Leads Aides)</th><td>
          <input type="url" name="cme_aid_gas_url" value="<?php echo esc_attr(get_option('cme_aid_gas_url','')); ?>" class="regular-text" placeholder="https://script.google.com/macros/s/.../exec"/>
          <p class="description">URL /exec obtenue apres deploiement de cme-aides-leads.gs</p>
        </td></tr>
      </table>
      <p><input type="submit" class="button-primary" value="Enregistrer"/></p>
    </form>
  </div>
  <?php
}

// ── Handler AJAX Lead ──────────────────────────────────────────────────────
if(!function_exists('cme_aid_handle_lead')):
function cme_aid_handle_lead(){
  if(!check_ajax_referer('cme_aid_lead_nonce','nonce',false)){
    wp_send_json_error(array('msg'=>'Nonce invalide'));return;
  }
  $raw  = wp_unslash(isset($_POST['payload'])?$_POST['payload']:'');
  $data = json_decode($raw,true);
  if(!$data){wp_send_json_error(array('msg'=>'Payload invalide'));return;}

  $prenom = sanitize_text_field($data['prenom']??'');
  $nom    = sanitize_text_field($data['nom']??'');
  $email  = sanitize_email($data['email']??'');
  $tel    = sanitize_text_field($data['telephone']??'');
  $adresse= sanitize_text_field($data['adresse']??'');
  $profil = sanitize_text_field($data['profil']??'');
  $travaux= sanitize_text_field($data['travaux']??'');
  $mpr    = intval($data['montant_mpr']??0);
  $cee    = intval($data['montant_cee']??0);
  $total_aides = intval($data['total_aides']??0);
  $budget = intval($data['budget']??0);
  $reste  = intval($data['reste_a_charge']??0);
  $dest   = 'contact@comprendre-mon-energie.fr';

  $sujet = '🏠 Nouvelle demande Aides Rénovation — '.$prenom.' '.$nom.' — Profil '.$profil;

  $corps = '<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:580px;margin:auto">
    <div style="background:linear-gradient(135deg,#92400e,#f59e0b);color:#fff;padding:20px 24px;border-radius:10px 10px 0 0">
      <h2 style="margin:0">🏠 Nouvelle demande — Simulateur Aides Rénovation</h2>
      <p style="margin:4px 0 0;opacity:.85;font-size:13px">'.date('d/m/Y H:i').'</p>
    </div>
    <div style="background:#fff;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 10px 10px;padding:20px 24px">
      <h3 style="color:#f59e0b;margin:0 0 12px">Contact</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
        <tr><td style="padding:6px;color:#6b7280;width:150px">Nom complet</td><td style="padding:6px;font-weight:600">'.$prenom.' '.$nom.'</td></tr>
        <tr><td style="padding:6px;color:#6b7280">Email</td><td style="padding:6px"><a href="mailto:'.$email.'" style="color:#f59e0b">'.$email.'</a></td></tr>
        <tr><td style="padding:6px;color:#6b7280">Telephone</td><td style="padding:6px"><a href="tel:'.$tel.'" style="color:#f59e0b">'.$tel.'</a></td></tr>
        <tr><td style="padding:6px;color:#6b7280">Adresse</td><td style="padding:6px">'.$adresse.'</td></tr>
      </table>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 16px">
      <h3 style="color:#f59e0b;margin:0 0 12px">Simulation</h3>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:5px;color:#6b7280">Profil MaPrimeRenov</td><td style="padding:5px;font-weight:600">'.$profil.'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Travaux envisages</td><td style="padding:5px;font-weight:600">'.$travaux.'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Budget travaux</td><td style="padding:5px;font-weight:600">'.number_format($budget,0,',',' ').' EUR</td></tr>
        <tr><td style="padding:5px;color:#6b7280">MaPrimeRenov</td><td style="padding:5px;font-weight:600;color:#16a34a">'.number_format($mpr,0,',',' ').' EUR</td></tr>
        <tr><td style="padding:5px;color:#6b7280">CEE</td><td style="padding:5px;font-weight:600;color:#16a34a">'.number_format($cee,0,',',' ').' EUR</td></tr>
        <tr style="background:#fffbeb"><td style="padding:8px;color:#92400e;font-weight:600">Total aides</td><td style="padding:8px;font-weight:700;color:#92400e;font-size:16px">'.number_format($total_aides,0,',',' ').' EUR</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Reste a charge estime</td><td style="padding:5px;font-weight:600">'.number_format($reste,0,',',' ').' EUR</td></tr>
      </table>
    </div>
  </body></html>';

  $headers = array('Content-Type: text/html; charset=UTF-8','From: Simulateur Aides <noreply@comprendre-mon-energie.fr>');
  $mail_ok = wp_mail($dest,$sujet,$corps,$headers);

  $gas_url = cme_aid_get_gas_url();
  $gas_result = 'non configure';
  if($gas_url){
    $url = $gas_url.'?payload='.rawurlencode($raw);
    $resp = wp_remote_get($url,array('timeout'=>20,'blocking'=>true,'sslverify'=>false));
    $gas_result = is_wp_error($resp)?'erreur:'.$resp->get_error_message():wp_remote_retrieve_body($resp);
  }

  wp_remote_post('https://cme-tracking-api-217943559750.europe-west1.run.app/api/log-lead', array(
    'timeout' => 8, 'blocking' => false, 'sslverify' => false,
    'headers' => array('Content-Type' => 'application/json'),
    'body' => json_encode(array(
      'tool' => 'aides-renovation', 'prenom' => $prenom, 'nom' => $nom, 'email' => $email,
      'telephone' => $tel, 'adresse' => $adresse, 'montant_estime' => $budget,
      'economie_estimee' => $total_aides,
      'details' => array('profil'=>$profil,'travaux'=>$travaux,'montant_mpr'=>$mpr,'montant_cee'=>$cee,'reste_a_charge'=>$reste),
      'source_page' => 'simulateur-aides-renovation-energetique',
      'source_post_id' => sanitize_text_field($data['src_post'] ?? '')
    ))
  ));

  wp_send_json_success(array('status'=>'ok','email_sent'=>$mail_ok,'gas'=>$gas_result));
}
endif;
add_action('wp_ajax_cme_aid_lead','cme_aid_handle_lead');
add_action('wp_ajax_nopriv_cme_aid_lead','cme_aid_handle_lead');

// ── Footer scripts (base64, immunise contre minifieurs des le depart) ────────
if(!function_exists('cme_aid_print_footer_scripts')):
function cme_aid_print_footer_scripts(){
  global $cme_aid_footer_scripts;
  if (empty($cme_aid_footer_scripts)) return;
  $i = 0;
  foreach ($cme_aid_footer_scripts as $js) {
    $i++;
    $b64 = base64_encode($js);
    echo '<script type="text/plain" id="cme-aid-payload-'.$i.'" data-no-optimize="1" data-noptimize="1" data-cfasync="false">'.$b64.'</script>'."\n";
    echo '<script id="cme-aid-loader-'.$i.'" data-no-optimize="1" data-noptimize="1" data-cfasync="false">'
        .'(function(){var e=document.getElementById("cme-aid-payload-'.$i.'");if(!e)return;'
        .'var c=decodeURIComponent(escape(atob(e.textContent||e.innerText)));'
        .'var s=document.createElement("script");s.text=c;document.body.appendChild(s);})();'
        .'</script>'."\n";
  }
}
endif;

if(!function_exists('cme_aid_sc')):
function cme_aid_sc($atts){
$uid='aid'.uniqid();
$aid_nonce=wp_create_nonce('cme_aid_lead_nonce');
$aid_ajax=esc_js(admin_url('admin-ajax.php'));
ob_start();?>
<style>
#<?php echo $uid;?>{--g1:#78350f;--g2:#b45309;--g3:#f59e0b;--g4:#d97706;--gb:#fffbeb;--gbl:#fde68a;--gbm:#fcd34d;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;width:100%;max-width:1400px;margin:0 auto;background:#f1f5f9}
#<?php echo $uid;?> *{box-sizing:border-box;-webkit-text-size-adjust:100%}
#<?php echo $uid;?> .aid-hero{background:linear-gradient(135deg,var(--g1) 0%,var(--g2) 55%,var(--g3) 100%);color:#fff;padding:2.25rem 2rem 2rem;display:flex;align-items:center;gap:2rem;flex-wrap:wrap}
#<?php echo $uid;?> .hero-text{flex:1;min-width:200px}
#<?php echo $uid;?> .hero-title{font-size:clamp(20px,3vw,28px);font-weight:800;margin:0 0 6px}
#<?php echo $uid;?> .hero-sub{font-size:clamp(13px,1.5vw,15px);opacity:.85;margin:0 0 12px;line-height:1.5}
#<?php echo $uid;?> .hbadge{background:rgb(255 255 255 / .15);border:1px solid rgb(255 255 255 / .25);border-radius:20px;padding:4px 12px;font-size:12px;margin-right:6px;margin-bottom:4px;display:inline-block}
#<?php echo $uid;?> .aid-body{display:grid;grid-template-columns:1fr;gap:0}
@media(min-width:860px){#<?php echo $uid;?> .aid-body{grid-template-columns:62% 38%}}
#<?php echo $uid;?> .aid-left{padding:1.25rem;display:flex;flex-direction:column;gap:12px}
#<?php echo $uid;?> .aid-right{padding:1.25rem 1.25rem 1.25rem 0;display:flex;flex-direction:column;gap:12px}
@media(max-width:859px){#<?php echo $uid;?> .aid-right{padding:0 1.25rem 1.25rem}}
@media(min-width:860px){#<?php echo $uid;?> .aid-right{position:sticky;top:0;align-self:start;max-height:100vh;overflow-y:auto}}
#<?php echo $uid;?> .sc{background:#fff;border-radius:14px;padding:1.25rem;box-shadow:0 1px 4px rgb(0 0 0 / .06)}
#<?php echo $uid;?> .stitle{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;color:#111827;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #f3f4f6}
#<?php echo $uid;?> label{font-size:13px;color:#6b7280;display:block;margin-bottom:6px;font-weight:500}
#<?php echo $uid;?> .hint{font-size:12px;color:#9ca3af;margin-top:5px;line-height:1.4}
#<?php echo $uid;?> .addr-row{display:flex;gap:8px}
#<?php echo $uid;?> .inp-wrap{flex:1;position:relative}
#<?php echo $uid;?> .addr-inp{width:100%;border:1.5px solid #e5e7eb;border-radius:10px;padding:0 14px;height:52px;font-size:16px;background:#f9fafb;color:#111827;outline:none;font-family:inherit;-webkit-appearance:none;transition:border .15s;display:block}
#<?php echo $uid;?> .addr-inp:focus{border-color:var(--g3);background:#fff;box-shadow:0 0 0 3px rgb(245 158 11 / .1)}
#<?php echo $uid;?> .gps-btn{width:52px;height:52px;border:1.5px solid #e5e7eb;border-radius:10px;background:#f9fafb;font-size:18px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:all .15s}
#<?php echo $uid;?> .gps-btn:hover{border-color:var(--g3);background:var(--gb)}
#<?php echo $uid;?> .ac-drop{display:none;position:absolute;top:56px;left:0;right:0;background:#fff;border:1.5px solid var(--g3);border-radius:12px;z-index:99999;max-height:260px;overflow-y:auto;box-shadow:0 8px 28px rgb(245 158 11 / .18)}
#<?php echo $uid;?> .ac-drop.open{display:block}
#<?php echo $uid;?> .ac-item{padding:11px 14px;cursor:pointer;border-bottom:1px solid #f3f4f6;transition:background .1s}
#<?php echo $uid;?> .ac-item:last-child{border-bottom:none}
#<?php echo $uid;?> .ac-item:hover{background:var(--gb)}
#<?php echo $uid;?> .ac-name{font-size:14px;color:#111827;font-weight:500}
#<?php echo $uid;?> .ac-ctx{font-size:11px;color:#6b7280;margin-top:2px}
#<?php echo $uid;?> .addr-status{font-size:12px;color:#6b7280;margin-top:5px;display:none}
#<?php echo $uid;?> .info-grn{background:var(--gb);border:1px solid var(--gbl);border-radius:8px;padding:9px 12px;font-size:13px;color:var(--g4);margin-top:8px;display:none}
#<?php echo $uid;?> input[type=number]{border:1.5px solid #e5e7eb;border-radius:10px;padding:0 8px 0 14px;height:52px;font-size:16px;background:#f9fafb;color:#111827;width:100%;outline:none;font-family:inherit;-moz-appearance:textfield;transition:border .15s}
#<?php echo $uid;?> input[type=number]:focus{border-color:var(--g3);background:#fff;box-shadow:0 0 0 3px rgb(245 158 11 / .1)}
#<?php echo $uid;?> .g2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
#<?php echo $uid;?> .tog{display:flex;gap:8px}
#<?php echo $uid;?> .tbtn{flex:1;height:52px;border:1.5px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:14px;cursor:pointer;font-family:inherit;transition:all .15s;font-weight:500}
#<?php echo $uid;?> .tbtn.on{border-color:var(--g3);background:var(--g3);color:#fff;font-weight:600}
#<?php echo $uid;?> .stepper{display:flex;align-items:center;border:1.5px solid #e5e7eb;border-radius:10px;overflow:hidden;background:#fff;height:52px}
#<?php echo $uid;?> .step-btn{width:52px;height:100%;border:none;background:#fff0;font-size:22px;cursor:pointer;color:#374151;flex-shrink:0;transition:background .15s}
#<?php echo $uid;?> .step-btn:hover{background:var(--gb);color:var(--g4)}
#<?php echo $uid;?> .step-val{flex:1;text-align:center;font-size:18px;font-weight:700;color:#111827}
#<?php echo $uid;?> .opts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px}
#<?php echo $uid;?> .obtn{min-height:56px;border:1.5px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:13px;cursor:pointer;font-family:inherit;transition:all .15s;display:flex;align-items:center;justify-content:center;gap:6px;font-weight:500;padding:8px;text-align:center;line-height:1.3}
#<?php echo $uid;?> .obtn:hover{border-color:var(--gbm);background:var(--gb);color:var(--g4)}
#<?php echo $uid;?> .obtn.on{border-color:var(--g3);background:var(--gb);color:var(--g4);font-weight:600;box-shadow:0 2px 8px rgb(245 158 11/.2)}
#<?php echo $uid;?> .dpe-row{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}
#<?php echo $uid;?> .dpe-btn{width:44px;height:44px;border-radius:8px;border:2.5px solid #fff0;font-size:16px;font-weight:800;cursor:pointer;font-family:inherit;transition:all .15s;color:#fff;flex-shrink:0;display:flex;align-items:center;justify-content:center;text-align:center;line-height:1;padding:0}
#<?php echo $uid;?> .dpe-btn.on{border-color:#111;transform:scale(1.18);box-shadow:0 3px 10px rgb(0 0 0 / .3);z-index:1;position:relative}
#<?php echo $uid;?> .dpe-info{font-size:12px;margin-top:8px;padding:8px 12px;border-radius:8px;border:1px solid #e5e7eb;background:#f9fafb;color:#374151;line-height:1.4}
#<?php echo $uid;?> .cta-btn{width:100%;height:60px;border:none;border-radius:14px;background:linear-gradient(135deg,var(--g4),var(--g3));color:#fff;font-size:17px;font-weight:700;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:10px;box-shadow:0 4px 20px rgb(245 158 11 / .4);transition:opacity .15s;margin-top:4px}
#<?php echo $uid;?> .cta-btn:hover{opacity:.9}
#<?php echo $uid;?> .cta-btn:disabled{opacity:.7;cursor:not-allowed}
#<?php echo $uid;?> .aid-prev{background:#fff;border-radius:14px;padding:1.25rem;box-shadow:0 1px 4px rgb(0 0 0 / .06)}
#<?php echo $uid;?> .prev-title{font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.07em;margin-bottom:12px}
#<?php echo $uid;?> .prev-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
#<?php echo $uid;?> .prev-card{background:#f8fafc;border-radius:10px;padding:10px;text-align:center}
#<?php echo $uid;?> .prev-val{font-size:17px;font-weight:700;color:var(--g4)}
#<?php echo $uid;?> .prev-lbl{font-size:11px;color:#6b7280;margin-top:2px}
#<?php echo $uid;?> .profil-badge{display:flex;align-items:center;gap:10px;padding:12px;border-radius:10px;margin-top:10px;font-weight:700;font-size:13px}
#<?php echo $uid;?> .profil-bleu{background:#dbeafe;color:#1e40af}
#<?php echo $uid;?> .profil-jaune{background:#fef9c3;color:#854d0e}
#<?php echo $uid;?> .profil-violet{background:#ede9fe;color:#5b21b6}
#<?php echo $uid;?> .profil-rose{background:#fce7f3;color:#9d174d}
#<?php echo $uid;?> .recap{background:#fff;border-radius:14px;padding:1.25rem;box-shadow:0 1px 4px rgb(0 0 0 / .06)}
#<?php echo $uid;?> .recap-title{font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px}
#<?php echo $uid;?> .ri{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #f3f4f6}
#<?php echo $uid;?> .ri:last-child{border-bottom:none}
#<?php echo $uid;?> .ri-lbl{font-size:12px;color:#6b7280;flex:1}
#<?php echo $uid;?> .ri-val{font-size:12px;font-weight:600;color:#111827;text-align:right}
#<?php echo $uid;?> .ri-empty{color:#d1d5db;font-style:italic;font-weight:400}
#<?php echo $uid;?> .results{display:none;padding:1.25rem}
#<?php echo $uid;?> .results.show{display:block;animation:si .5s ease}
@keyframes si{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
#<?php echo $uid;?> .res-hero{background:linear-gradient(135deg,#78350f 0%,var(--g1) 30%,var(--g2) 65%,var(--g3) 100%);border-radius:16px;padding:1.75rem;color:#fff;margin-bottom:12px}
#<?php echo $uid;?> .res-title{font-size:20px;font-weight:800;text-align:center;margin-bottom:6px}
#<?php echo $uid;?> .res-sub{font-size:13px;opacity:.75;text-align:center}
#<?php echo $uid;?> .res-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
@media(max-width:480px){#<?php echo $uid;?> .res-cards{grid-template-columns:1fr 1fr}}
#<?php echo $uid;?> .rcard{background:#fff;border-radius:12px;padding:14px 10px;text-align:center;border:1px solid #f3f4f6}
#<?php echo $uid;?> .rcard-ico{font-size:22px;margin-bottom:4px}
#<?php echo $uid;?> .rcard-val{font-size:16px;font-weight:700;color:#111827}
#<?php echo $uid;?> .rcard.eco .rcard-val{color:var(--g4)}
#<?php echo $uid;?> .rcard-lbl{font-size:11px;color:#6b7280;margin-top:3px;line-height:1.3}
#<?php echo $uid;?> .aide-row{display:flex;align-items:flex-start;gap:10px;padding:10px 0;border-bottom:1px solid #f3f4f6}
#<?php echo $uid;?> .aide-row:last-of-type{border-bottom:none}
#<?php echo $uid;?> .aide-ico{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0;margin-top:1px}
#<?php echo $uid;?> .aide-nom{font-size:13px;font-weight:600;color:#111827;margin-bottom:2px}
#<?php echo $uid;?> .aide-det{font-size:11px;color:#6b7280;line-height:1.4}
#<?php echo $uid;?> .aide-cond{font-size:11px;color:#16a34a;font-weight:500;margin-top:2px}
#<?php echo $uid;?> .aide-cond.no{color:#9ca3af}
#<?php echo $uid;?> .aide-amt{font-size:14px;font-weight:700;text-align:right;min-width:90px;flex-shrink:0;margin-top:2px}
#<?php echo $uid;?> .budget-summ{background:#fffbeb;border-radius:10px;padding:14px;margin-top:8px;border:1px solid #fde68a}
#<?php echo $uid;?> .bs-row{display:flex;justify-content:space-between;font-size:13px;padding:3px 0}
#<?php echo $uid;?> .bs-net{display:flex;justify-content:space-between;align-items:baseline;margin-top:8px;padding-top:8px;border-top:1px solid #fde68a}
#<?php echo $uid;?> .pdf-btn{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;height:52px;border-radius:12px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);color:#fff;font-size:15px;font-weight:700;cursor:pointer;border:none;font-family:inherit;transition:opacity .15s;margin-top:16px;margin-bottom:20px}
#<?php echo $uid;?> .pdf-btn:hover{opacity:.88}
#<?php echo $uid;?> .pdf-btn:disabled{opacity:.6;cursor:not-allowed}
#<?php echo $uid;?> .cta2{background:linear-gradient(135deg,var(--g4),var(--g3));border-radius:16px;padding:1.25rem;text-align:center;margin-bottom:12px}
#<?php echo $uid;?> .cta2 h3{font-size:16px;font-weight:700;color:#fff;margin:0 0 6px}
#<?php echo $uid;?> .cta2 p{font-size:13px;color:rgb(255 255 255 / .9);margin:0 0 14px;line-height:1.4}
#<?php echo $uid;?> .cta2-btn{height:48px;padding:0 28px;border-radius:10px;background:#fff;color:var(--g4);font-size:15px;font-weight:700;cursor:pointer;border:none;font-family:inherit;transition:all .15s}
#<?php echo $uid;?> .cta2-btn:hover{background:var(--gb)}
#<?php echo $uid;?> .fnote{font-size:11px;color:#9ca3af;line-height:1.6;margin-bottom:8px}
#<?php echo $uid;?> .new-sim{width:100%;height:44px;border:1px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:13px;cursor:pointer;font-family:inherit;margin-bottom:12px;transition:all .15s}
.lmodal-ov{display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:99999;align-items:center;justify-content:center;padding:16px}
.lmodal-ov.open{display:flex}
.lmodal-box{background:#fff;border-radius:16px;width:100%;max-width:420px;max-height:90vh;overflow-y:auto;box-shadow:0 20px 50px rgba(0,0,0,.3)}
.lmodal-head{background:linear-gradient(135deg,#92400e,#f59e0b);color:#fff;padding:18px 22px;border-radius:16px 16px 0 0;font-size:16px;font-weight:700;position:relative}
.lmodal-close{position:absolute;top:12px;right:14px;background:rgba(255,255,255,.2);border:none;color:#fff;width:28px;height:28px;border-radius:50%;font-size:18px;line-height:1;cursor:pointer}
.lmodal-summ{background:#fffbeb;margin:16px 22px 0;padding:12px 14px;border-radius:10px;border:1px solid #fde68a}
.lmfrow{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:16px 22px 0}
.lmfi{width:100%;height:44px;border:1px solid #e5e7eb;border-radius:8px;padding:0 12px;font-size:15px;background:#f9fafb;color:#111827;box-sizing:border-box}
.lmfi:focus{outline:none;border-color:#f59e0b;background:#fff}
.lmrgpd{display:flex;align-items:flex-start;gap:8px;padding:14px 22px 0;font-size:12px;color:#6b7280;line-height:1.5;cursor:pointer}
.lmrgpd input{margin-top:2px;flex-shrink:0}
.lmferr{display:none;color:#dc2626;font-size:12px;padding:10px 22px 0;line-height:1.4}
.lmodal-sub{width:calc(100% - 44px);margin:16px 22px 22px;height:46px;border:none;border-radius:10px;background:#f59e0b;color:#fff;font-size:15px;font-weight:600;cursor:pointer}
.lmodal-sub:disabled{opacity:.6;cursor:not-allowed}
@media(max-width:480px){.lmfrow{grid-template-columns:1fr}}
</style>
<div id="<?php echo $uid;?>"><p style="color:#9ca3af;font-size:14px;padding:1rem">⏳ Chargement...</p></div>
<script>
(function(){
'use strict';
var UID='<?php echo $uid;?>',
GEO='https://api-adresse.data.gouv.fr',
AJAX_URL='<?php echo $aid_ajax;?>',
AIDNONCE='<?php echo $aid_nonce;?>';

/* ── Barème officiel MaPrimeRénov' 2026 — Circulaire VLOL2534404C (Anah) ──── */
var BAREME = {
  idf: {
    1:{tm:24031,mo:29253,it:40851}, 2:{tm:35270,mo:42933,it:60051},
    3:{tm:42357,mo:51564,it:71846}, 4:{tm:49455,mo:60208,it:84562},
    5:{tm:56580,mo:68877,it:96817}, plus:{tm:7116,mo:8663,it:12257}
  },
  autre: {
    1:{tm:17363,mo:22259,it:31185}, 2:{tm:25393,mo:32553,it:45842},
    3:{tm:30540,mo:39148,it:55196}, 4:{tm:35676,mo:45735,it:64550},
    5:{tm:40835,mo:52348,it:73907}, plus:{tm:5151,mo:6598,it:9357}
  }
};

// Départements Île-de-France
var DEPTS_IDF = ['75','77','78','91','92','93','94','95'];

function seuils(personnes, idf){
  var n = Math.max(1, Math.min(5, personnes));
  var t = BAREME[idf?'idf':'autre'];
  var base = t[n];
  if(personnes > 5){
    var extra = personnes - 5;
    return {
      tm: base.tm===undefined?t[5].tm+extra*t.plus.tm:t[5].tm+extra*t.plus.tm,
      mo: t[5].mo+extra*t.plus.mo,
      it: t[5].it+extra*t.plus.it
    };
  }
  return base;
}

function calcProfil(rfr, personnes, idf){
  var s = seuils(personnes, idf);
  if(rfr <= s.tm) return 'bleu';
  if(rfr <= s.mo) return 'jaune';
  if(rfr <= s.it) return 'violet';
  return 'rose';
}

var PROFIL_LBL = {bleu:'Très modeste (Bleu)', jaune:'Modeste (Jaune)', violet:'Intermédiaire (Violet)', rose:'Supérieur (Rose)'};

/* ── Forfaits MaPrimeRénov' parcours mono-geste (2026) ─────────────────────── */
var FORFAITS_GESTE = {
  pac_air_eau:    {nom:'Pompe à chaleur air/eau',        bleu:5000, jaune:4000, violet:3000, rose:0, unit:false},
  pac_geo:        {nom:'Pompe à chaleur géothermique',   bleu:11000,jaune:9000, violet:6000, rose:0, unit:false},
  cet:            {nom:'Chauffe-eau thermodynamique',    bleu:1200, jaune:800,  violet:400,  rose:0, unit:false},
  chauffe_eau_solaire:{nom:'Chauffe-eau solaire individuel',bleu:4000,jaune:3000,violet:2000,rose:0, unit:false},
  poele_bois:     {nom:'Poêle à bois / insert',          bleu:2500, jaune:1500, violet:1000, rose:0, unit:false},
  isolation_combles:{nom:'Isolation combles/rampants (m²)',bleu:25,jaune:20,   violet:15,   rose:0, unit:true},
  isolation_toiture:{nom:'Isolation toiture terrasse (m²)',bleu:75,jaune:60,   violet:40,   rose:0, unit:true},
  fenetres:       {nom:'Fenêtres (par équipement)',      bleu:100,  jaune:80,   violet:40,   rose:0, unit:false},
  vmc_double_flux:{nom:'VMC double flux',                bleu:1500, jaune:1000, violet:600,  rose:0, unit:false},
  audit:          {nom:'Audit énergétique',              bleu:500,  jaune:400,  violet:300,  rose:200,unit:false}
};

/* ── CEE — forfaits indicatifs cumulables (parcours par geste) ─────────────── */
var FORFAITS_CEE = {
  pac_air_eau:2000, pac_geo:3000, cet:500, chauffe_eau_solaire:800,
  poele_bois:400, isolation_combles:0, isolation_toiture:0,
  fenetres:0, vmc_double_flux:500, audit:0
};

/* ── Rénovation d'ampleur — taux + plafonds dépenses éligibles ─────────────── */
var AMPLEUR = {
  bleu:  {taux:0.80, plafond_idf:80000, plafond_autre:70000},
  jaune: {taux:0.60, plafond_idf:70000, plafond_autre:60000},
  violet:{taux:0.45, plafond_idf:52500, plafond_autre:45000},
  rose:  {taux:0.10, plafond_idf:35000, plafond_autre:30000}
};

/* ── Écrêtement cumul MPR + CEE (parcours par geste) ────────────────────────── */
var ECRETEMENT = {bleu:0.90, jaune:0.75, violet:0.60, rose:0};

/* ── Aides régionales (même table que solaire) ──────────────────────────────── */
var REG_DEPT={
  '22':'BR','29':'BR','35':'BR','56':'BR','44':'PL','49':'PL','53':'PL','72':'PL','85':'PL',
  '14':'NM','27':'NM','50':'NM','61':'NM','76':'NM','02':'HF','59':'HF','60':'HF','62':'HF','80':'HF',
  '08':'GE','10':'GE','51':'GE','52':'GE','54':'GE','55':'GE','57':'GE','67':'GE','68':'GE','88':'GE',
  '75':'IF','77':'IF','78':'IF','91':'IF','92':'IF','93':'IF','94':'IF','95':'IF',
  '18':'CV','28':'CV','36':'CV','37':'CV','41':'CV','45':'CV',
  '21':'BF','25':'BF','39':'BF','58':'BF','70':'BF','71':'BF','89':'BF','90':'BF',
  '01':'AR','03':'AR','07':'AR','15':'AR','26':'AR','38':'AR','42':'AR','43':'AR','63':'AR','69':'AR','73':'AR','74':'AR',
  '16':'NA','17':'NA','19':'NA','23':'NA','24':'NA','33':'NA','40':'NA','47':'NA','64':'NA','79':'NA','86':'NA','87':'NA',
  '09':'OC','11':'OC','12':'OC','30':'OC','31':'OC','32':'OC','34':'OC','46':'OC','48':'OC','65':'OC','66':'OC','81':'OC','82':'OC',
  '04':'PA','05':'PA','06':'PA','13':'PA','83':'PA','84':'PA','2A':'CO','2B':'CO'
};
var AIDES_REG={
  'BR':{reg:'Bretagne',prog:'Breizh Énergies',min:500,max:1500},
  'PL':{reg:'Pays de la Loire',prog:'Énergie Pays de la Loire',min:400,max:1000},
  'NM':{reg:'Normandie',prog:'Aide Énergie Normandie',min:300,max:800},
  'HF':{reg:'Hauts-de-France',prog:'Energif Hauts-de-France',min:400,max:1200},
  'GE':{reg:'Grand Est',prog:'Grand Est Énergie',min:300,max:1000},
  'IF':{reg:'Île-de-France',prog:null,min:0,max:0},
  'CV':{reg:'Centre-Val de Loire',prog:'Aide Énergie CVL',min:300,max:800},
  'BF':{reg:'Bourgogne-Franche-Comté',prog:'BFC Énergie',min:300,max:800},
  'AR':{reg:'Auvergne-Rhône-Alpes',prog:'AURA Rénovation',min:500,max:1500},
  'NA':{reg:'Nouvelle-Aquitaine',prog:'NA Rénovation',min:500,max:2000},
  'OC':{reg:'Occitanie',prog:'Chèque Occitanie Rénovation',min:500,max:2000},
  'PA':{reg:'Région PACA',prog:'PACA Rénov',min:700,max:2500},
  'CO':{reg:'Corse',prog:'ADEC Rénovation',min:800,max:3000}
};

function getDept(cp){if(!cp||cp.length<2)return null;return cp.substring(0,2)==='97'?cp.substring(0,3):cp.substring(0,2);}
function getRegionNom(cp){
  var dept=getDept(cp);
  if(!dept)return null;
  if(DEPTS_IDF.indexOf(dept)>-1)return 'Île-de-France';
  var rc=REG_DEPT[dept];
  return rc && AIDES_REG[rc] ? AIDES_REG[rc].reg : null;
}
function $g(id){return document.getElementById(UID+'-'+id);}
function mk(t,c,x){var d=document.createElement(t);if(c)d.className=c;if(x!=null)d.textContent=x;return d;}
function ap(p,c){if(p&&c)p.appendChild(c);return p;}
function fmtNum(n){if(n===null||n===undefined||isNaN(n))return '-';var s=Math.round(n).toString();return s.replace(/\B(?=(\d{3})+(?!\d))/g,' ');}

var DPE_THERM={A:35,B:70,C:120,D:190,E:280,F:390,G:550};
var DPE_COL={A:'#00a84f',B:'#51b848',C:'#bcd630',D:'#f9c000',E:'#f07900',F:'#e73a1b',G:'#c00'};
function estimDPE(yr){return yr<1948?'G':yr<1975?'F':yr<1989?'E':yr<2001?'D':yr<2011?'D':yr<2021?'C':'B';}

/* ── État ─────────────────────────────────────────────────────────────────── */
var S={
  adresse:'', cp:'', lat:null, lng:null, idf:false,
  statut:'proprio', personnes:2, rfr:35000,
  annee_construction:2000, dpe:'E', dpe_confirmed:false,
  travaux:['pac_air_eau'], surface_isol:30,
  parcours:'geste' // 'geste' ou 'ampleur'
};

/* ── Moteur de calcul principal ──────────────────────────────────────────── */
function calcAll(){
  var idf = S.idf;
  var profil = calcProfil(S.rfr, S.personnes, idf);
  var f = FORFAITS_GESTE;

  // ── Parcours par geste : somme des forfaits MPR + CEE ──────────────────
  var mpr_geste = 0, cee_geste = 0, budget_geste = 0;
  S.travaux.forEach(function(t){
    var forfait = f[t];
    if(!forfait) return;
    var montant_mpr = forfait.unit ? (forfait[profil] * (S.surface_isol||30)) : forfait[profil];
    var montant_cee = FORFAITS_CEE[t] || 0;
    mpr_geste += montant_mpr;
    cee_geste += montant_cee;
    // Budget travaux estimatif (ordre de grandeur par geste)
    var couts_indicatifs = {
      pac_air_eau:12000, pac_geo:18000, cet:2500, chauffe_eau_solaire:6000,
      poele_bois:4000, isolation_combles:(S.surface_isol||30)*45,
      isolation_toiture:(S.surface_isol||30)*90, fenetres:800,
      vmc_double_flux:4000, audit:800
    };
    budget_geste += couts_indicatifs[t] || 0;
  });

  // Écrêtement : MPR + CEE ne peut dépasser X% du budget selon profil
  var plafond_ecretement = budget_geste * (ECRETEMENT[profil]||0);
  var cumul_geste = mpr_geste + cee_geste;
  if(cumul_geste > plafond_ecretement && plafond_ecretement > 0){
    var ratio = plafond_ecretement / cumul_geste;
    mpr_geste = Math.round(mpr_geste * ratio);
    cee_geste = Math.round(cee_geste * ratio);
  }
  // Plafond global 20 000€ sur 5 ans (parcours par geste)
  mpr_geste = Math.min(mpr_geste, 20000);

  // ── Parcours rénovation d'ampleur (si sélectionné) ──────────────────────
  var mpr_ampleur = 0, budget_ampleur = 0;
  if(S.parcours === 'ampleur'){
    var amp = AMPLEUR[profil];
    budget_ampleur = Math.max(budget_geste, 25000); // ordre de grandeur bouquet travaux
    var plafond_dep = idf ? amp.plafond_idf : amp.plafond_autre;
    var dep_eligible = Math.min(budget_ampleur, plafond_dep);
    mpr_ampleur = Math.round(dep_eligible * amp.taux);
  }

  var budget = S.parcours === 'ampleur' ? budget_ampleur : budget_geste;
  var mpr = S.parcours === 'ampleur' ? mpr_ampleur : mpr_geste;
  var cee = S.parcours === 'ampleur' ? 0 : cee_geste; // CEE non cumulable en ampleur

  // ── TVA réduite 5,5% (tous travaux MaPrimeRénov-éligibles) ──────────────
  var tva_taux_normal = 0.20, tva_taux_reduit = 0.055;
  var eco_tva = Math.round(budget * (tva_taux_normal - tva_taux_reduit) / (1+tva_taux_normal));

  // ── Aides locales ────────────────────────────────────────────────────────
  var dept = getDept(S.cp);
  var rc = dept ? REG_DEPT[dept] : null;
  var ar = rc ? AIDES_REG[rc] : null;
  var aide_locale = ar && ar.max > 0 ? Math.round((ar.min+ar.max)/2) : 0;

  var total_aides = mpr + cee + eco_tva + aide_locale;
  var reste_a_charge = Math.max(0, budget - total_aides);
  var eco_ptz_eligible = S.statut === 'proprio' && reste_a_charge > 0;
  var eco_ptz_montant = eco_ptz_eligible ? Math.min(reste_a_charge, 50000) : 0;

  return {
    profil: profil, profil_lbl: PROFIL_LBL[profil],
    budget: budget, mpr: mpr, cee: cee, eco_tva: eco_tva,
    aide_locale: aide_locale, aide_locale_nom: ar?ar.reg+' — '+(ar.prog||'Aides locales'):'',
    total_aides: total_aides, reste_a_charge: reste_a_charge,
    eco_ptz_eligible: eco_ptz_eligible, eco_ptz_montant: eco_ptz_montant,
    taux_couverture: budget>0 ? Math.round(total_aides/budget*100) : 0
  };
}

/* ── Prévisualisation en direct ──────────────────────────────────────────── */
function updatePrev(){
  var R = calcAll();
  var pv = {profil:R.profil_lbl, budget:fmtNum(R.budget)+' EUR', total:fmtNum(R.total_aides)+' EUR', reste:fmtNum(R.reste_a_charge)+' EUR'};
  Object.keys(pv).forEach(function(k){var el=$g('p-'+k);if(el)el.textContent=pv[k];});
  var badge = $g('profil-badge');
  if(badge){
    badge.className = 'profil-badge profil-'+R.profil;
    badge.textContent = '● '+R.profil_lbl;
  }
  var rv = {
    adr: S.adresse ? (S.adresse.length>28?S.adresse.substring(0,28)+'…':S.adresse) : '—',
    zone: S.cp ? (getRegionNom(S.cp) || (S.idf?'Île-de-France':'Hors Île-de-France')) : '—',
    foyer: S.personnes+' pers. — RFR '+fmtNum(S.rfr)+' EUR',
    statut: S.statut==='proprio'?'Propriétaire':'Locataire',
    dpe: 'Classe '+S.dpe,
    parcours: S.parcours==='ampleur'?'Rénovation d\'ampleur':'Par geste',
    travaux: S.travaux.length+' geste(s) sélectionné(s)'
  };
  Object.keys(rv).forEach(function(k){var el=$g('r-'+k);if(el){el.textContent=rv[k];el.className='ri-val'+(rv[k]==='—'?' ri-empty':'');}});
}

/* ── Autocomplete adresse (identique solaire) ────────────────────────────── */
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
              S.idf = DEPTS_IDF.indexOf(S.cp.substring(0,2))>-1;
              if(f.geometry&&f.geometry.coordinates){S.lng=f.geometry.coordinates[0];S.lat=f.geometry.coordinates[1];}
              if(irrEl){var regNom=getRegionNom(S.cp)||(S.idf?'Île-de-France':'Hors Île-de-France');irrEl.textContent='📍 '+regNom+' — '+p.city;irrEl.style.display='block';}
              updatePrev();
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
      if(d.features&&d.features[0]){var p=d.features[0].properties;S.adresse=p.label;S.cp=p.postcode||'';inp.value=p.label;S.idf=DEPTS_IDF.indexOf(S.cp.substring(0,2))>-1;if(irrEl){var regNom2=getRegionNom(S.cp)||(S.idf?'Île-de-France':'Hors Île-de-France');irrEl.textContent='📍 '+regNom2+' — '+p.city;irrEl.style.display='block';}updatePrev();}
    }).catch(function(){stEl.textContent='Erreur';});
  },function(){stEl.textContent='Accès refusé';stEl.style.display='block';});
}

function svgI(p,s){s=s||18;return '<svg width="'+s+'" height="'+s+'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'+p+'</svg>';}
var SI={loc:'<path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/>',home:'<path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9,22 9,12 15,12 15,22"/>',bolt:'<polygon points="13,2 3,14 12,14 11,22 21,10 12,10 13,2"/>',euro:'<path d="M6 8c0-4 3-6 6-6s5 2 6 4"/><path d="M6 16c0 4 3 6 6 6s5-2 6-4"/><line x1="2" y1="10" x2="14" y2="10"/><line x1="2" y1="14" x2="14" y2="14"/>'};
function mkTit(ico,txt){var d=mk('div','stitle');d.innerHTML=svgI(SI[ico])+' '+txt;return d;}

var TRAVAUX_LIST = [
  ['pac_air_eau','🌡️ Pompe à chaleur air/eau'],
  ['pac_geo','🔥 Pompe à chaleur géothermique'],
  ['cet','♨️ Chauffe-eau thermodynamique'],
  ['chauffe_eau_solaire','☀️ Chauffe-eau solaire'],
  ['poele_bois','🪵 Poêle à bois / insert'],
  ['isolation_combles','🏠 Isolation combles'],
  ['isolation_toiture','🏢 Isolation toiture terrasse'],
  ['fenetres','🪟 Fenêtres'],
  ['vmc_double_flux','💨 VMC double flux'],
  ['audit','📋 Audit énergétique']
];

function buildForm(root){
  var hero=mk('div','aid-hero');
  hero.innerHTML='<div class="hero-text"><h2 class="hero-title">🏠 Simulateur Aides Rénovation Énergétique</h2><p class="hero-sub">MaPrimeRénov\', CEE, Éco-PTZ, TVA réduite — estimez vos aides en 2 minutes</p><div><span class="hbadge">✓ Barème officiel 2026</span><span class="hbadge">✓ Sans engagement</span><span class="hbadge">✓ Devis inclus</span></div></div>';
  ap(root,hero);
  var body=mk('div','aid-body'),left=mk('div','aid-left'),right=mk('div','aid-right');

  /* S1: Logement */
  var s1=mk('div','sc');ap(s1,mkTit('loc','Votre logement'));
  ap(s1,mk('label',null,'Adresse'));
  var arow=mk('div','addr-row'),iw=mk('div','inp-wrap');
  var adI=mk('input','addr-inp');adI.type='text';adI.placeholder='Ex: 10 rue de la Paix, 75001 Paris...';adI.setAttribute('autocomplete','off');
  var drop=mk('div','ac-drop');ap(iw,adI);ap(iw,drop);
  var gpsB=mk('button','gps-btn');gpsB.type='button';gpsB.innerHTML='📍';
  ap(arow,iw);ap(arow,gpsB);ap(s1,arow);
  var adSt=mk('div','addr-status');ap(s1,adSt);
  var zoneBdg=mk('div','info-grn');ap(s1,zoneBdg);
  setupAddr(adI,drop,zoneBdg,adSt);
  gpsB.addEventListener('click',function(){doGPS(adI,zoneBdg,adSt);});

  var stW=mk('div');stW.style.marginTop='14px';ap(stW,mk('label',null,'Vous êtes'));
  var tog=mk('div','tog');
  var bP=mk('button','tbtn'+(S.statut==='proprio'?' on':''),'🏠 Propriétaire');
  var bL=mk('button','tbtn'+(S.statut==='locataire'?' on':''),'🔑 Locataire');
  bP.addEventListener('click',function(){S.statut='proprio';bP.className='tbtn on';bL.className='tbtn';updatePrev();});
  bL.addEventListener('click',function(){S.statut='locataire';bL.className='tbtn on';bP.className='tbtn';updatePrev();});
  ap(tog,bP);ap(tog,bL);ap(stW,tog);ap(s1,stW);

  var gH=mk('div','g2');gH.style.marginTop='14px';
  var hW=mk('div');ap(hW,mk('label',null,'Personnes dans le foyer'));
  var step=mk('div','stepper');
  var sm=mk('button','step-btn','−');sm.type='button';
  var sv=mk('div','step-val',String(S.personnes));
  var sp2=mk('button','step-btn','+');sp2.type='button';
  sm.addEventListener('click',function(){if(S.personnes>1){S.personnes--;sv.textContent=String(S.personnes);updatePrev();}});
  sp2.addEventListener('click',function(){if(S.personnes<10){S.personnes++;sv.textContent=String(S.personnes);updatePrev();}});
  ap(step,sm);ap(step,sv);ap(step,sp2);ap(hW,step);ap(gH,hW);

  var rW=mk('div');ap(rW,mk('label',null,'Revenu fiscal de référence (RFR)'));
  var rI=document.createElement('input');rI.type='text';rI.inputMode='numeric';
  rI.value=S.rfr>0?fmtNum(S.rfr)+' EUR':'';
  rI.addEventListener('focus',function(){
    rI.value=S.rfr>0?String(S.rfr):'';
  });
  rI.addEventListener('input',function(){
    var brut=rI.value.replace(/[^0-9]/g,'');
    S.rfr=parseInt(brut)||0;
    rI.value=brut;
    updatePrev();
  });
  rI.addEventListener('blur',function(){
    rI.value=S.rfr>0?fmtNum(S.rfr)+' EUR':'';
  });
  ap(rW,rI);ap(gH,rW);ap(s1,gH);
  ap(s1,mk('div','hint','RFR de l\'ensemble du foyer (avis d\'imposition, année N-1)'));

  var acW=mk('div');acW.style.marginTop='14px';
  ap(acW,mk('label',null,'Année de construction'));
  var acS=document.createElement('select');
  [['2025','Neuf / moins de 2 ans'],['2018','2018 — 2024'],['2010','2010 — 2017'],['2000','2000 — 2009'],['1990','1990 — 1999'],['1975','1975 — 1989'],['1960','Avant 1975']
  ].forEach(function(o){var op=document.createElement('option');op.value=o[0];op.textContent=o[1];if(parseInt(o[0])===S.annee_construction)op.selected=true;acS.appendChild(op);});
  acS.onchange=function(){S.annee_construction=parseInt(acS.value)||2000;if(!S.dpe_confirmed){S.dpe=estimDPE(S.annee_construction);majDpe();}updatePrev();};
  ap(acW,acS);ap(acW,mk('div','hint','Logement de plus de 15 ans requis pour MaPrimeRénov\''));ap(s1,acW);

  var dpeW=mk('div');dpeW.style.marginTop='14px';ap(dpeW,mk('label',null,'Classe énergétique DPE'));
  if(!S.dpe_confirmed)S.dpe=estimDPE(S.annee_construction);
  var dpeRow=mk('div','dpe-row');
  var dpeInfo=mk('div','dpe-info');
  function majDpe(){
    dpeInfo.textContent='Classe '+S.dpe+' — '+(DPE_THERM[S.dpe]||190)+' kWh/m²/an'+((S.dpe==='F'||S.dpe==='G')?' — Passoire thermique (bonus sortie passoire éligible)':'');
    dpeRow.querySelectorAll('.dpe-btn').forEach(function(x){x.className='dpe-btn'+(x.textContent.trim()===S.dpe?' on':'');});
  }
  ['A','B','C','D','E','F','G'].forEach(function(cls){
    var b=mk('button','dpe-btn'+(S.dpe===cls?' on':''),cls);b.type='button';b.style.background=DPE_COL[cls];b.style.color=cls==='D'?'#333':'#fff';
    b.addEventListener('click',function(){S.dpe=cls;S.dpe_confirmed=true;majDpe();updatePrev();});
    ap(dpeRow,b);
  });
  majDpe();
  ap(dpeW,dpeRow);ap(dpeW,dpeInfo);ap(s1,dpeW);ap(left,s1);

  /* S2: Parcours + Travaux */
  var s2=mk('div','sc');ap(s2,mkTit('bolt','Votre projet de rénovation'));
  ap(s2,mk('label',null,'Type de parcours'));
  var pTog=mk('div','tog');
  var pG=mk('button','tbtn'+(S.parcours==='geste'?' on':''),'🔧 Par geste');
  var pA=mk('button','tbtn'+(S.parcours==='ampleur'?' on':''),'🏗️ Rénovation d\'ampleur');
  pG.addEventListener('click',function(){S.parcours='geste';pG.className='tbtn on';pA.className='tbtn';updatePrev();});
  pA.addEventListener('click',function(){S.parcours='ampleur';pA.className='tbtn on';pG.className='tbtn';updatePrev();});
  ap(pTog,pG);ap(pTog,pA);ap(s2,pTog);
  ap(s2,mk('div','hint','Par geste : 1 ou plusieurs travaux ciblés. Rénovation d\'ampleur : bouquet de travaux avec gain DPE ≥2 classes.'));

  var travW=mk('div');travW.style.marginTop='14px';ap(travW,mk('label',null,'Travaux envisagés'));
  var opts=mk('div','opts');
  TRAVAUX_LIST.forEach(function(e){
    var on = S.travaux.indexOf(e[0])>-1;
    var b=mk('button','obtn'+(on?' on':''),e[1]);b.type='button';
    b.addEventListener('click',function(){
      var i=S.travaux.indexOf(e[0]);
      if(i>-1)S.travaux.splice(i,1);else S.travaux.push(e[0]);
      b.className='obtn'+(S.travaux.indexOf(e[0])>-1?' on':'');
      updatePrev();
    });
    ap(opts,b);
  });
  ap(travW,opts);ap(s2,travW);

  var surfW=mk('div');surfW.style.marginTop='14px';
  ap(surfW,mk('label',null,'Surface à isoler (m²) — si isolation sélectionnée'));
  var surfI=document.createElement('input');surfI.type='number';surfI.value=S.surface_isol;surfI.min=5;surfI.max=300;surfI.step=5;
  surfI.addEventListener('input',function(){S.surface_isol=parseInt(surfI.value)||30;updatePrev();});
  ap(surfW,surfI);ap(s2,surfW);ap(left,s2);

  /* CTA */
  var ctaBtn=mk('button','cta-btn');ctaBtn.innerHTML='<span>Voir mes aides &gt;</span>';
  ctaBtn.addEventListener('click',function(){
    if(!S.cp||S.cp.length<5){
      adSt.textContent='⚠️ Sélectionnez votre adresse dans la liste ou utilisez la géolocalisation 📍';
      adSt.style.display='block';adSt.style.color='#dc2626';adI.style.borderColor='#dc2626';adI.focus();
      document.getElementById(UID).scrollIntoView({behavior:'smooth',block:'start'});return;
    }
    if(S.travaux.length===0){
      adSt.textContent='⚠️ Sélectionnez au moins un type de travaux';
      adSt.style.display='block';adSt.style.color='#dc2626';return;
    }
    adSt.style.display='none';adI.style.borderColor='';
    ctaBtn.innerHTML='<span>Calcul...</span>';ctaBtn.disabled=true;
    setTimeout(function(){showResults();ctaBtn.innerHTML='<span>Voir mes aides &gt;</span>';ctaBtn.disabled=false;},700);
  });
  ap(left,ctaBtn);

  /* DROITE */
  var prev=mk('div','aid-prev');ap(prev,mk('div','prev-title','💰 Estimation en direct'));
  var pg=mk('div','prev-grid');
  function mkPV(id,lbl){var c=mk('div','prev-card');var v=mk('div','prev-val','—');v.id=UID+'-p-'+id;ap(c,v);ap(c,mk('div','prev-lbl',lbl));ap(pg,c);}
  mkPV('budget','Budget travaux');mkPV('total','Total aides');mkPV('reste','Reste à charge');
  var badge=mk('div','profil-badge');badge.id=UID+'-profil-badge';ap(prev,badge);
  ap(prev,pg);ap(right,prev);

  var recap=mk('div','recap');ap(recap,mk('div','recap-title','📋 Récapitulatif'));
  [['adr','📍 Adresse'],['zone','🗺️ Zone'],['foyer','👥 Foyer'],['statut','🏠 Statut'],['dpe','🏷️ DPE'],['parcours','🔧 Parcours'],['travaux','📦 Travaux']
  ].forEach(function(r){var row=mk('div','ri');ap(row,mk('div','ri-lbl',r[1]));var v=mk('div','ri-val ri-empty','—');v.id=UID+'-r-'+r[0];ap(row,v);ap(recap,row);});
  ap(right,recap);ap(body,left);ap(body,right);ap(root,body);
  updatePrev();
}

/* ── Résultats ────────────────────────────────────────────────────────────── */
var _R=null;
function showResults(){
  var el=document.getElementById(UID+'-res');if(!el)return;
  _R=calcAll();el.innerHTML='';el.className='results show';

  var hero=mk('div','res-hero');
  var titleEl=mk('div','res-title','Vos aides à la rénovation énergétique');ap(hero,titleEl);
  ap(hero,mk('div','res-sub','Profil '+_R.profil_lbl+' — Parcours '+(S.parcours==='ampleur'?'Rénovation d\'ampleur':'Par geste')));
  ap(el,hero);

  var cards=mk('div','res-cards');
  [{ico:'💰',v:fmtNum(_R.budget)+'€',l:'Budget travaux'},
   {cls:'eco',ico:'🏛️',v:fmtNum(_R.mpr)+'€',l:'MaPrimeRénov\''},
   {cls:'eco',ico:'⚡',v:fmtNum(_R.cee)+'€',l:'CEE'},
   {cls:'eco',ico:'🧾',v:fmtNum(_R.eco_tva)+'€',l:'Économie TVA'},
   {ico:'📊',v:_R.taux_couverture+'%',l:'Couvert par aides'},
   {ico:'💳',v:fmtNum(_R.reste_a_charge)+'€',l:'Reste à charge'}
  ].forEach(function(it){var c=mk('div','rcard '+(it.cls||''));ap(c,mk('div','rcard-ico',it.ico));ap(c,mk('div','rcard-val',it.v));ap(c,mk('div','rcard-lbl',it.l));ap(cards,c);});
  ap(el,cards);

  var aSc=mk('div','sc');aSc.style.marginBottom='12px';
  ap(aSc,mkTit('euro','Détail des aides mobilisables'));

  var aidesData=[
    {nom:'MaPrimeRénov\' ('+_R.profil_lbl+')',montant:_R.mpr,eligible:_R.mpr>0,detail:S.parcours==='ampleur'?'Rénovation d\'ampleur — % du montant HT selon profil':'Parcours par geste — forfaits cumulés',cond:'Anah — maprimerenov.gouv.fr'},
    {nom:'Certificats d\'Économie d\'Énergie (CEE)',montant:_R.cee,eligible:_R.cee>0,detail:'Versé par les fournisseurs d\'énergie, cumulable en parcours par geste',cond:S.parcours==='ampleur'?'Non cumulable en rénovation d\'ampleur':'Cumulable avec MaPrimeRénov\''},
    {nom:'TVA réduite à 5,5%',montant:_R.eco_tva,eligible:_R.eco_tva>0,detail:'Appliquée automatiquement sur la facture (au lieu de 20%)',cond:'Logement de plus de 2 ans'},
    {nom:'Éco-PTZ (prêt à taux zéro)',montant:_R.eco_ptz_montant,eligible:_R.eco_ptz_eligible,type:'pret',detail:'Jusqu\'à 50 000€ à taux 0%, sans condition de revenus',cond:_R.eco_ptz_eligible?'Éligible — via votre banque':'Non éligible (locataire ou reste à charge nul)'},
    {nom:_R.aide_locale_nom||'Aides régionales & locales',montant:_R.aide_locale,eligible:_R.aide_locale>0,detail:'Montant indicatif, sous conditions de ressources',cond:'France Rénov\' — 0 800 321 321'}
  ];

  aidesData.forEach(function(a){
    var row=mk('div','aide-row');
    var ico=mk('div','aide-ico');
    ico.textContent=a.eligible?'✓':'✗';
    ico.style.background=a.eligible?'#dcfce7':'#f3f4f6';
    ico.style.color=a.eligible?'#166534':'#9ca3af';
    var info=mk('div');info.style.cssText='flex:1;min-width:0';
    ap(info,mk('div','aide-nom',a.nom));ap(info,mk('div','aide-det',a.detail));
    ap(info,mk('div','aide-cond'+(a.eligible?'':' no'),a.cond));
    var amt=mk('div','aide-amt');
    if(a.eligible && a.montant>0){amt.textContent=(a.type==='pret'?'Prêt : ':'+')+fmtNum(a.montant)+'€';amt.style.color=a.type==='pret'?'#1d4ed8':'#16a34a';}
    else{amt.textContent='—';amt.style.color='#9ca3af';}
    ap(row,ico);ap(row,info);ap(row,amt);ap(aSc,row);
  });

  var bS=mk('div','budget-summ');
  [['Budget travaux TTC',fmtNum(_R.budget)+'€','#6b7280'],
   ['Total aides mobilisables','−'+fmtNum(_R.total_aides)+'€','#16a34a']
  ].forEach(function(r){var row=mk('div','bs-row');var l=mk('span',null,r[0]);l.style.color=r[2];var v=mk('span',null,r[1]);v.style.fontWeight='600';ap(row,l);ap(row,v);ap(bS,row);});
  var nR=mk('div','bs-net');
  var nl=mk('div',null,'Reste à charge estimé');nl.style.cssText='font-size:13px;font-weight:700;color:#92400e';
  var nv=mk('div',null,fmtNum(_R.reste_a_charge)+'€');nv.style.cssText='font-size:19px;font-weight:800;color:#92400e';
  ap(nR,nl);ap(nR,nv);ap(bS,nR);ap(aSc,bS);ap(el,aSc);

  var pdfBtn=mk('button','pdf-btn');pdfBtn.type='button';pdfBtn.innerHTML='📄 Télécharger mon estimation PDF';
  pdfBtn.addEventListener('click',function(){
    pdfBtn.innerHTML='⏳ Génération en cours...';pdfBtn.disabled=true;
    genererPDF(S,_R,aidesData).then(function(){
      pdfBtn.innerHTML='✅ PDF téléchargé !';
      setTimeout(function(){pdfBtn.innerHTML='📄 Télécharger mon estimation PDF';pdfBtn.disabled=false;},3000);
    }).catch(function(err){
      console.error('[CME PDF]',err.message||err);
      pdfBtn.innerHTML='❌ Erreur — F12 console';pdfBtn.disabled=false;
      setTimeout(function(){pdfBtn.innerHTML='📄 Télécharger mon estimation PDF';},4000);
    });
  });
  ap(el,pdfBtn);

  var cta2=mk('div','cta2');
  ap(cta2,mk('h3',null,'🏗️ Obtenez votre devis gratuit'));
  ap(cta2,mk('p',null,'Un conseiller France Rénov\' partenaire monte votre dossier et vous accompagne — sans engagement'));
  var cb=mk('button','cta2-btn','Demander mon accompagnement >');
  cb.addEventListener('click',function(){openLeadModal({
    profil:_R.profil_lbl, travaux:S.travaux.join(', '),
    montant_mpr:_R.mpr, montant_cee:_R.cee, total_aides:_R.total_aides,
    budget:_R.budget, reste_a_charge:_R.reste_a_charge
  });});
  ap(cta2,cb);ap(el,cta2);

  ap(el,mk('div','fnote','* Estimation non contractuelle basée sur le barème Anah 2026 (circulaire du 1er décembre 2025). Montants indicatifs : vérifiez votre éligibilité exacte sur maprimerenov.gouv.fr ou france-renov.gouv.fr.'));
  var nr=mk('button','new-sim','🔄 Nouvelle simulation');
  nr.addEventListener('click',function(){el.innerHTML='';el.className='results';window.scrollTo({top:document.getElementById(UID).offsetTop-10,behavior:'smooth'});});
  ap(el,nr);
  el.scrollIntoView({behavior:'smooth',block:'start'});
}

/* ── Modal Lead ───────────────────────────────────────────────────────────── */
var LEAD_CTX=null;
function openLeadModal(ctx){
  LEAD_CTX=ctx;
  var ov=document.getElementById(UID+'-lmodal');if(!ov)return;
  var summ=document.getElementById(UID+'-lm-summ');
  if(summ){
    summ.innerHTML='<div style="font-weight:600;font-size:15px;color:#111827">Profil '+ctx.profil+'</div>'
      +'<div style="display:flex;gap:16px;margin-top:10px;padding-top:10px;border-top:1px solid #fde68a">'
      +'<div><div style="font-size:18px;font-weight:700;color:#92400e">'+fmtNum(ctx.total_aides)+'€</div><div style="font-size:11px;color:#9ca3af">aides totales</div></div>'
      +'<div><div style="font-size:18px;font-weight:700;color:#111827">'+fmtNum(ctx.reste_a_charge)+'€</div><div style="font-size:11px;color:#9ca3af">reste à charge</div></div>'
      +'</div>';
  }
  var err=document.getElementById(UID+'-lm-err');if(err)err.style.display='none';
  var subb=document.getElementById(UID+'-lm-sub');if(subb){subb.disabled=false;subb.textContent='Envoyer ma demande →';}
  ov.className='lmodal-ov open';document.body.style.overflow='hidden';
}
function closeLeadModal(){var ov=document.getElementById(UID+'-lmodal');if(ov){ov.className='lmodal-ov';document.body.style.overflow='';}}
function submitLead(){
  var g=function(id){return document.getElementById(UID+'-'+id);};
  var prn=(g('lm-prn')||{}).value||'',nom=(g('lm-nom')||{}).value||'';
  var mail=(g('lm-mail')||{}).value||'',tel=(g('lm-tel')||{}).value||'';
  var rgpd=g('lm-rgpd')&&g('lm-rgpd').checked;
  var err=g('lm-err');
  if(!prn.trim()||!nom.trim()||!mail.trim()||!tel.trim()||!rgpd){if(err)err.style.display='block';return;}
  if(err)err.style.display='none';
  var sub=g('lm-sub');if(sub){sub.disabled=true;sub.textContent='Envoi en cours...';}
  var data=Object.assign({prenom:prn.trim(),nom:nom.trim(),email:mail.trim(),telephone:tel.trim(),adresse:S.adresse,src_post:new URLSearchParams(window.location.search).get('src_post')||''},LEAD_CTX);
  showLeadSuccess();
  var fd=new FormData();fd.append('action','cme_aid_lead');fd.append('nonce',AIDNONCE);fd.append('payload',JSON.stringify(data));
  fetch(AJAX_URL,{method:'POST',body:fd}).then(function(r){return r.json();})
    .then(function(res){console.log('[CME Aides Lead]',res);}).catch(function(err){console.warn('[CME Aides Lead] Erreur:',err);});
}
function showLeadSuccess(){
  var form=document.getElementById(UID+'-lmform');
  if(form){
    var prn=(document.getElementById(UID+'-lm-prn')||{}).value||'';
    var nom=(document.getElementById(UID+'-lm-nom')||{}).value||'';
    var mail=(document.getElementById(UID+'-lm-mail')||{}).value||'';
    var tel=(document.getElementById(UID+'-lm-tel')||{}).value||'';
    var srcPost=new URLSearchParams(window.location.search).get('src_post')||'';
    var ctx=LEAD_CTX||{};
    var leadData={
      tool:'aides-renovation',
      source_post_id:srcPost,
      montant_estime:ctx.total_aides||0,
      economie_estimee:0,
      details:{profil:ctx.profil||'',travaux:ctx.travaux||'',montant_mpr:ctx.montant_mpr||0,montant_cee:ctx.montant_cee||0,reste_a_charge:ctx.reste_a_charge||0,budget:ctx.budget||0}
    };
    var lienCompte='https://espace-client.comprendre-mon-energie.fr/register?prenom='
      +encodeURIComponent(prn)+'&nom='+encodeURIComponent(nom)+'&email='+encodeURIComponent(mail)+'&telephone='+encodeURIComponent(tel)
      +'&lead_data='+encodeURIComponent(JSON.stringify(leadData));
    form.innerHTML='<div style="text-align:center;padding:20px 10px"><div style="width:52px;height:52px;border-radius:50%;background:#dcfce7;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">✓</div><div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoyée !</div><div style="font-size:13px;color:#6b7280;line-height:1.5">Un conseiller vous recontacte sous 48h.</div>'
      +'<a href="'+lienCompte+'" target="_blank" style="display:inline-block;margin-top:16px;background:#f59e0b;color:#fff;font-weight:600;padding:12px 24px;border-radius:10px;text-decoration:none;font-size:14px">Créer mon espace client &rarr;</a></div>';
  }
  setTimeout(closeLeadModal,6000);
}
function buildLeadModal(root){
  var ov=mk('div','lmodal-ov');ov.id=UID+'-lmodal';
  var box=mk('div','lmodal-box');
  var head=mk('div','lmodal-head');
  ap(head,mk('div',null,'📩 Recevoir mon accompagnement'));
  var sub=mk('div');sub.style.cssText='font-size:12px;color:#fff;opacity:.85;font-weight:400;margin-top:2px';
  sub.textContent='Un conseiller France Rénov\' confirme votre éligibilité';ap(head,sub);
  var cls=mk('button','lmodal-close','×');cls.type='button';cls.onclick=closeLeadModal;ap(head,cls);ap(box,head);
  var summ=mk('div','lmodal-summ');summ.id=UID+'-lm-summ';ap(box,summ);
  var form=mk('div');form.id=UID+'-lmform';
  var row1=mk('div','lmfrow');
  var fPrn=mk('input','lmfi');fPrn.id=UID+'-lm-prn';fPrn.type='text';fPrn.placeholder='Prénom *';
  var fNom=mk('input','lmfi');fNom.id=UID+'-lm-nom';fNom.type='text';fNom.placeholder='Nom *';
  ap(row1,fPrn);ap(row1,fNom);ap(form,row1);
  var fMail=mk('input','lmfi');fMail.id=UID+'-lm-mail';fMail.type='email';fMail.placeholder='Email *';fMail.style.marginTop='10px';ap(form,fMail);
  var fTel=mk('input','lmfi');fTel.id=UID+'-lm-tel';fTel.type='tel';fTel.placeholder='Téléphone *';fTel.style.marginTop='10px';ap(form,fTel);
  var rgpd=mk('label','lmrgpd');
  var chk=document.createElement('input');chk.type='checkbox';chk.id=UID+'-lm-rgpd';
  var txt=mk('span');txt.innerHTML='J\'accepte que mes données soient transmises pour être recontacté, conformément à notre <a href="https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/" target="_blank" style="color:#f59e0b">politique de confidentialité</a>.';
  ap(rgpd,chk);ap(rgpd,txt);ap(form,rgpd);
  var err=mk('div','lmferr','⚠️ Merci de remplir tous les champs et d\'accepter la politique de confidentialité.');err.id=UID+'-lm-err';ap(form,err);
  var subb=mk('button','lmodal-sub','Envoyer ma demande →');subb.id=UID+'-lm-sub';subb.type='button';subb.onclick=submitLead;ap(form,subb);
  ap(box,form);
  ov.addEventListener('click',function(e){if(e.target===ov)closeLeadModal();});
  ap(ov,box);ap(root,ov);
}

/* ── PDF (moteur jsPDF identique au solaire, thème ambre) ────────────────── */
var PDF_LEGAL = [
  'POLITIQUE DE CONFIDENTIALITE (RGPD)', '',
  'Comprendre Mon Energie s\'engage en faveur de la protection de vos donnees personnelles.',
  'En application du RGPD, nous vous communiquons les conditions dans lesquelles vos donnees',
  'personnelles sont traitees par nos soins.', '',
  'DONNEES COLLECTEES : coordonnees (nom, prenom, telephone, email), preferences,',
  'informations techniques et de localisation. Aucune donnee sensible n\'est collectee.', '',
  'FONDEMENTS JURIDIQUES : consentement (art. 6.1.a RGPD), execution d\'un contrat,',
  'interet legittime (art. 6.1.e RGPD), obligation legale.', '',
  'DUREE DE CONSERVATION : 3 ans a compter de la collecte, sauf obligations legales.', '',
  'VOS DROITS : rectification, effacement, limitation, portabilite, opposition,',
  'retrait du consentement, plainte aupres de la CNIL.',
  'Contact DPO : contact@comprendre-mon-energie.fr',
  'CNIL - 3 Place de Fontenoy - TSA 80715 - 75334 Paris Cedex 07', '',
  'MENTIONS LEGALES', '',
  'Editeur : Comprendre Mon Energie',
  'Capital : 5 000 EUR | ICE : 003941396000038',
  'Siege social : 61 rue de Lyon - 75012 Paris',
  'Directeur de la publication : Blal Oussama',
  'Email : contact@comprendre-mon-energie.fr',
  'Site : https://www.comprendre-mon-energie.fr', '',
  'Hebergeur : O2switch - Clermont-Ferrand - Capital 100 000 EUR',
  'Tel : +33 4 44 44 60 40 | support@o2switch.fr', '',
  'SOURCE DU BAREME',  '',
  'Circulaire relative aux plafonds de ressources applicables en 2026 (Anah),',
  'NOR VLOL2534404C du 1er decembre 2025. Plafonds en vigueur au 1er janvier 2026.',
  'Consultez france-renov.gouv.fr pour la simulation officielle et a jour.'
];

async function genererPDF(S, R, aidesData) {
  var _w = 0;
  while (!window.jspdf && _w < 80) { await new Promise(function(r){setTimeout(r,100);}); _w++; }
  if (!window.jspdf) {
    await new Promise(function(resolve,reject){
      var s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
      var t=setTimeout(function(){reject(new Error('CDN timeout'));},10000);
      s.onload=function(){clearTimeout(t);resolve();};s.onerror=function(){clearTimeout(t);reject(new Error('CDN erreur'));};
      document.head.appendChild(s);
    });
  }
  if (!window.jspdf) throw new Error('jsPDF non disponible');
  var jsPDF=window.jspdf.jsPDF;
  var doc=new jsPDF({unit:'mm',format:'a4',orientation:'portrait'});
  var PW=210,PH=297,MAR=15,CW=180;
  var AMB=[180,83,9],DRK=[17,24,39],GRY=[107,114,128],LGT=[243,244,246];
  var today=new Date().toLocaleDateString('fr-FR');
  var pageNum=0;

  var logoB64=null,logoW=42,logoH=14;
  try{
    var fd=new FormData();fd.append('action','cme_aid_logo_b64');
    var lr=await fetch(AJAX_URL,{method:'POST',body:fd});var ld=await lr.json();
    if(ld.success){logoB64=ld.data.b64;
      await new Promise(function(res){var tmpI=new Image();tmpI.onload=function(){if(tmpI.naturalWidth>0)logoH=logoW*tmpI.naturalHeight/tmpI.naturalWidth;res();};tmpI.onerror=res;tmpI.src=logoB64;});
    }
  }catch(e){}

  function newPage(titre){
    if(pageNum>0)doc.addPage();pageNum++;
    doc.setFillColor(AMB[0],AMB[1],AMB[2]);doc.rect(0,0,PW,22,'F');
    if(logoB64){
      try{var lW=Math.min(logoW,19);var lH=Math.min(logoH,10);var lY=(22-lH)/2;
        doc.setFillColor(255,255,255);doc.roundedRect(MAR-2,lY-2,lW+4,lH+4,2,2,'F');
        doc.addImage(logoB64,'PNG',MAR,lY,lW,lH);
      }catch(e){doc.setTextColor(255,255,255);doc.setFontSize(10);doc.setFont('helvetica','bold');doc.text('CME',MAR,12);}
    }
    if(titre){doc.setTextColor(255,255,255);doc.setFontSize(10);doc.setFont('helvetica','bold');doc.text(titre,PW-MAR,13,{align:'right'});}
    doc.setFillColor(AMB[0],AMB[1],AMB[2]);doc.rect(0,PH-14,PW,14,'F');
    doc.setTextColor(255,255,255);doc.setFontSize(8.5);doc.setFont('helvetica','normal');
    doc.text('comprendre-mon-energie.fr  |  contact@comprendre-mon-energie.fr  |  61 rue de Lyon 75012 Paris',PW/2,PH-6,{align:'center'});
    doc.text('Page '+pageNum,PW-MAR,PH-6,{align:'right'});
    return 30;
  }
  function sectTitle(label,y){
    doc.setFillColor(LGT[0],LGT[1],LGT[2]);doc.rect(MAR,y-5,CW,9,'F');
    doc.setDrawColor(AMB[0],AMB[1],AMB[2]);doc.rect(MAR,y-5,3,9,'F');
    doc.setTextColor(AMB[0],AMB[1],AMB[2]);doc.setFontSize(10);doc.setFont('helvetica','bold');
    doc.text(label,MAR+6,y+1);return y+8;
  }
  function row(lbl,val,y,bold){
    doc.setTextColor(107,114,128);doc.setFontSize(8.5);doc.setFont('helvetica','normal');
    var lbl2=doc.splitTextToSize(String(lbl||''),68);doc.text(lbl2,MAR+4,y);
    doc.setTextColor(17,24,39);doc.setFontSize(8.5);doc.setFont('helvetica',bold?'bold':'normal');
    var val2=doc.splitTextToSize(String(val||'-'),88);doc.text(val2,MAR+76,y);
    return y+Math.max(lbl2.length,val2.length)*5+1;
  }
  function bigKPI(label,val,unit,x,y,col){
    var c=col||AMB;var bW=72,bH=30;
    doc.setFillColor(255,255,255);doc.setDrawColor(c[0],c[1],c[2]);doc.setLineWidth(0.8);
    doc.roundedRect(x,y,bW,bH,3,3,'FD');var cx=x+bW/2;
    doc.setTextColor(c[0],c[1],c[2]);doc.setFontSize(15);doc.setFont('helvetica','bold');
    doc.text(String(val||''),cx,y+11,{align:'center',maxWidth:bW-8});
    doc.setTextColor(107,114,128);doc.setFontSize(8);doc.setFont('helvetica','normal');
    doc.text(String(unit||''),cx,y+18,{align:'center',maxWidth:bW-8});
    doc.setFontSize(8);doc.setFont('helvetica','bold');doc.setTextColor(17,24,39);
    doc.text(String(label||''),cx,y+26,{align:'center',maxWidth:bW-8});
    return y+bH+5;
  }

  // PAGE 1 — COUVERTURE
  doc.setFillColor(AMB[0],AMB[1],AMB[2]);doc.rect(0,0,PW,PH,'F');
  doc.setFillColor(255,255,255);doc.roundedRect(MAR,40,CW,168,5,5,'F');
  if(logoB64){try{var cW=20,cH=Math.min(14,cW*logoH/logoW),cX=PW/2-cW/2;
    doc.setFillColor(255,255,255);doc.roundedRect(cX-4,4,cW+8,cH+8,3,3,'F');
    doc.addImage(logoB64,'PNG',cX,8,cW,cH);}catch(e){}}
  doc.setTextColor(255,255,255);doc.setFontSize(22);doc.setFont('helvetica','bold');
  doc.text('Estimation de vos aides '+new Date().getFullYear(),PW/2,34,{align:'center'});
  doc.setTextColor(AMB[0],AMB[1],AMB[2]);doc.setFontSize(14);doc.setFont('helvetica','bold');
  doc.text('R\u00e9novation \u00c9nerg\u00e9tique',PW/2,55,{align:'center'});
  doc.setDrawColor(AMB[0],AMB[1],AMB[2]);doc.setLineWidth(0.5);doc.line(MAR+10,59,PW-MAR-10,59);
  if(S.adresse){doc.setTextColor(DRK[0],DRK[1],DRK[2]);doc.setFontSize(11);doc.setFont('helvetica','normal');
    doc.text(doc.splitTextToSize(S.adresse,CW-20),PW/2,67,{align:'center'});}
  doc.setTextColor(GRY[0],GRY[1],GRY[2]);doc.setFontSize(9);doc.text('Document genere le '+today,PW/2,80,{align:'center'});

  var bX1=MAR+18,bX2=MAR+18+72+10,bY1=98,bY2=bY1+35;
  bigKPI('MaPrimeRenov',fmtNum(R.mpr)+' EUR','profil '+R.profil,bX1,bY1,[22,163,74]);
  bigKPI('CEE + TVA',fmtNum(R.cee+R.eco_tva)+' EUR','aides cumulees',bX2,bY1,[37,99,235]);
  bigKPI('Total aides',fmtNum(R.total_aides)+' EUR','sur '+fmtNum(R.budget)+' EUR',bX1,bY2,AMB);
  bigKPI('Reste a charge',fmtNum(R.reste_a_charge)+' EUR',R.taux_couverture+'% couvert',bX2,bY2,[239,68,68]);
  doc.setTextColor(107,114,128);doc.setFontSize(7.5);doc.setFont('helvetica','normal');
  doc.text('Source: Bareme Anah 2026 - Circulaire du 1er decembre 2025',PW/2,bY2+40,{align:'center'});

  doc.setFillColor(255,255,255);doc.rect(0,PH-34,PW,34,'F');
  doc.setDrawColor(AMB[0],AMB[1],AMB[2]);doc.setLineWidth(0.3);doc.line(MAR+10,PH-34,PW-MAR-10,PH-34);
  doc.setTextColor(107,114,128);doc.setFontSize(7.5);
  doc.text('Estimation basee sur votre profil et vos travaux declares',PW/2,PH-26,{align:'center'});
  doc.setTextColor(AMB[0],AMB[1],AMB[2]);doc.setFontSize(8);doc.setFont('helvetica','normal');
  doc.text('www.comprendre-mon-energie.fr',PW/2,PH-12,{align:'center'});
  doc.setTextColor(107,114,128);
  doc.text('contact@comprendre-mon-energie.fr  -  61 rue de Lyon 75012 Paris',PW/2,PH-6,{align:'center'});
  pageNum=1;

  // PAGE 2 — PROFIL & LOGEMENT
  var y=newPage('Votre Profil');
  y=sectTitle('FOYER & LOGEMENT',y);
  y=row('Adresse',S.adresse||'-',y);
  y=row('Zone',(function(){var r=getRegionNom(S.cp);return r?r.replace('Île-de-France','Ile-de-France'):(S.idf?'Ile-de-France':'Hors Ile-de-France');})(),y);
  y=row('Personnes au foyer',String(S.personnes),y);
  y=row('Revenu fiscal de reference',fmtNum(S.rfr)+' EUR',y,true);
  y=row('Profil MaPrimeRenov',R.profil_lbl,y,true);
  y=row('Statut',S.statut==='proprio'?'Proprietaire':'Locataire',y);
  y=row('Annee construction',String(S.annee_construction),y);
  y=row('DPE actuel',S.dpe,y);
  y+=4;
  y=sectTitle('PROJET DE RENOVATION',y);
  y=row('Parcours',S.parcours==='ampleur'?'Renovation d\'ampleur':'Par geste',y,true);
  y=row('Travaux envisages',S.travaux.length+' geste(s)',y);
  y+=4;
  y=sectTitle('BAREME DE REFERENCE (Zone '+(S.idf?'IDF':'Hors IDF')+')',y);
  var s=seuils(S.personnes,S.idf);
  y=row('Plafond tres modeste',fmtNum(s.tm)+' EUR',y);
  y=row('Plafond modeste',fmtNum(s.mo)+' EUR',y);
  y=row('Plafond intermediaire',fmtNum(s.it)+' EUR',y);

  // PAGE 3 — DETAIL AIDES
  y=newPage('Detail des Aides');
  y=sectTitle('AIDES MOBILISABLES',y);
  aidesData.forEach(function(a){
    y=row(a.nom, a.eligible?fmtNum(a.montant)+' EUR':'Non eligible', y, a.eligible);
    y=row('  Condition',a.cond,y);
  });
  y+=6;
  doc.setFillColor(254,243,199);doc.setDrawColor(AMB[0],AMB[1],AMB[2]);doc.setLineWidth(0.5);
  doc.roundedRect(MAR,y-4,CW,16,3,3,'FD');
  doc.setTextColor(DRK[0],DRK[1],DRK[2]);doc.setFontSize(12);doc.setFont('helvetica','bold');
  doc.text('RESTE A CHARGE ESTIME : '+fmtNum(R.reste_a_charge)+' EUR',PW/2,y+6,{align:'center'});
  y+=22;
  y=sectTitle('BUDGET GLOBAL',y);
  y=row('Budget travaux TTC',fmtNum(R.budget)+' EUR',y,true);
  y=row('Total aides mobilisables',fmtNum(R.total_aides)+' EUR',y,true);
  y=row('Taux de couverture',R.taux_couverture+'%',y);

  // PAGE 4 — MENTIONS LEGALES
  y=newPage('Mentions Legales');
  doc.setTextColor(DRK[0],DRK[1],DRK[2]);doc.setFontSize(8);doc.setFont('helvetica','normal');
  var legalY=y;
  PDF_LEGAL.forEach(function(line){
    if(legalY>PH-20)legalY=newPage('Mentions Legales (suite)');
    if(line.startsWith('POLITIQUE')||line.startsWith('MENTIONS')||line.startsWith('VOS DROITS')||line.startsWith('SOURCE')){
      legalY=sectTitle(line,legalY);
    } else if(line===''){legalY+=3;}
    else{doc.setTextColor(line.startsWith('-')?GRY[0]:DRK[0],line.startsWith('-')?GRY[1]:DRK[1],line.startsWith('-')?GRY[2]:DRK[2]);
      doc.setFont('helvetica',line.startsWith('  ')?'italic':'normal');
      var lines=doc.splitTextToSize(line,CW);doc.text(lines,MAR+4,legalY);legalY+=lines.length*4.5;}
  });

  var dateStr=new Date().toISOString().split('T')[0];
  try{
    var pdfBlob=doc.output('blob');var blobUrl=URL.createObjectURL(pdfBlob);
    var dlLink=document.createElement('a');dlLink.href=blobUrl;dlLink.download='Estimation-Aides-CME-'+dateStr+'.pdf';
    dlLink.style.display='none';document.body.appendChild(dlLink);dlLink.click();
    setTimeout(function(){document.body.removeChild(dlLink);URL.revokeObjectURL(blobUrl);},2000);
  }catch(saveErr){doc.save('Estimation-Aides-CME-'+dateStr+'.pdf');}
}

/* ── Init ─────────────────────────────────────────────────────────────────── */
function $(){return document.getElementById(UID);}
function render(){
  var root=$();if(!root)return;root.innerHTML='';
  buildForm(root);
  var res=mk('div','results');res.id=UID+'-res';ap(root,res);
}
(function(){
  var rootEl=$();
  if(rootEl&&rootEl.parentNode&&!document.getElementById(UID+'-lmodal')){
    buildLeadModal(rootEl.parentNode);
  }
})();
render();
})();
</script>
<?php
$html = ob_get_clean();
if (preg_match('/<script>(.*?)<\/script>/s', $html, $m)) {
  $html = preg_replace('/<script>.*?<\/script>/s', '', $html, 1);
  global $cme_aid_footer_scripts;
  if (!isset($cme_aid_footer_scripts)) $cme_aid_footer_scripts = array();
  $cme_aid_footer_scripts[] = $m[1];
  if (!has_action('wp_footer', 'cme_aid_print_footer_scripts')) {
    add_action('wp_footer', 'cme_aid_print_footer_scripts', 99);
  }
}
return $html;
}
endif;
add_shortcode('simulateur_aides','cme_aid_sc');
