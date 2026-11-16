<?php
/**
 * Plugin Name: CME Comparateur Énergie
 * Plugin URI:  https://www.comprendre-mon-energie.fr
 * Description: Comparateur gaz & électricité — v3.0 vanilla JS, design complet, zéro conflit WordPress
 * Version:     3.4.5
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
  // Profil collecte aux etapes 1/2 -- deja present dans $data (envoye par
  // le JS depuis S), mais jusqu'ici jamais lu ici : il n'atteignait donc
  // ni l'email ni (surtout) leads_convertis/BigQuery, seul le relais
  // Google Sheets (cme-comparateur-leads.gs, qui lit le payload brut) le
  // recevait. Corrige le 16/11/2026 (diagnostic operateur).
  $logement  = sanitize_text_field($data['logement']??'');
  $surface   = intval($data['surface']??0);
  $personnes = intval($data['personnes']??0);
  $chauffage = sanitize_text_field($data['chauffage']??'');
  $cp        = sanitize_text_field($data['codepostal']??'');
  $pdl       = sanitize_text_field($data['pdl']??'');
  $pce       = sanitize_text_field($data['pce']??'');
  $dest   = 'contact@comprendre-mon-energie.fr';

  // Bug trouve le 16/11/2026 (test isole de cme_cmp_handle_lead(), task #28) :
  // des guillemets simples n'interpretent jamais les echappements \xHH en PHP
  // (contrairement a l'equivalent JS \u.. plus haut, openLeadModal()) -- la
  // chaine restait donc litteralement "\xF0\x9F\x94\xA5"/"\xE2\x9A\xA1" dans
  // le sujet/corps de CHAQUE email de lead envoye jusqu'ici. Guillemets
  // doubles : PHP interprete alors correctement les octets UTF-8 (🔥/⚡).
  $icon = ($energie==='gaz')?"\xF0\x9F\x94\xA5":"\xE2\x9A\xA1";
  $sujet = $icon.' Nouvelle demande comparateur — '.$prenom.' '.$nom.' — '.$fourn;

  $corps = '<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:580px;margin:auto">
    <div style="background:linear-gradient(135deg,#1e3a8a,#3b82f6);color:#fff;padding:20px 24px;border-radius:10px 10px 0 0">
      <h2 style="margin:0">'.$icon.' Nouvelle demande — Comparateur Energie</h2>
      <p style="margin:4px 0 0;opacity:.85;font-size:13px">'.date('d/m/Y H:i').'</p>
    </div>
    <div style="background:#fff;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 10px 10px;padding:20px 24px">
      <h3 style="color:#3b82f6;margin:0 0 12px">Contact</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
        <tr><td style="padding:6px;color:#6b7280;width:150px">Nom et pr&eacute;nom</td><td style="padding:6px;font-weight:600">'.trim($prenom.' '.$nom).'</td></tr>
        <tr><td style="padding:6px;color:#6b7280">Email</td><td style="padding:6px">'.($email?'<a href="mailto:'.$email.'" style="color:#3b82f6">'.$email.'</a>':'<span style="color:#9ca3af">non demand&eacute; (formulaire simplifi&eacute;)</span>').'</td></tr>
        <tr><td style="padding:6px;color:#6b7280">Telephone</td><td style="padding:6px"><a href="tel:'.$tel.'" style="color:#3b82f6">'.$tel.'</a></td></tr>
        <tr><td style="padding:6px;color:#6b7280">Logement</td><td style="padding:6px">'.esc_html($logement).' — '.esc_html($surface).' m² — '.esc_html($personnes).' pers. — chauffage '.esc_html($chauffage).'</td></tr>
        <tr><td style="padding:6px;color:#6b7280">Code postal</td><td style="padding:6px">'.esc_html($cp).'</td></tr>
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
      'details' => array(
        'energie'=>$energie,'fournisseur'=>$fourn,'offre'=>$offre,'kwh'=>$kwh,'option_tarifaire'=>$opt,'lien_offre'=>$lien,
        'logement'=>$logement,'surface'=>$surface,'personnes'=>$personnes,'chauffage'=>$chauffage,
        'codepostal'=>$cp,'pdl'=>$pdl,'pce'=>$pce
      ),
      'source_page' => 'comparateur-energie-electricite-gaz',
      'source_post_id' => sanitize_text_field($data['src_post'] ?? '')
    ))
  ));

  wp_send_json_success(array('status'=>'ok','email_sent'=>$mail_ok,'gas'=>$gas_result));
}
endif;
add_action('wp_ajax_cme_cmp_lead','cme_cmp_handle_lead');
add_action('wp_ajax_nopriv_cme_cmp_lead','cme_cmp_handle_lead');

// ── Fraicheur des prix d'offres de marche (concurrents ELEC/GAZ) ─────────────
// Ces prix (tableaux ELEC/GAZ ci-dessous, hors offres de reference EDF/CRE
// qui sont desormais branchees en live sur indicateurs_reglementaires, voir
// tracking-api/server.py) ne peuvent PAS etre automatises : aucune API
// publique fiable n'existe pour les offres de marche des fournisseurs
// (restriction confirmee le 16/11/2026, demande operateur). Ils doivent donc
// etre revus et mis a jour MANUELLEMENT par l'operateur a un rythme
// trimestriel -- mettre a jour cette date a CHAQUE verification manuelle
// (meme si aucun prix n'a change), c'est elle qui alimente le rappel
// automatique : scripts-maintenance/verifier_fraicheur_prix_marche_comparateur.py
// + .github/workflows/verif-fraicheur-prix-comparateur.yml (echoue
// visiblement dans l'onglet Actions une fois le seuil trimestriel depasse).
if(!defined('CME_CMP_PRIX_MARCHE_DERNIERE_VERIF')) define('CME_CMP_PRIX_MARCHE_DERNIERE_VERIF','2026-11-16');

if(!function_exists('cme_comp_sc')):
function cme_comp_sc($atts){
$atts=shortcode_atts(['energie'=>'dual'],$atts);
$eg=esc_attr($atts['energie']);
$uid='cme'.uniqid();
$cmp_nonce=wp_create_nonce('cme_cmp_lead_nonce');
$cmp_ajax=esc_js(admin_url('admin-ajax.php'));
// Piege WordPress classique evite ici : NE PAS appeler wp_enqueue_style()/
// wp_enqueue_script() depuis ce callback -- le shortcode est evalue pendant
// le rendu de the_content(), donc APRES que wp_head() (et wp_print_styles(),
// hook sur wp_head) ait deja tourne. Un enqueue de style a ce moment n'est
// alors jamais imprime (pas de 2e passage de wp_print_styles en pied de
// page dans la plupart des themes) -- bug silencieux classique. Voir
// cme_cmp_enqueue_assets() plus bas (hook wp_enqueue_scripts, qui tourne
// bien avant wp_head()) pour l enqueue reel ; ce callback ne fait que
// renvoyer le marqueur HTML.
return '<div id="'.esc_attr($uid).'" class="cme-comp" data-eg="'.esc_attr($eg).'" data-cme-nonce="'.esc_attr($cmp_nonce).'" data-ajax="'.esc_attr($cmp_ajax).'"><p style="color:#9ca3af;font-size:14px;padding:1rem">⏳ Chargement...</p></div>';
}

endif;
add_shortcode('comparateur_energie','cme_comp_sc');

if(!function_exists('cme_cmp_enqueue_assets')):
function cme_cmp_enqueue_assets(){
  global $post;
  // Charge sur les pages qui contiennent reellement le shortcode, ET depuis
  // le 16/11/2026 sur CHAQUE article (is_singular('post')) meme sans
  // shortcode dans le contenu stocke -- demande operateur : remplacer le 1er
  // mini-formulaire periodique "contact-expert-inline" par ce comparateur,
  // insere cote CLIENT par wordpress-mu-plugins/cme-cta-progressifs.php, sur
  // tous les articles anciens et nouveaux (meme principe de couverture
  // retroactive "gratuite" deja etabli pour contact-expert-inline -- aucune
  // reecriture du contenu stocke de chaque article). En dehors des articles
  // et des pages a shortcode reel, rien n est charge -- toujours pas de poids
  // inutile sur le reste du site.
  $a_le_shortcode = ($post instanceof WP_Post) && has_shortcode($post->post_content, 'comparateur_energie');
  $est_un_article = is_singular('post');
  if (!$a_le_shortcode && !$est_un_article) return;
  $assets_dir = plugin_dir_path(__FILE__).'assets/';
  $assets_url = plugins_url('assets/', __FILE__);
  $css_file = $assets_dir.'comparateur-energie.css';
  $js_file  = $assets_dir.'comparateur-energie.js';
  // Version = date de modification du fichier -> cache-bust automatique a
  // chaque mise a jour de l asset (upload cPanel), sans etape manuelle a
  // retenir -- meme philosophie que CME_CMP_PRIX_MARCHE_DERNIERE_VERIF plus
  // haut (un oubli possible pour un rappel humain, mais ici c est le
  // filesystem qui fournit la valeur, donc aucun oubli possible).
  $css_ver = file_exists($css_file) ? filemtime($css_file) : null;
  $js_ver  = file_exists($js_file)  ? filemtime($js_file)  : null;
  wp_enqueue_style('cme-comparateur-energie', $assets_url.'comparateur-energie.css', array(), $css_ver);
  wp_enqueue_script('cme-comparateur-energie', $assets_url.'comparateur-energie.js', array(), $js_ver, true);
  // Nonce/URL ajax exposes en global JS (window.CME_CMP_BOOT) pour
  // l'instance inseree cote client par cme-cta-progressifs.php, qui n'a pas
  // de marqueur PHP (le vrai shortcode porte deja son propre nonce en
  // attribut data-* sur son marqueur HTML -- inutile pour ce cas-la, mais
  // localiser systematiquement est sans risque et plus simple que de
  // distinguer les deux cas ici).
  wp_localize_script('cme-comparateur-energie', 'CME_CMP_BOOT', array(
    'nonce' => wp_create_nonce('cme_cmp_lead_nonce'),
    'ajax'  => admin_url('admin-ajax.php'),
  ));
}
endif;
add_action('wp_enqueue_scripts','cme_cmp_enqueue_assets');
