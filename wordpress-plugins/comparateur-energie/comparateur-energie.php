<?php
/**
 * Plugin Name: CME Comparateur Énergie
 * Plugin URI:  https://www.comprendre-mon-energie.fr
 * Description: Comparateur gaz & électricité — v3.0 vanilla JS, design complet, zéro conflit WordPress
 * Version:     3.4.2
 * Author:      CME
 * License:     GPL-2.0+
 */
if(!defined('ABSPATH'))exit;
if(!function_exists('cme_cmp_get_gas_url')):
function cme_cmp_get_gas_url(){
  $db_url = get_option('cme_cmp_gas_url','');
  if($db_url) return $db_url;
  return (defined('CME_CMP_APPS_SCRIPT_URL') && CME_CMP_APPS_SCRIPT_URL) ? CME_CMP_APPS_SCRIPT_URL : '';
}
endif;

// ── Page de reglages admin (fallback si wp-config.php ne fonctionne pas) ─────
add_action('admin_menu', function(){
  add_options_page('CME Comparateur - Reglages','CME Comparateur','manage_options','cme-cmp-settings','cme_cmp_settings_page');
});
add_action('admin_init', function(){
  register_setting('cme_cmp_group','cme_cmp_gas_url', array('sanitize_callback'=>'esc_url_raw'));
});
function cme_cmp_settings_page(){
  $url = cme_cmp_get_gas_url();
  $ok  = !empty($url);
  ?>
  <div class="wrap">
    <h1>CME Comparateur - Reglages Google Sheets</h1>
    <?php if($ok): ?>
    <div class="notice notice-success"><p><strong>OK</strong> - URL configuree : <code><?php echo esc_html($url); ?></code></p></div>
    <?php else: ?>
    <div class="notice notice-error"><p><strong>URL manquante</strong> - Remplissez le champ ci-dessous.</p></div>
    <?php endif; ?>
    <form method="post" action="options.php">
      <?php settings_fields('cme_cmp_group'); ?>
      <table class="form-table">
        <tr><th>URL Apps Script (Leads Comparateur)</th><td>
          <input type="url" name="cme_cmp_gas_url" value="<?php echo esc_attr(get_option('cme_cmp_gas_url','')); ?>" class="regular-text" placeholder="https://script.google.com/macros/s/.../exec"/>
          <p class="description">URL /exec obtenue apres deploiement de cme-comparateur-leads.gs</p>
        </td></tr>
      </table>
      <p><input type="submit" class="button-primary" value="Enregistrer"/></p>
    </form>
  </div>
  <?php
}

if(!function_exists('cme_cmp_handle_lead')):
function cme_cmp_handle_lead(){
  if(!check_ajax_referer('cme_cmp_lead_nonce','nonce',false)){
    wp_send_json_error(array('msg'=>'Nonce invalide'));return;
  }
  $raw  = wp_unslash(isset($_POST['payload'])?$_POST['payload']:'');
  $data = json_decode($raw,true);
  if(!$data){wp_send_json_error(array('msg'=>'Payload invalide'));return;}

  $prenom = sanitize_text_field($data['prenom']??'');
  $nom    = sanitize_text_field($data['nom']??'');
  $email  = sanitize_email($data['email']??'');
  $tel    = sanitize_text_field($data['telephone']??'');
  $energie= sanitize_text_field($data['energie']??'');
  $fourn  = sanitize_text_field($data['fournisseur']??'');
  $offre  = sanitize_text_field($data['offre']??'');
  $prix   = intval($data['prix_annuel']??0);
  $eco    = intval($data['economie']??0);
  $kwh    = intval($data['kwh']??0);
  $opt    = sanitize_text_field($data['option_tarifaire']??'');
  $lien   = esc_url_raw($data['lien_offre']??'');
  $dest   = 'contact@comprendre-mon-energie.fr';

  $icon = ($energie==='gaz')?'\xF0\x9F\x94\xA5':'\xE2\x9A\xA1';
  $sujet = $icon.' Nouvelle demande comparateur — '.$prenom.' '.$nom.' — '.$fourn;

  $corps = '<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:580px;margin:auto">
    <div style="background:linear-gradient(135deg,#1e3a8a,#3b82f6);color:#fff;padding:20px 24px;border-radius:10px 10px 0 0">
      <h2 style="margin:0">'.$icon.' Nouvelle demande — Comparateur Energie</h2>
      <p style="margin:4px 0 0;opacity:.85;font-size:13px">'.date('d/m/Y H:i').'</p>
    </div>
    <div style="background:#fff;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 10px 10px;padding:20px 24px">
      <h3 style="color:#3b82f6;margin:0 0 12px">Contact</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
        <tr><td style="padding:6px;color:#6b7280;width:150px">Nom complet</td><td style="padding:6px;font-weight:600">'.$prenom.' '.$nom.'</td></tr>
        <tr><td style="padding:6px;color:#6b7280">Email</td><td style="padding:6px"><a href="mailto:'.$email.'" style="color:#3b82f6">'.$email.'</a></td></tr>
        <tr><td style="padding:6px;color:#6b7280">Telephone</td><td style="padding:6px"><a href="tel:'.$tel.'" style="color:#3b82f6">'.$tel.'</a></td></tr>
      </table>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 16px">
      <h3 style="color:#3b82f6;margin:0 0 12px">Offre selectionnee</h3>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:5px;color:#6b7280">Energie</td><td style="padding:5px;font-weight:600">'.ucfirst($energie).'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Fournisseur</td><td style="padding:5px;font-weight:600">'.$fourn.' — '.$offre.'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Option tarifaire</td><td style="padding:5px;font-weight:600">'.($opt==='hphc'?'Heures pleines/creuses':'Base').'</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Consommation</td><td style="padding:5px;font-weight:600">'.number_format($kwh,0,',',' ').' kWh/an</td></tr>
        <tr style="background:#eff6ff"><td style="padding:8px;color:#1d4ed8;font-weight:600">Prix annuel estime</td><td style="padding:8px;font-weight:700;color:#1d4ed8;font-size:16px">'.number_format($prix,0,',',' ').' EUR/an</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Economie estimee</td><td style="padding:5px;font-weight:600;color:#16a34a">'.number_format($eco,0,',',' ').' EUR/an</td></tr>
        <tr><td style="padding:5px;color:#6b7280">Lien offre</td><td style="padding:5px"><a href="'.$lien.'" style="color:#3b82f6">Voir loffre</a></td></tr>
      </table>
    </div>
  </body></html>';

  $headers = array('Content-Type: text/html; charset=UTF-8','From: Comparateur Energie <noreply@comprendre-mon-energie.fr>');
  $mail_ok = wp_mail($dest,$sujet,$corps,$headers);

  // Google Sheets via GAS dedie
  $gas_url = cme_cmp_get_gas_url();
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
      'tool' => 'comparateur-energie', 'prenom' => $prenom, 'nom' => $nom, 'email' => $email,
      'telephone' => $tel, 'montant_estime' => $prix, 'economie_estimee' => $eco,
      'details' => array('energie'=>$energie,'fournisseur'=>$fourn,'offre'=>$offre,'kwh'=>$kwh,'option_tarifaire'=>$opt,'lien_offre'=>$lien),
      'source_page' => 'comparateur-energie-electricite-gaz',
      'source_post_id' => sanitize_text_field($data['src_post'] ?? '')
    ))
  ));

  wp_send_json_success(array('status'=>'ok','email_sent'=>$mail_ok,'gas'=>$gas_result));
}
endif;
add_action('wp_ajax_cme_cmp_lead','cme_cmp_handle_lead');
add_action('wp_ajax_nopriv_cme_cmp_lead','cme_cmp_handle_lead');

if(!function_exists('cme_comp_sc')):
function cme_comp_sc($atts){
$atts=shortcode_atts(['energie'=>'dual'],$atts);
$eg=esc_attr($atts['energie']);
$uid='cme'.uniqid();
$cmp_nonce=wp_create_nonce('cme_cmp_lead_nonce');
$cmp_ajax=esc_js(admin_url('admin-ajax.php'));
ob_start();?>
<style>
#<?php echo $uid;?>{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:1400px;margin:0 auto;padding:.5rem 0;width:100%;overflow-x:hidden}
#<?php echo $uid;?> *{box-sizing:border-box;-webkit-text-size-adjust:100%}
#<?php echo $uid;?> .cc{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:1.25rem;margin-bottom:14px}
#<?php echo $uid;?> .g2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
#<?php echo $uid;?> .g3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
#<?php echo $uid;?> label{font-size:13px;color:#6b7280;display:block;margin-bottom:6px;font-weight:500}
#<?php echo $uid;?> input[type=text],#<?php echo $uid;?> select{border:1px solid #e5e7eb;border-radius:8px;padding:0 12px;height:44px;font-size:16px;background:#f9fafb;color:#111827;width:100%;-webkit-appearance:none;appearance:none;outline:none;font-family:inherit}
#<?php echo $uid;?> input[type=number]{border:1px solid #e5e7eb;border-radius:8px;padding:0 8px 0 12px;height:52px;font-size:16px;background:#f9fafb;color:#111827;width:100%;outline:none;font-family:inherit;-moz-appearance:textfield}
#<?php echo $uid;?> input[type=number]::-webkit-inner-spin-button{-webkit-appearance:inner-spin-button;opacity:1;width:36px;height:52px;cursor:pointer;background:#e5e7eb;border-left:1px solid #d1d5db;border-radius:0 8px 8px 0}
#<?php echo $uid;?> input[type=number]::-webkit-outer-spin-button{-webkit-appearance:inner-spin-button;opacity:1}
#<?php echo $uid;?> input[type=number]:focus{border-color:#3b82f6;background:#fff}
#<?php echo $uid;?> input[type=number]:focus::-webkit-inner-spin-button{background:#dbeafe}
#<?php echo $uid;?> input:focus,#<?php echo $uid;?> select:focus{border-color:#3b82f6;background:#fff}
#<?php echo $uid;?> .hint{font-size:12px;color:#9ca3af;margin-top:5px;line-height:1.4}
#<?php echo $uid;?> .stitle{font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.06em;margin-bottom:14px}
#<?php echo $uid;?> .tog{display:flex;gap:6px;flex-wrap:wrap}
#<?php echo $uid;?> .tbtn{flex:1;min-width:80px;height:44px;border:1px solid #e5e7eb;border-radius:10px;background:#f9fafb;color:#374151;font-size:13px;cursor:pointer;font-family:inherit;transition:all .15s;padding:0 8px;line-height:1.2}
#<?php echo $uid;?> .tbtn.on{border:1.5px solid #3b82f6;background:#eff6ff;color:#1d4ed8;font-weight:500}
#<?php echo $uid;?> .sbar{display:flex;align-items:center;gap:6px;margin-bottom:20px}
#<?php echo $uid;?> .sdot{width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;flex-shrink:0;border:1.5px solid #d1d5db;background:#f3f4f6;color:#9ca3af;transition:all .2s}
#<?php echo $uid;?> .sdot.done{border-color:#10b981;background:#d1fae5;color:#065f46}
#<?php echo $uid;?> .sdot.act{border-color:#3b82f6;background:#dbeafe;color:#1d4ed8}
#<?php echo $uid;?> .sline{flex:1;height:1px;background:#e5e7eb}
#<?php echo $uid;?> .slbl{font-size:12px;font-weight:500;color:#9ca3af;white-space:nowrap;transition:color .2s}
#<?php echo $uid;?> .slbl.act{color:#1d4ed8}
#<?php echo $uid;?> .slbl.done{color:#065f46}
#<?php echo $uid;?> .bp{height:44px;padding:0 24px;border:none;border-radius:10px;background:#3b82f6;color:#fff;font-size:15px;font-weight:600;cursor:pointer;font-family:inherit;transition:background .15s}
#<?php echo $uid;?> .bp:hover{background:#2563eb}
#<?php echo $uid;?> .bo{height:40px;padding:0 16px;border:1px solid #e5e7eb;border-radius:10px;background:#fff;color:#374151;font-size:13px;cursor:pointer;font-family:inherit;transition:all .15s}
#<?php echo $uid;?> .bo:hover{border-color:#3b82f6;color:#1d4ed8}
#<?php echo $uid;?> .acts{display:flex;justify-content:space-between;align-items:center;margin-top:16px;gap:10px}
#<?php echo $uid;?> .ibox-info{padding:12px 14px;border-radius:10px;font-size:13px;line-height:1.5;margin-top:10px;background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af}
#<?php echo $uid;?> .ibox-hint{font-size:12px;color:#9ca3af;margin-top:8px;line-height:1.4}
#<?php echo $uid;?> .summ-box{display:flex;align-items:center;justify-content:space-between;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;margin-top:14px}
#<?php echo $uid;?> .summ-val{font-size:22px;font-weight:700;color:#111827}
#<?php echo $uid;?> .offer-card{background:#fff;border-radius:14px;border:1px solid #e5e7eb;padding:1.25rem;margin-bottom:12px;position:relative;transition:box-shadow .15s}
#<?php echo $uid;?> .offer-card:hover{box-shadow:0 2px 12px rgba(0,0,0,.06)}
#<?php echo $uid;?> .offer-card.best{border:2px solid #3b82f6}
#<?php echo $uid;?> .best-badge{position:absolute;top:-12px;left:16px;background:#3b82f6;color:#fff;font-size:11px;font-weight:600;padding:3px 12px;border-radius:6px}
#<?php echo $uid;?> .offer-top{display:flex;align-items:flex-start;gap:12px;margin-bottom:10px}
#<?php echo $uid;?> .logo-wrap{width:52px;height:52px;border-radius:10px;background:#f9fafb;border:1px solid #e5e7eb;display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden;padding:4px}
#<?php echo $uid;?> .logo-wrap img{width:100%;height:100%;object-fit:contain}
#<?php echo $uid;?> .logo-fb{width:52px;height:52px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;flex-shrink:0;letter-spacing:-.5px}
#<?php echo $uid;?> .offer-info{flex:1;min-width:0}
#<?php echo $uid;?> .offer-name{font-weight:600;font-size:15px;color:#111827;margin-bottom:2px;line-height:1.3}
#<?php echo $uid;?> .offer-type{font-size:12px;color:#6b7280;line-height:1.4}
#<?php echo $uid;?> .offer-price{text-align:right;flex-shrink:0;min-width:90px}
#<?php echo $uid;?> .price-val{font-size:20px;font-weight:700;color:#111827;line-height:1.1}
#<?php echo $uid;?> .price-sub{font-size:11px;color:#9ca3af;margin-top:2px}
#<?php echo $uid;?> .price-eco{font-size:12px;color:#10b981;font-weight:600;margin-top:3px}
#<?php echo $uid;?> .price-ref{font-size:11px;color:#9ca3af;margin-top:3px}
#<?php echo $uid;?> .tags-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
#<?php echo $uid;?> .tag{font-size:11px;padding:4px 8px;border-radius:6px;background:#f3f4f6;color:#374151;border:.5px solid #e5e7eb}
#<?php echo $uid;?> .tag-green{background:#d1fae5;color:#065f46;border-color:#a7f3d0}
#<?php echo $uid;?> .offer-btn{width:100%;height:40px;border:1px solid #e5e7eb;border-radius:8px;background:transparent;color:#374151;font-size:13px;cursor:pointer;margin-top:10px;font-family:inherit;transition:all .15s}
#<?php echo $uid;?> .offer-btn:hover{border-color:#3b82f6;color:#1d4ed8}
#<?php echo $uid;?> .offer-btn.best{height:44px;border:none;background:#3b82f6;color:#fff;font-size:14px;font-weight:600;margin-top:12px}
#<?php echo $uid;?> .offer-btn.best:hover{background:#2563eb}
#<?php echo $uid;?> .tabs-row{display:flex;border-bottom:1px solid #e5e7eb;margin-bottom:14px}
#<?php echo $uid;?> .tab-btn{padding:10px 18px;font-size:14px;background:transparent;border:none;border-bottom:2px solid transparent;color:#6b7280;cursor:pointer;font-family:inherit;margin-bottom:-1px;transition:all .15s}
#<?php echo $uid;?> .tab-btn.on{color:#1d4ed8;border-bottom-color:#3b82f6;font-weight:500}
#<?php echo $uid;?> .stat-card{background:#f9fafb;border-radius:10px;padding:12px 8px;text-align:center}
#<?php echo $uid;?> .stat-val{font-size:16px;font-weight:700;color:#111827}
#<?php echo $uid;?> .stat-lbl{font-size:11px;color:#9ca3af;margin-top:3px;line-height:1.3}
#<?php echo $uid;?> .eco-badge{background:#d1fae5;color:#065f46;font-size:12px;font-weight:600;padding:5px 12px;border-radius:8px;white-space:nowrap}
#<?php echo $uid;?> .results-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;gap:10px;flex-wrap:wrap}
#<?php echo $uid;?> .page-title{font-size:18px;font-weight:700;color:#111827;margin:0 0 4px}
#<?php echo $uid;?> .page-sub{font-size:13px;color:#6b7280;margin:0 0 16px}
#<?php echo $uid;?> .fnote{background:#f9fafb;border-radius:10px;padding:12px 14px;margin-top:14px;font-size:12px;color:#9ca3af;line-height:1.5}
@media(max-width:480px){
  #<?php echo $uid;?> .g2{grid-template-columns:1fr}
  #<?php echo $uid;?> .g3{grid-template-columns:1fr 1fr}
  #<?php echo $uid;?> .slbl{display:none}
  #<?php echo $uid;?> .cc{padding:1rem}
  #<?php echo $uid;?> .offer-card{padding:1rem}
  #<?php echo $uid;?> .price-val{font-size:17px}
  #<?php echo $uid;?> .offer-price{min-width:80px}
  #<?php echo $uid;?> .tog{flex-wrap:wrap}
}

/* ── Modal Lead (hors conteneur - classes globales dediees) ─────────────────── */
.lmodal-ov{display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:99999;align-items:center;justify-content:center;padding:16px}
.lmodal-ov.open{display:flex}
.lmodal-box{background:#fff;border-radius:16px;width:100%;max-width:420px;max-height:90vh;overflow-y:auto;box-shadow:0 20px 50px rgba(0,0,0,.3)}
.lmodal-head{background:linear-gradient(135deg,#1e3a8a,#3b82f6);color:#fff;padding:18px 22px;border-radius:16px 16px 0 0;font-size:16px;font-weight:700;position:relative}
.lmodal-close{position:absolute;top:12px;right:14px;background:rgba(255,255,255,.2);border:none;color:#fff;width:28px;height:28px;border-radius:50%;font-size:18px;line-height:1;cursor:pointer}
.lmodal-summ{background:#eff6ff;margin:16px 22px 0;padding:12px 14px;border-radius:10px;border:1px solid #bfdbfe}
.lmfrow{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:16px 22px 0}
.lmfi{width:100%;height:44px;border:1px solid #e5e7eb;border-radius:8px;padding:0 12px;font-size:15px;background:#f9fafb;color:#111827;box-sizing:border-box}
.lmfi:focus{outline:none;border-color:#3b82f6;background:#fff}
.lmrgpd{display:flex;align-items:flex-start;gap:8px;padding:14px 22px 0;font-size:12px;color:#6b7280;line-height:1.5;cursor:pointer}
.lmrgpd input{margin-top:2px;flex-shrink:0}
.lmferr{display:none;color:#dc2626;font-size:12px;padding:10px 22px 0;line-height:1.4}
.lmodal-sub{width:calc(100% - 44px);margin:16px 22px 22px;height:46px;border:none;border-radius:10px;background:#3b82f6;color:#fff;font-size:15px;font-weight:600;cursor:pointer}
.lmodal-sub:disabled{opacity:.6;cursor:not-allowed}
@media(max-width:480px){.lmfrow{grid-template-columns:1fr}}
</style>
<div id="<?php echo $uid;?>"><p style="color:#9ca3af;font-size:14px;padding:1rem">⏳ Chargement...</p></div>
<script>
(function(){
var UID='<?php echo $uid;?>',EDEF='<?php echo $eg;?>',
CMPNONCE='<?php echo $cmp_nonce;?>',CMPAJAX='<?php echo $cmp_ajax;?>',
API='https://cme-tracking-api-217943559750.europe-west1.run.app';

var LOGOS={
edf:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/06/edf_logo.png',
te:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/Total-energie-logo.png',
engie:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/Engie-logo-1.png',
ekwa:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/06/ekwateur_logo-scaled.png',
octopus:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/06/octopus_energy_logo.png',
ohm:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/OHM-logo.png',
ilek:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/Ilek-logo.png',
plenitude:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/06/Logo_Plenitude.png',
vattenfall:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/06/vattenfall_logo.png',
butagaz:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/06/butagaz_logo.webp',
alpiq:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/Alpiq-logo.png',
primeo:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/Primeo-logo.png'
};

var ELEC=[
{id:'edf-bleu',logo:'edf',nom:'EDF',offre:'Tarif Bleu',type:'Tarif réglementé',px:0.19398,abo:11.80,eng:0,vert:false,tags:['Tarif officiel','Sans engagement','Garantie EDF'],c:'#1A4F8A',i:'EDF',url:'https://particulier.edf.fr/fr/accueil/electricite-gaz.html'},
{id:'primeo-elec',logo:'primeo',nom:'Primeo Énergie',offre:'Fix Confort+',type:'Offre de marché',px:0.1970,abo:8.20,eng:12,vert:false,tags:['Prix fixe 1 an','Groupe suisse'],c:'#E30613',i:'PRM',url:'https://souscription.primeo-energie.fr/mesCoordonnees'},
{id:'ohm-elec',logo:'ohm',nom:'Ohm Énergie',offre:'Prix Fixe Élec',type:'Offre locale',px:0.1980,abo:7.80,eng:12,vert:false,tags:['Prix fixe 1 an','Service client FR','Local'],c:'#FF6600',i:'OHM',url:'https://ohm-energie.com/offre/electricite'},
{id:'alpiq-elec',logo:'alpiq',nom:'Alpiq',offre:'Elec Fixe Confort',type:'Offre de marché',px:0.1995,abo:8.40,eng:12,vert:false,tags:['Groupe suisse','Prix fixe 1 an'],c:'#005A96',i:'ALP',url:'https://particuliers.alpiq.fr/electricite/notre-offre'},
{id:'ekwa-elec',logo:'ekwa',nom:'Ekwateur',offre:'Électricité Verte',type:'Offre verte',px:0.2010,abo:7.99,eng:0,vert:true,tags:['100% renouvelable','Coopérative','B-Corp'],c:'#3D8B37',i:'EKW',url:'https://ekwateur.fr/electricite-verte/'},
{id:'vattenfall',logo:'vattenfall',nom:'Vattenfall',offre:'Elec Fixe',type:'Offre de marché',px:0.2020,abo:8.60,eng:12,vert:true,tags:['Hydroélectrique','Prix fixe'],c:'#1F3A6E',i:'VAT',url:'https://www.vattenfall.fr/electricite-et-gaz/offres-electricite-moins-chere'},
{id:'plen-elec',logo:'plenitude',nom:'Plenitude',offre:'Fix Électricité',type:'Offre de marché',px:0.2030,abo:8.30,eng:12,vert:false,tags:['Prix fixe 2 ans','Ex-Eni'],c:'#F5A623',i:'PLN',url:'https://www.eniplenitude.fr/offres-electricite'},
{id:'ilek-elec',logo:'ilek',nom:'ilek',offre:'Je choisis Vert',type:'Offre verte',px:0.2055,abo:8.10,eng:0,vert:true,tags:['Énergie locale','Producteurs FR'],c:'#6DBF4A',i:'ILK',url:'https://www.ilek.fr/offre-electricite'},
{id:'octopus-elec',logo:'octopus',nom:'Octopus Energy',offre:'Électricité Verte',type:'Offre verte',px:0.2075,abo:8.20,eng:0,vert:true,tags:['100% vert','App innovante'],c:'#E8107F',i:'OCT',url:'https://octopusenergy.fr/offre'},
{id:'te-fixe',logo:'te',nom:'TotalEnergies',offre:'Verte Fixe 1 an',type:'Offre de marché',px:0.2089,abo:8.90,eng:12,vert:true,tags:['Prix fixe 1 an','100% renouvelable'],c:'#E8001C',i:'TE',url:'https://www.totalenergies.fr/particuliers/electricite/offres-d-electricite'},
{id:'engie-elec',logo:'engie',nom:'Engie',offre:'Elec Moins Chère',type:'Offre de marché',px:0.2045,abo:8.50,eng:0,vert:false,tags:['Sans engagement','App mobile'],c:'#009DE0',i:'ENG',url:'https://particuliers.engie.fr/electricite.html'},
{id:'butagaz-elec',logo:'butagaz',nom:'Butagaz',offre:'Elec Sérénité',type:'Offre de marché',px:0.2095,abo:8.75,eng:0,vert:false,tags:['Groupe Shell','Sans engagement'],c:'#E85D1E',i:'BUT',url:'https://www.butagaz.fr/gaz-electricite/offres-electricite'}
];
var GAZ=[
{id:'ohm-gaz',logo:'ohm',nom:'Ohm Énergie',offre:'Gaz Prix Fixe',type:'Offre locale',px:0.0971,abo:5.70,eng:12,vert:false,tags:['Prix fixe 1 an','Service client FR'],c:'#FF6600',i:'OHM',url:'https://ohm-energie.com/offre/offre-gaz'},
{id:'engie-gaz',logo:'engie',nom:'Engie',offre:'Gaz Moins Cher',type:'Offre de marché',px:0.1045,abo:5.80,eng:0,vert:false,tags:['Sans engagement','App mobile'],c:'#009DE0',i:'ENG',url:'https://particuliers.engie.fr/gaz.html'},
{id:'vat-gaz',logo:'vattenfall',nom:'Vattenfall',offre:'Gaz Fixe',type:'Offre de marché',px:0.1050,abo:5.90,eng:12,vert:false,tags:['Prix fixe 1 an'],c:'#1F3A6E',i:'VAT',url:'https://www.vattenfall.fr/electricite-et-gaz/offres-gaz-moins-cheres'},
{id:'plen-gaz',logo:'plenitude',nom:'Plenitude',offre:'Fix Gaz',type:'Offre de marché',px:0.1065,abo:6.00,eng:12,vert:false,tags:['Prix fixe 2 ans','Ex-Eni'],c:'#F5A623',i:'PLN',url:'https://www.eniplenitude.fr/offres-gaz'},
{id:'te-gaz',logo:'te',nom:'TotalEnergies',offre:'Gaz Fixe 1 an',type:'Offre de marché',px:0.1089,abo:5.99,eng:12,vert:false,tags:['Prix fixe 1 an'],c:'#E8001C',i:'TE',url:'https://www.totalenergies.fr/particuliers/electricite-et-gaz/offres-d-electricite-et-gaz'},
{id:'butagaz-gaz',logo:'butagaz',nom:'Butagaz',offre:'Gaz Sérénité',type:'Offre de marché',px:0.1120,abo:6.20,eng:0,vert:false,tags:['Groupe Shell','Sans engagement'],c:'#E85D1E',i:'BUT',url:'https://www.butagaz.fr/gaz-electricite/offres-electricite'},
{id:'ekwa-biogaz',logo:'ekwa',nom:'Ekwateur',offre:'Biogaz 100%',type:'Gaz vert',px:0.1180,abo:6.10,eng:0,vert:true,tags:['Biogaz 100%','B-Corp'],c:'#3D8B37',i:'EKW',url:'https://ekwateur.fr/gaz-vert-renouvelable/'},
{id:'edf-gaz',logo:'edf',nom:'EDF',offre:'Prix Repère CRE',type:'Référence CRE',px:0.12766,abo:6.49,eng:0,vert:false,tags:['Référence CRE','Prix repère'],c:'#1A4F8A',i:'EDF',url:'https://particulier.edf.fr/fr/accueil/electricite-gaz.html'}
];

// ── État global ──────────────────────────────────────────────────────────────
var S={
  step:1,
  logement:'maison',surface:75,personnes:2,chauffage:'elec',
  codepostal:'75001',pdl:'',pce:'',
  option:'base',elec:3500,gaz:8000,
  enrg:EDEF==='gaz'?'gaz':(EDEF==='dual'?'dual':'elec'),
  tab:EDEF==='gaz'?'gaz':'elec',
  edfPrix:0.19398,edfAbo:11.80,edfDate:'01/02/2026',
  gazRef:0.12766,gazAbo:6.49
};

// ── Calculs ──────────────────────────────────────────────────────────────────
function estim(){
  var s=parseInt(S.surface)||75,n=parseInt(S.personnes)||2;
  S.elec=Math.round(s*15+n*400+(S.chauffage==='elec'?s*28:0));
  S.gaz=S.chauffage==='gaz'?Math.round(s*60+n*500):S.chauffage==='pac'?Math.round(s*8+n*200):2000;
}
function pMoy(p,opt){
  var px=parseFloat(p)||0.19398;
  if(opt!=='hphc')return px;
  return Math.round((px*1.156*.60+px*0.726*.40)*10000)/10000;
}
function calcAn(o,kwh,opt){
  return Math.round(pMoy(o.px,opt)*(parseInt(kwh)||3500)+(parseFloat(o.abo)||9.47)*12);
}
function logClic(d){
  fetch(API+'/api/log-clic',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify(Object.assign({tool:'comparateur-energie',user_agent:navigator.userAgent.slice(0,120)},d))}).catch(function(){});
}

// ── DOM helpers ──────────────────────────────────────────────────────────────
function $(){return document.getElementById(UID);}
function mk(tag,cls,txt){
  var d=document.createElement(tag);
  if(cls)d.className=cls;
  if(txt!=null)d.textContent=txt;
  return d;
}
function ap(parent,child){parent.appendChild(child);return parent;}

function mkTog(opts,val,onChange){
  var d=mk('div','tog');
  opts.forEach(function(o){
    var b=mk('button','tbtn'+(val===o.v?' on':''),o.l);
    b.onclick=function(){
      d.querySelectorAll('.tbtn').forEach(function(x){x.className='tbtn';});
      b.className='tbtn on';
      onChange(o.v);
    };
    ap(d,b);
  });
  return d;
}

function mkInput(type,val,onChg,ph,min,max,step){
  var i=document.createElement('input');
  i.type=type;i.value=val||'';
  if(ph)i.placeholder=ph;
  if(min!=null)i.min=min;
  if(max!=null)i.max=max;
  if(step)i.step=step;
  i.oninput=function(){onChg(i.value);};
  return i;
}
function mkField(lbl,type,val,onChg,ph,min,max,step){
  var d=mk('div');
  ap(d,mk('label',null,lbl));
  ap(d,mkInput(type,val,onChg,ph,min,max,step));
  return d;
}
function mkSel(lbl,opts,selIdx,onChg){
  var d=mk('div'),s=document.createElement('select');
  ap(d,mk('label',null,lbl));
  opts.forEach(function(o,i){
    var op=document.createElement('option');
    op.value=i;op.textContent=o;
    if(i===selIdx)op.selected=true;
    ap(s,op);
  });
  s.onchange=function(){onChg(parseInt(s.value));};
  return ap(d,s);
}
function mkLogo(o){
  var w=mk('div','logo-wrap');
  if(LOGOS[o.logo]){
    var img=new Image();
    img.alt=o.nom;
    img.onerror=function(){w.innerHTML='';var f=mk('div','logo-fb');f.style.background=o.c+'25';f.style.color=o.c;f.textContent=o.i;ap(w,f);};
    img.src=LOGOS[o.logo];
    ap(w,img);
  } else {
    var f=mk('div','logo-fb');f.style.background=o.c+'25';f.style.color=o.c;f.textContent=o.i;ap(w,f);
  }
  return w;
}

// ── StepBar ──────────────────────────────────────────────────────────────────
function mkSbar(cur){
  var labels=['Mon profil','Consommation','Offres'];
  var d=mk('div','sbar');
  labels.forEach(function(lbl,i){
    var n=i+1,done=n<cur,act=n===cur;
    var dot=mk('div','sdot'+(done?' done':act?' act':''),done?'✓':String(n));
    var sp=mk('span','slbl'+(done?' done':act?' act':''),lbl);
    var wrap=mk('div');wrap.style.cssText='display:flex;align-items:center;gap:6px;flex-shrink:0';
    ap(wrap,dot);ap(wrap,sp);ap(d,wrap);
    if(i<2)ap(d,mk('div','sline'));
  });
  return d;
}

// ── Carte offre ──────────────────────────────────────────────────────────────
function mkOfferCard(o,rang,kwh,opt,energie,refPrix){
  var best=rang===0;
  var prix=calcAn(o,kwh,opt);
  var eco=Math.max(0,refPrix-prix);
  var d=mk('div','offer-card'+(best?' best':''));

  if(best){ap(d,mk('div','best-badge','⭐ Meilleure offre'));}

  var top=mk('div','offer-top');
  ap(top,mkLogo(o));

  var info=mk('div','offer-info');
  ap(info,mk('div','offer-name',o.nom+' — '+o.offre));
  ap(info,mk('div','offer-type',o.type));
  ap(info,mk('div','offer-type',o.eng>0?'Engagement '+o.eng+' mois':'Sans engagement'));
  ap(top,info);

  var pr=mk('div','offer-price');
  ap(pr,mk('div','price-val',prix.toLocaleString('fr-FR')+'€'));
  var sub=mk('div','price-sub','/an · '+Math.round(prix/12)+'€/mois');ap(pr,sub);
  if(eco>0){ap(pr,mk('div','price-eco','−'+eco.toLocaleString('fr-FR')+'€/an'));}
  else{ap(pr,mk('div','price-ref','Référence'));}
  ap(top,pr);
  ap(d,top);

  var tags=mk('div','tags-row');
  if(o.vert){var tg=mk('span','tag tag-green','♻ Énergie verte');ap(tags,tg);}
  o.tags.forEach(function(t){ap(tags,mk('span','tag',t));});
  ap(d,tags);

  var btn=mk('button','offer-btn'+(best?' best':''),best?'Souscrire à cette offre →':'Voir cette offre →');
  btn.onclick=function(){
    logClic({offre_id:o.id,offre_nom:o.nom+' — '+o.offre,energie:energie,kwh:kwh,prix_annuel:prix,economie:eco});
    openLeadModal({
      fournisseur:o.nom, offre:o.offre, energie:energie,
      prix_annuel:prix, economie:eco, kwh:kwh,
      option_tarifaire:S.option,
      lien_offre:o.url+'?utm_source=cme&utm_medium=comparateur&utm_campaign='+o.id
    });
  };
  ap(d,btn);
  return d;
}

// ── Étape 1 ──────────────────────────────────────────────────────────────────
function step1(root){
  var showE=S.enrg==='elec'||S.enrg==='dual';
  var showG=S.enrg==='gaz'||S.enrg==='dual';

  // Profil
  var c1=mk('div','cc');
  ap(c1,mk('div','stitle','🏠 Type de logement'));
  ap(c1,mkTog([{v:'maison',l:'🏠 Maison'},{v:'appartement',l:'🏢 Appartement'}],S.logement,function(v){S.logement=v;}));
  var g2=mk('div','g2');g2.style.marginTop='14px';
  ap(g2,mkField('Surface (m²)','number',S.surface,function(v){S.surface=parseInt(v)||75;estim();},'',10,500));
  ap(g2,mkSel('Nombre de personnes',['1 personne','2 personnes','3 personnes','4 personnes','5+ personnes'],Math.min(4,(parseInt(S.personnes)||2)-1),function(v){S.personnes=v+1;estim();}));
  ap(g2,mkSel('Mode de chauffage',['⚡ Électrique','🔥 Gaz naturel','♻ Pompe à chaleur','🛢 Fioul / autre'],['elec','gaz','pac','fioul'].indexOf(S.chauffage),function(v){S.chauffage=['elec','gaz','pac','fioul'][v];estim();}));
  ap(g2,mkField('Code postal','text',S.codepostal,function(v){S.codepostal=v;},'ex: 75001'));
  ap(c1,g2);
  ap(root,c1);

  // PDL/PCE conditionnel
  if(showE||showG){
    var cp=mk('div','cc');
    ap(cp,mk('div','stitle','📋 Numéros de compteur (optionnel)'));
    var gp=mk('div','g2');
    if(showE){
      var dp=mk('div');
      ap(dp,mk('label',null,'N° PDL / PRM — Électricité'));
      var ip=mkInput('text',S.pdl,function(v){S.pdl=v;},'14 chiffres');
      ap(dp,ip);
      ap(dp,mk('div','hint','📄 Sur votre facture EDF ou relevé Linky'));
      ap(gp,dp);
    }
    if(showG){
      var dc=mk('div');
      ap(dc,mk('label',null,'N° PCE — Gaz'));
      var ic=mkInput('text',S.pce,function(v){S.pce=v;},'14 chiffres');
      ap(dc,ic);
      ap(dc,mk('div','hint','📄 Sur votre facture gaz GRDF'));
      ap(gp,dc);
    }
    ap(cp,gp);
    ap(root,cp);
  }

  // Énergie (dual uniquement)
  if(EDEF==='dual'){
    var ce=mk('div','cc');
    ap(ce,mk('div','stitle','⚡ Énergie à comparer'));
    ap(ce,mkTog(
      [{v:'elec',l:'⚡ Électricité'},{v:'gaz',l:'🔥 Gaz'},{v:'dual',l:'⚡🔥 Électricité & Gaz'}],
      S.enrg,
      function(v){S.enrg=v;S.tab=v==='gaz'?'gaz':'elec';render();}
    ));
    ap(root,ce);
  }

  var acts=mk('div','acts');
  ap(acts,mk('div'));
  var nb=mk('button','bp','Continuer →');
  nb.onclick=function(){S.step=2;render();};
  ap(acts,nb);
  ap(root,acts);
}

// ── Input number avec flèches natives stylisées ─────────────────────────────
function mkNumStepper(val,min,max,step,onChange){
  var inp=document.createElement('input');
  inp.type='number';
  inp.value=val;
  inp.min=min;inp.max=max;inp.step=step;
  inp.oninput=function(){var v=parseInt(inp.value);if(!isNaN(v)&&v>=min&&v<=max)onChange(v);};
  inp.onblur=function(){
    var v=parseInt(inp.value)||val;
    v=Math.max(min,Math.min(max,Math.round(v/step)*step));
    inp.value=v;onChange(v);
  };
  return inp;
}

// ── Étape 2 ──────────────────────────────────────────────────────────────────
function step2(root){
  var showE=S.enrg==='elec'||S.enrg==='dual';
  var showG=S.enrg==='gaz'||S.enrg==='dual';

  // Option tarifaire
  var ct=mk('div','cc');
  ap(ct,mk('div','stitle','🕐 Option tarifaire'));
  ap(ct,mkTog(
    [{v:'base',l:'⚡ Tarif de base'},{v:'hphc',l:'🌙 Heures pleines / creuses'}],
    S.option,
    function(v){S.option=v;render();}
  ));
  if(S.option==='hphc'){
    var ib=mk('div','ibox-info','🌙 Heures creuses (~22h–6h) : tarif réduit. ☀️ Heures pleines : tarif normal. Avantageux si vous programmez lave-linge ou chargez un VE la nuit.');
    ap(ct,ib);
  } else {
    ap(ct,mk('div','ibox-hint','✅ Prix unique 24h/24 — idéal si votre consommation est régulière.'));
  }
  ap(root,ct);

  // Consommation
  var cc=mk('div','cc');
  ap(cc,mk('div','stitle','📊 Consommation annuelle estimée'));
  var gc=mk('div','g2');
  if(showE){
    var de=mk('div');
    ap(de,mk('label',null,'⚡ Électricité (kWh/an)'));
    var ie=mkNumStepper(S.elec,500,30000,100,function(v){S.elec=v;updateSumm();});
    ap(de,ie);
    ap(de,mk('div','hint','Estimé selon votre profil — modifiable'));
    ap(gc,de);
  }
  if(showG){
    var dg=mk('div');
    ap(dg,mk('label',null,'🔥 Gaz (kWh/an)'));
    var ig=mkNumStepper(S.gaz,500,50000,1000,function(v){S.gaz=v;updateSumm();});
    ap(dg,ig);
    ap(dg,mk('div','hint','Estimé selon votre chauffage — modifiable'));
    ap(gc,dg);
  }
  ap(cc,gc);

  // Facture estimée interactive (élec ET gaz)
  var smWrap=mk('div');smWrap.style.cssText='display:grid;grid-template-columns:'+(showE&&showG?'1fr 1fr':'1fr')+';gap:12px;margin-top:14px';
  if(showE){
    var sm=mk('div','summ-box');sm.style.flex='1';
    var sd=mk('div');
    var sl=mk('div');sl.style.cssText='font-size:12px;color:#9ca3af;margin-bottom:6px';sl.id=UID+'-summ-lbl';ap(sd,sl);
    var sv=mk('div');sv.style.cssText='display:flex;align-items:baseline;gap:6px;flex-wrap:wrap';
    var svv=mk('span');svv.style.cssText='font-size:20px;font-weight:700;color:#111827';svv.id=UID+'-summ-val';
    var sva=mk('span');sva.style.cssText='font-size:13px;color:#6b7280';sva.textContent='/an';
    var svm=mk('span');svm.style.cssText='font-size:12px;color:#9ca3af';svm.id=UID+'-summ-mo';
    ap(sv,svv);ap(sv,sva);ap(sv,svm);ap(sd,sv);ap(sm,sd);
    ap(sm,mk('div',null,'⚡'));ap(smWrap,sm);
  }
  if(showG){
    var smg=mk('div','summ-box');smg.style.flex='1';
    var sdg=mk('div');
    var slg=mk('div');slg.style.cssText='font-size:12px;color:#9ca3af;margin-bottom:6px';slg.id=UID+'-summ-gaz-lbl';ap(sdg,slg);
    var svg2=mk('div');svg2.style.cssText='display:flex;align-items:baseline;gap:6px;flex-wrap:wrap';
    var svgv=mk('span');svgv.style.cssText='font-size:20px;font-weight:700;color:#111827';svgv.id=UID+'-summ-gaz-val';
    var svga=mk('span');svga.style.cssText='font-size:13px;color:#6b7280';svga.textContent='/an';
    var svgm=mk('span');svgm.style.cssText='font-size:12px;color:#9ca3af';svgm.id=UID+'-summ-gaz-mo';
    ap(svg2,svgv);ap(svg2,svga);ap(svg2,svgm);ap(sdg,svg2);ap(smg,sdg);
    ap(smg,mk('div',null,'🔥'));ap(smWrap,smg);
  }
  ap(cc,smWrap);
  ap(root,cc);

  // Actions
  var acts=mk('div','acts');
  var bb=mk('button','bo','← Retour');
  bb.onclick=function(){S.step=1;render();};
  ap(acts,bb);
  var nb=mk('button','bp','Voir les offres →');
  nb.onclick=function(){S.step=3;render();};
  ap(acts,nb);
  ap(root,acts);

  updateSumm();
}

function updateSumm(){
  // Facture élec
  var lbl=document.getElementById(UID+'-summ-lbl');
  var val=document.getElementById(UID+'-summ-val');
  var mo=document.getElementById(UID+'-summ-mo');
  if(lbl&&val&&mo){
    var trvK=S.option==='hphc'?pMoy(S.edfPrix,'hphc'):S.edfPrix;
    var trv=Math.round(trvK*(parseInt(S.elec)||3500)+S.edfAbo*12)||0;
    lbl.textContent='💡 Facture EDF actuelle — option '+(S.option==='hphc'?'HP/HC':'Base');
    val.textContent=trv.toLocaleString('fr-FR')+' €';
    mo.textContent='soit '+Math.round(trv/12)+' €/mois';
  }
  // Facture gaz (Prix Repère CRE)
  var glbl=document.getElementById(UID+'-summ-gaz-lbl');
  var gval=document.getElementById(UID+'-summ-gaz-val');
  var gmo=document.getElementById(UID+'-summ-gaz-mo');
  if(glbl&&gval&&gmo){
    var trvGaz=Math.round(S.gazRef*(parseInt(S.gaz)||8000)+S.gazAbo*12)||0;
    glbl.textContent='💡 Facture gaz actuelle (Prix Repère CRE)';
    gval.textContent=trvGaz.toLocaleString('fr-FR')+' €';
    gmo.textContent='soit '+Math.round(trvGaz/12)+' €/mois';
  }
}

// ── Étape 3 ──────────────────────────────────────────────────────────────────
function step3(root){
  var offs=S.tab==='elec'?ELEC:GAZ;
  var kwh=S.tab==='elec'?(parseInt(S.elec)||3500):(parseInt(S.gaz)||8000);
  var sorted=offs.slice().sort(function(a,b){return calcAn(a,kwh,S.option)-calcAn(b,kwh,S.option);});
  var ref=sorted[sorted.length-1];
  var refPrix=calcAn(ref,kwh,S.option);
  var maxE=Math.max(0,refPrix-calcAn(sorted[0],kwh,S.option));
  var avgE=Math.max(0,Math.round(sorted.reduce(function(s,o){return s+Math.max(0,refPrix-calcAn(o,kwh,S.option));},0)/sorted.length));

  // Onglets dual
  if(EDEF==='dual'&&S.enrg==='dual'){
    var tabs=mk('div','tabs-row');
    ['elec','gaz'].forEach(function(t){
      var cnt=t==='elec'?ELEC.length:GAZ.length;
      var tb=mk('button','tab-btn'+(S.tab===t?' on':''),(t==='elec'?'⚡ Électricité':'🔥 Gaz')+' ('+cnt+')');
      tb.onclick=function(){S.tab=t;render();};
      ap(tabs,tb);
    });
    ap(root,tabs);
  }

  // En-tête résultats
  var rh=mk('div','results-head');
  var rht=mk('h3');rht.style.cssText='font-size:15px;font-weight:600;color:#111827;margin:0';
  rht.textContent=sorted.length+' offres trouvées'+(S.option==='hphc'?' · option HP/HC':'');
  ap(rh,rht);
  if(maxE>0){
    var eb=mk('span','eco-badge',"Jusqu'à "+maxE.toLocaleString('fr-FR')+'€/an');
    ap(rh,eb);
  }
  ap(root,rh);

  // Cartes offres
  sorted.forEach(function(o,i){
    ap(root,mkOfferCard(o,i,kwh,S.option,S.tab,refPrix));
  });

  // Stats résumées
  var g3=mk('div','g3');g3.style.marginTop='8px';
  [
    ['Économie moy.',avgE>0?'+'+avgE.toLocaleString('fr-FR')+'€':'—'],
    ['Offres comparées',String(sorted.length)],
    ['Meilleure offre',calcAn(sorted[0],kwh,S.option).toLocaleString('fr-FR')+'€']
  ].forEach(function(p){
    var s=mk('div','stat-card');
    ap(s,mk('div','stat-val',p[1]));
    ap(s,mk('div','stat-lbl',p[0]));
    ap(g3,s);
  });
  ap(root,g3);

  // Note légale
  ap(root,mk('div','fnote','ℹ️ Tarif EDF mis à jour depuis la CRE ('+S.edfDate+'). Offres de marché : indicatifs trimestriels. Votre facture réelle dépend de votre puissance souscrite et consommation exacte.'));

  // Boutons retour
  var acts=mk('div','acts');acts.style.marginTop='14px';
  var bm=mk('button','bo','← Modifier');
  bm.onclick=function(){S.step=2;render();};
  ap(acts,bm);
  var bn=mk('button','bo','🔄 Nouvelle recherche');
  bn.onclick=function(){S.step=1;render();};
  ap(acts,bn);
  ap(root,acts);
}

// ── Modal Lead (formulaire souscription) ──────────────────────────────────────
var LEAD_CTX=null;

function openLeadModal(ctx){
  LEAD_CTX=ctx;
  var ov=document.getElementById(UID+'-lmodal');
  if(!ov)return;
  var icon=ctx.energie==='gaz'?'\ud83d\udd25':'\u26a1';
  var summ=document.getElementById(UID+'-lm-summ');
  if(summ){
    summ.innerHTML=
      '<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">'
      +'<span style="font-size:20px">'+icon+'</span>'
      +'<div><div style="font-weight:600;font-size:15px;color:#111827">'+ctx.fournisseur+' \u2014 '+ctx.offre+'</div>'
      +'<div style="font-size:12px;color:#6b7280">'+(ctx.energie==='gaz'?'Gaz naturel':'\u00c9lectricit\u00e9')+'</div></div></div>'
      +'<div style="display:flex;gap:16px;margin-top:10px;padding-top:10px;border-top:1px solid #e5e7eb">'
      +'<div><div style="font-size:18px;font-weight:700;color:#111827">'+ctx.prix_annuel.toLocaleString('fr-FR')+'\u20ac</div><div style="font-size:11px;color:#9ca3af">par an</div></div>'
      +(ctx.economie>0?'<div><div style="font-size:18px;font-weight:700;color:#10b981">\u2212'+ctx.economie.toLocaleString('fr-FR')+'\u20ac</div><div style="font-size:11px;color:#9ca3af">\u00e9conomie/an</div></div>':'')
      +'</div>';
  }
  var err=document.getElementById(UID+'-lm-err');if(err)err.style.display='none';
  var subb=document.getElementById(UID+'-lm-sub');
  if(subb){subb.disabled=false;subb.textContent='Envoyer ma demande \u2192';}
  ov.className='lmodal-ov open';
  document.body.style.overflow='hidden';
}
function closeLeadModal(){
  var ov=document.getElementById(UID+'-lmodal');
  if(ov){ov.className='lmodal-ov';document.body.style.overflow='';}
}
function submitLead(){
  var g=function(id){return document.getElementById(UID+'-'+id);};
  var prn=(g('lm-prn')||{}).value||'', nom=(g('lm-nom')||{}).value||'';
  var mail=(g('lm-mail')||{}).value||'', tel=(g('lm-tel')||{}).value||'';
  var rgpd=g('lm-rgpd')&&g('lm-rgpd').checked;
  var err=g('lm-err');
  if(!prn.trim()||!nom.trim()||!mail.trim()||!tel.trim()||!rgpd){
    if(err)err.style.display='block';
    return;
  }
  if(err)err.style.display='none';
  var sub=g('lm-sub');
  if(sub){sub.disabled=true;sub.textContent='Envoi en cours...';}

  // Ouvrir l'onglet fournisseur IMMEDIATEMENT (geste utilisateur direct)
  // -> evite le blocage popup (window.open apres un fetch async est bloque)
  var providerTab=null;
  if(LEAD_CTX&&LEAD_CTX.lien_offre){
    providerTab=window.open('about:blank','_blank');
  }

  var data=Object.assign({
    prenom:prn.trim(),nom:nom.trim(),email:mail.trim(),telephone:tel.trim(),
    logement:S.logement,surface:S.surface,personnes:S.personnes,chauffage:S.chauffage,
    codepostal:S.codepostal,pdl:S.pdl,pce:S.pce,
    src_post:new URLSearchParams(window.location.search).get('src_post')||''
  },LEAD_CTX);

  // Rediriger l'onglet deja ouvert vers l'offre - instantane
  if(providerTab){
    try{providerTab.location.href=LEAD_CTX.lien_offre;}catch(e){}
  }

  // Confirmation immediate, sans attendre le serveur
  showLeadSuccess();

  // Envoi en arriere-plan (email + Sheets)
  var fd=new FormData();
  fd.append('action','cme_cmp_lead');
  fd.append('nonce',CMPNONCE);
  fd.append('payload',JSON.stringify(data));
  fetch(CMPAJAX,{method:'POST',body:fd})
    .then(function(r){return r.json();})
    .then(function(res){
      console.log('[CME Lead] Reponse serveur:',res);
      if(res&&res.data)console.log('[CME Lead] Email envoye:',res.data.email_sent,'| Sheets:',res.data.gas);
    })
    .catch(function(err){console.warn('[CME Lead] Erreur:',err);});
}
function showLeadSuccess(){
  var form=document.getElementById(UID+'-lmform');
  if(form){
    form.innerHTML='<div style="text-align:center;padding:20px 10px">'
      +'<div style="width:52px;height:52px;border-radius:50%;background:#d1fae5;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">\u2713</div>'
      +'<div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoy\u00e9e !</div>'
      +'<div style="font-size:13px;color:#6b7280;line-height:1.5">Nous vous recontactons sous 48h.<br>L\'offre du fournisseur s\'est ouverte dans un nouvel onglet.</div>'
      +'</div>';
  }
  setTimeout(closeLeadModal,2200);
}

function buildLeadModal(root){
  var ov=mk('div','lmodal-ov');ov.id=UID+'-lmodal';
  var box=mk('div','lmodal-box');

  var head=mk('div','lmodal-head');
  ap(head,mk('div',null,'\ud83d\udce9 Recevoir cette offre'));
  var sub=mk('div');sub.style.cssText='font-size:12px;color:#6b7280;font-weight:400;margin-top:2px';
  sub.textContent='Un conseiller confirme votre \u00e9ligibilit\u00e9 et vous accompagne';
  ap(head,sub);
  var cls=mk('button','lmodal-close','\u00d7');cls.type='button';cls.onclick=closeLeadModal;
  ap(head,cls);ap(box,head);

  var summ=mk('div','lmodal-summ');summ.id=UID+'-lm-summ';ap(box,summ);

  var form=mk('div');form.id=UID+'-lmform';

  var row1=mk('div','lmfrow');
  var fPrn=mk('input','lmfi');fPrn.id=UID+'-lm-prn';fPrn.type='text';fPrn.placeholder='Pr\u00e9nom *';
  var fNom=mk('input','lmfi');fNom.id=UID+'-lm-nom';fNom.type='text';fNom.placeholder='Nom *';
  ap(row1,fPrn);ap(row1,fNom);ap(form,row1);

  var fMail=mk('input','lmfi');fMail.id=UID+'-lm-mail';fMail.type='email';fMail.placeholder='Email *';
  fMail.style.marginTop='10px';ap(form,fMail);

  var fTel=mk('input','lmfi');fTel.id=UID+'-lm-tel';fTel.type='tel';fTel.placeholder='T\u00e9l\u00e9phone *';
  fTel.style.marginTop='10px';ap(form,fTel);

  var rgpd=mk('label','lmrgpd');
  var chk=document.createElement('input');chk.type='checkbox';chk.id=UID+'-lm-rgpd';
  var txt=mk('span');
  txt.innerHTML='J\'accepte que mes donn\u00e9es soient transmises au fournisseur pour \u00eatre recontact\u00e9, conform\u00e9ment \u00e0 notre <a href="https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/" target="_blank" style="color:#3b82f6">politique de confidentialit\u00e9</a> et nos <a href="https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/" target="_blank" style="color:#3b82f6">conditions g\u00e9n\u00e9rales</a>.';
  ap(rgpd,chk);ap(rgpd,txt);ap(form,rgpd);

  var err=mk('div','lmferr','\u26a0\ufe0f Merci de remplir tous les champs et d\'accepter la politique de confidentialit\u00e9.');
  err.id=UID+'-lm-err';ap(form,err);

  var subb=mk('button','lmodal-sub','Envoyer ma demande \u2192');subb.id=UID+'-lm-sub';
  subb.type='button';subb.onclick=submitLead;ap(form,subb);

  ap(box,form);
  ov.addEventListener('click',function(e){if(e.target===ov)closeLeadModal();});
  ap(ov,box);ap(root,ov);
}

// ── Rendu principal ──────────────────────────────────────────────────────────
function render(){
  var root=$();if(!root)return;
  root.innerHTML='';

  // Header
  var hd=mk('div');hd.style.marginBottom='16px';
  ap(hd,mk('h2','page-title','⚡ Comparateur des offres Électricité & Gaz'));
  ap(hd,mk('p','page-sub',"Trouvez l'offre la moins chère selon votre profil en 2 minutes"));
  ap(root,hd);

  ap(root,mkSbar(S.step));

  if(S.step===1)step1(root);
  else if(S.step===2)step2(root);
  else step3(root);
}

// ── Init ─────────────────────────────────────────────────────────────────────
estim();
// Construire le modal UNE SEULE FOIS, hors du conteneur vide a chaque render()
(function(){
  var rootEl=$();
  if(rootEl&&rootEl.parentNode&&!document.getElementById(UID+'-lmodal')){
    buildLeadModal(rootEl.parentNode);
  }
})();
// Rendu immediat avec le prix EDF par defaut (pas d'attente reseau)
render();
// Mise a jour silencieuse du prix EDF en tache de fond (n'affecte pas le 1er rendu)
fetch(API+'/api/tarif-edf')
  .then(function(r){return r.json();})
  .then(function(d){
    if(d&&d.prix_kwh_ttc){
      S.edfPrix=d.prix_kwh_ttc;
      S.edfAbo=d.abo_mois_ttc||11.80;
      S.edfDate=d.date_debut_validite||'01/02/2026';
      ELEC.forEach(function(o){if(o.id==='edf-bleu'){o.px=S.edfPrix;o.abo=S.edfAbo;}});
      render(); // re-rendu discret si le prix a change
    }
  })
  .catch(function(){}); // silencieux : le prix par defaut reste affiche
})();
</script>
<?php
$html = ob_get_clean();
  // Extraire le <script>...</script> et le deplacer en wp_footer
  // (evite que wpautop/wptexturize casse un script volumineux)
  if (preg_match('/<script>(.*?)<\/script>/s', $html, $m)) {
    $html = preg_replace('/<script>.*?<\/script>/s', '', $html, 1);
    global $cme_cmp_footer_scripts;
    if (!isset($cme_cmp_footer_scripts)) $cme_cmp_footer_scripts = array();
    $cme_cmp_footer_scripts[] = $m[1];
    if (!has_action('wp_footer', 'cme_cmp_print_footer_scripts')) {
      add_action('wp_footer', 'cme_cmp_print_footer_scripts', 99);
    }
  }
  return $html;
}
endif;
add_shortcode('comparateur_energie','cme_comp_sc');

if(!function_exists('cme_cmp_print_footer_scripts')):
function cme_cmp_print_footer_scripts(){
  global $cme_cmp_footer_scripts;
  if (empty($cme_cmp_footer_scripts)) return;
  foreach ($cme_cmp_footer_scripts as $js) {
    echo '<script>'.$js.'</script>'."\n";
  }
}
endif;
