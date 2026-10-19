<?php
/**
 * Plugin Name: CME - Tracking de conversion (formulaire contact + appel)
 * Description: Journalise deux evenements de conversion qui n'etaient suivis
 * nulle part depuis la migration des CTA vers /contactez-un-expert/ (oct.
 * 2026) : la soumission reussie du formulaire de contact (WPForms, #472) et
 * le clic sur un lien tel: (numero du header, present sur tout le site).
 * Pousse un evenement dataLayer (pour GA4/GTM) ET journalise cote serveur
 * dans la meme table BigQuery que les 3 anciens simulateurs
 * (leads_convertis, via /api/log-lead) pour un suivi independant de GA4.
 * Fichier distinct de cme-cta-progressifs.php : portee differente (tracking,
 * pas insertion de CTA), site entier et non limitee aux articles -- pour ne
 * pas melanger deux responsabilites dans le meme fichier.
 *
 * DEPLOIEMENT : comme cme-cta-progressifs.php, ce fichier n'est PAS
 * versionne automatiquement sur le serveur. Apres toute modification :
 * telecharger (cloudshell download), renommer l'ancien en .bak horodate en
 * cPanel, uploader le nouveau dans /wp-content/mu-plugins/, purger les deux
 * caches LiteSpeed (cPanel + wp-admin), verifier avec ?t=$RANDOM.
 */
if (!defined('ABSPATH')) {
    exit;
}

add_action('wp_footer', function () {
    echo "<script id=\"cme-tracking-conversion\">\n";
    echo <<<'JS'
(function () {
  'use strict';

  var TRACK_API = 'https://cme-tracking-api-217943559750.europe-west1.run.app/api/log-lead';

  function dataLayerPush(obj) {
    try {
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push(obj);
    } catch (e) {}
  }

  function journaliser(payload) {
    try {
      payload.timestamp = new Date().toISOString();
      payload.source_page = window.location.href;
      payload.user_agent = (navigator.userAgent || '').slice(0, 120);
      var body = JSON.stringify(payload);
      // sendBeacon d'abord : un clic tel: declenche souvent une navigation
      // immediate (ouverture de l'app telephone) qui peut interrompre un
      // fetch classique avant qu'il ne parte -- sendBeacon est concu pour
      // survivre a ce cas. Repli sur fetch keepalive si indisponible.
      if (navigator.sendBeacon) {
        var blob = new Blob([body], { type: 'application/json' });
        navigator.sendBeacon(TRACK_API, blob);
      } else if (window.fetch) {
        fetch(TRACK_API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body, keepalive: true }).catch(function () {});
      }
    } catch (e) {}
  }

  // ── CLIC SUR LE NUMERO DE TELEPHONE (tel:, n'importe ou sur le site) ──────
  function surClicDocument(evt) {
    try {
      var lien = evt.target.closest ? evt.target.closest('a[href^="tel:"]') : null;
      if (!lien) { return; }
      var numero = lien.getAttribute('href').replace(/^tel:/, '');
      dataLayerPush({ event: 'click_to_call', phone_number: numero });
      journaliser({ tool: 'appel-telephone', telephone: numero });
    } catch (e) {}
  }
  document.addEventListener('click', surClicDocument, true);

  // ── SOUMISSION DU FORMULAIRE DE CONTACT (WPForms, AJAX) ────────────────────
  var FORMULAIRE_DEJA_TRACKE = {};
  function surSoumissionFormulaire(formId) {
    var cle = String(formId || 'inconnu');
    if (FORMULAIRE_DEJA_TRACKE[cle]) { return; }   // evite un double comptage si l'evenement se declenche deux fois
    FORMULAIRE_DEJA_TRACKE[cle] = true;
    dataLayerPush({ event: 'generate_lead', form_id: cle, form_type: 'contact-expert' });
    journaliser({ tool: 'contact-expert-formulaire', details: JSON.stringify({ form_id: cle }) });
  }

  // Voie principale : evenement jQuery officiel de WPForms sur soumission AJAX reussie.
  try {
    if (window.jQuery) {
      window.jQuery(document).on('wpformsAjaxSubmitSuccess', function (event, formId) {
        surSoumissionFormulaire(formId);
      });
    }
  } catch (e) {}

  // Repli : si jQuery/l'evenement WPForms venait a changer, on observe aussi
  // l'apparition du message de confirmation dans le DOM (comportement WPForms
  // par defaut : .wpforms-confirmation-container-full remplace le formulaire).
  try {
    if (window.MutationObserver) {
      var observateur = new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
          var ajoutes = mutations[i].addedNodes || [];
          for (var j = 0; j < ajoutes.length; j++) {
            var noeud = ajoutes[j];
            if (noeud.nodeType !== 1) { continue; }
            if (noeud.classList && noeud.classList.contains('wpforms-confirmation-container-full')) {
              var conteneur = noeud.closest ? noeud.closest('[id^="wpforms-"]') : null;
              var id = conteneur ? (conteneur.id || '').replace('wpforms-', '') : 'inconnu';
              surSoumissionFormulaire(id);
            }
          }
        }
      });
      observateur.observe(document.body, { childList: true, subtree: true });
    }
  } catch (e) {}
})();
JS;
    echo "\n</script>\n";
});
