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
 * CORRECTIF du 19/10/2026 (v2), suite a un premier test reel en prod :
 * dataLayerPush() fonctionnait (generate_lead/click_to_call bien visibles
 * et marquables comme Key Event dans GA4), mais AUCUNE ligne n'arrivait
 * dans leads_convertis -- 0 malgre un clic tel: et une soumission de
 * formulaire reels. Deux causes cumulees, corrigees ici :
 *   1) navigator.sendBeacon() envoyait directement vers le domaine Cloud
 *      Run (cme-tracking-api-...run.app), donc en cross-origin, avec un
 *      Content-Type application/json -- non "CORS-safelisted", ce qui
 *      exige un preflight que sendBeacon ne gere pas de maniere fiable
 *      (la requete ne partait tout simplement jamais du navigateur dans ce
 *      cas, silencieusement, le tout etant avale par les try/catch).
 *      Corrige en faisant poster le JS en SAME-ORIGIN vers un relais REST
 *      WordPress (/wp-json/cme/v1/log-lead, ci-dessous), qui republie
 *      cote serveur (PHP, wp_remote_post) vers l'API Cloud Run -- aucun
 *      CORS possible sur une requete same-origin, quel que soit son
 *      Content-Type. Au passage, c'est le mode d'appel pour lequel
 *      /api/log-lead avait ete concu a l'origine (cf. commentaire de
 *      tracking-api/server.py : "Appele server-side depuis les handlers
 *      PHP WordPress (pas de JS direct)") -- notre v1 avait devie de ce
 *      contrat sans le corriger cote serveur.
 *   2) Le formulaire #472 redirige vers une page de confirmation dediee
 *      (/demande-confirmee/) plutot que d'afficher un message inline --
 *      ni l'evenement jQuery wpformsAjaxSubmitSuccess ni le
 *      MutationObserver (qui observent tous les deux la page d'origine)
 *      n'ont donc l'occasion de se declencher avant que le navigateur ne
 *      quitte la page. Ajout d'une 3e detection, plus fiable pour ce cas
 *      precis : au chargement de /demande-confirmee/ elle-meme.
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

define('CME_TRACKING_API_URL', 'https://cme-tracking-api-217943559750.europe-west1.run.app/api/log-lead');

// ── Relais server-side : le JS ci-dessous poste ICI (same-origin, sous
// wp-json), et ce relais republie vers l'API Cloud Run. Elimine tout
// probleme de CORS/preflight cote navigateur (voir correctif #1 ci-dessus).
add_action('rest_api_init', function () {
    register_rest_route('cme/v1', '/log-lead', [
        'methods'             => 'POST',
        'callback'            => 'cme_relayer_log_lead',
        // Public et sans etat, comme l'etait l'appel direct au Cloud Run
        // depuis le JS auparavant -- aucune donnee plus sensible qu'avant,
        // aucune auth requise cote WordPress non plus pour ce relais.
        'permission_callback' => '__return_true',
    ]);
});

function cme_relayer_log_lead(WP_REST_Request $request) {
    $payload = $request->get_body();
    wp_remote_post(CME_TRACKING_API_URL, [
        'headers'  => ['Content-Type' => 'application/json'],
        'body'     => $payload,
        'timeout'  => 5,
        // Fire-and-forget : on ne fait pas attendre le navigateur la reponse
        // de l'API Cloud Run, le tracking est best-effort par design.
        'blocking' => false,
    ]);
    return new WP_REST_Response(['status' => 'ok'], 200);
}

add_action('wp_footer', function () {
    echo "<script id=\"cme-tracking-conversion\">\n";
    echo <<<'JS'
(function () {
  'use strict';

  // Same-origin desormais (relais PHP ci-dessus) -- plus aucun souci CORS
  // possible quel que soit le Content-Type envoye.
  var TRACK_API = '/wp-json/cme/v1/log-lead';

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
      // sendBeacon d'abord : un clic tel: ou une redirection declenchent
      // souvent une navigation immediate qui peut interrompre un fetch
      // classique avant qu'il ne parte -- sendBeacon est concu pour
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

  // ── SOUMISSION DU FORMULAIRE DE CONTACT (WPForms) ──────────────────────────
  var FORMULAIRE_DEJA_TRACKE = {};
  function surSoumissionFormulaire(formId) {
    var cle = String(formId || 'inconnu');
    if (FORMULAIRE_DEJA_TRACKE[cle]) { return; }   // evite un double comptage si plusieurs voies se declenchent
    FORMULAIRE_DEJA_TRACKE[cle] = true;
    dataLayerPush({ event: 'generate_lead', form_id: cle, form_type: 'contact-expert' });
    journaliser({ tool: 'contact-expert-formulaire', details: JSON.stringify({ form_id: cle }) });
  }

  // Voie 1 : evenement jQuery officiel de WPForms sur soumission AJAX reussie
  // (ne se declenche que si la confirmation est un message inline, pas une
  // redirection -- voir voie 3 ci-dessous pour ce dernier cas).
  try {
    if (window.jQuery) {
      window.jQuery(document).on('wpformsAjaxSubmitSuccess', function (event, formId) {
        surSoumissionFormulaire(formId);
      });
    }
  } catch (e) {}

  // Voie 2 : repli par observation du DOM de la page d'origine (meme
  // limite que la voie 1 face a une redirection).
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

  // Voie 3 (ajoutee suite au test du 19/10) : la confirmation du formulaire
  // #472 redirige reellement vers /demande-confirmee/ -- la page d'origine
  // est quittee avant que les voies 1/2 ne puissent reagir. On detecte donc
  // aussi l'arrivee sur cette page de confirmation elle-meme, avec une garde
  // sessionStorage pour ne pas recompter un rechargement manuel de la page.
  try {
    if (window.location.pathname.indexOf('/demande-confirmee') !== -1) {
      var dejaConfirme = false;
      try { dejaConfirme = sessionStorage.getItem('cme_lead_confirme') === '1'; } catch (e) {}
      if (!dejaConfirme) {
        try { sessionStorage.setItem('cme_lead_confirme', '1'); } catch (e) {}
        surSoumissionFormulaire('472-page-confirmation');
      }
    }
  } catch (e) {}
})();
JS;
    echo "\n</script>\n";
});
