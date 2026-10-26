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
 *
 * AJOUT DU 26/10/2026 (cartographie des clics -- demande operateur) : relais
 * + tracker generique de clics a l'interieur du contenu des articles (liens
 * internes/externes, images), distinct du tracking lead/tel: ci-dessus.
 * Voir CLAUDE.md section "Cartographie des clics et progression du
 * formulaire" pour le detail complet (schema BigQuery, raison du choix
 * d'un lot bufferise plutot qu'un appel par clic, etc.). Necessite le
 * redeploiement de tracking-api (nouvelle route /api/log-interaction) ET
 * la creation prealable de la table interactions_contenu
 * (scripts-maintenance/creer_table_interactions_contenu.py, DDL -- a
 * executer une seule fois avant le premier deploiement de ce fichier).
 */
if (!defined('ABSPATH')) {
    exit;
}

define('CME_TRACKING_API_URL', 'https://cme-tracking-api-217943559750.europe-west1.run.app/api/log-lead');

// Onglet Google Sheets dedie aux leads du mini-formulaire integre aux
// articles (22/10/2026, voir cme-cta-progressifs.php et CLAUDE.md section
// "Formulaire de contact progressif"). Meme principe que les 3 anciens
// simulateurs (wordpress-plugins/simulateur-*, apps-scripts/cme-*-leads.gs) :
// relais server-side via wp_remote_get vers une Apps Script Web App, qui
// ecrit dans le classeur partage (onglet "Leads Formulaire Article").
// Deployee et URL renseignee le 22/10/2026.
define('CME_APPS_SCRIPT_LEADS_INLINE_URL', 'https://script.google.com/macros/s/AKfycbxpzUna-KBj6kpASyufpeAz0rF2C-lXFHSAjpUGiHnrqpTujYsLnUZi9aJlQrHciSThxA/exec');

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
    // CORRECTIF du 19/10 (v3) : un 2e test reel (apres le relais same-origin
    // de la v2) montre toujours 0 ligne en base, alors que cette route
    // WordPress repond bien 200 OK -- la panne est donc dans cet appel
    // sortant lui-meme (wp_remote_post vers Cloud Run), invisible jusqu'ici
    // car 'blocking' => false avalait silencieusement toute erreur. Passe en
    // bloquant (sans impact visiteur : c'est un appel serveur-a-serveur en
    // arriere-plan, pas le JS du navigateur) et journalise le resultat dans
    // un transient interne (plus expose par aucune route REST depuis le
    // 26/10/2026 -- voir plus bas, l'endpoint public /log-lead-debug qui le
    // lisait a ete retire une fois l'incident du 19/10 reellement resolu).
    $reponse = wp_remote_post(CME_TRACKING_API_URL, [
        'headers'  => ['Content-Type' => 'application/json'],
        'body'     => $payload,
        'timeout'  => 8,
        'blocking' => true,
    ]);

    if (is_wp_error($reponse)) {
        set_transient('cme_tracking_last_error', 'WP_Error: ' . $reponse->get_error_message(), HOUR_IN_SECONDS);
    } else {
        $code = wp_remote_retrieve_response_code($reponse);
        $corps = wp_remote_retrieve_body($reponse);
        set_transient(
            'cme_tracking_last_error',
            ($code === 200 ? 'OK' : "HTTP $code") . ' @ ' . current_time('mysql') . ' -- ' . substr($corps, 0, 300),
            HOUR_IN_SECONDS
        );
    }

    // Relais secondaire vers Google Sheets, UNIQUEMENT pour les leads du
    // mini-formulaire integre aux articles (22/10/2026) -- pas pour les
    // clics tel: ni les soumissions du formulaire /contactez-un-expert/,
    // qui ne passaient pas deja par un Sheet et ne doivent pas commencer a
    // y arriver sans l'avoir demande. Meme forme d'appel que l'existant
    // wordpress-plugins/simulateur-solaire/simulateur-solaire.php (wp_remote_get
    // avec payload en query string, bloquant -- invisible pour le visiteur,
    // c'est un appel serveur-a-serveur en arriere-plan comme celui ci-dessus).
    if (CME_APPS_SCRIPT_LEADS_INLINE_URL) {
        $donnees = json_decode($payload, true);
        if (is_array($donnees) && ($donnees['tool'] ?? '') === 'contact-expert-inline') {
            wp_remote_get(
                CME_APPS_SCRIPT_LEADS_INLINE_URL . '?payload=' . rawurlencode($payload),
                ['timeout' => 20, 'blocking' => true, 'sslverify' => false]
            );
        }
    }

    return new WP_REST_Response(['status' => 'ok'], 200);
}

// ── Relais pour le nouveau tracker de clics/contenu (26/10/2026) : meme
// principe que log-lead (same-origin -> republication server-side vers
// Cloud Run), mais recoit un LOT d'evenements (tableau JSON) en un seul
// appel, pas un evenement a la fois -- le JS bufferise cote navigateur.
add_action('rest_api_init', function () {
    register_rest_route('cme/v1', '/log-interaction', [
        'methods'             => 'POST',
        'callback'            => 'cme_relayer_log_interaction',
        'permission_callback' => '__return_true',
    ]);
});

define('CME_TRACKING_API_INTERACTION_URL', 'https://cme-tracking-api-217943559750.europe-west1.run.app/api/log-interaction');

function cme_relayer_log_interaction(WP_REST_Request $request) {
    wp_remote_post(CME_TRACKING_API_INTERACTION_URL, [
        'headers'  => ['Content-Type' => 'application/json'],
        'body'     => $request->get_body(),
        'timeout'  => 8,
        // Volume potentiellement plus eleve que log-lead (plusieurs
        // evenements par visite d'article, pas uniquement a la conversion) --
        // non-bloquant ici pour ne pas ralentir la reponse au navigateur,
        // a la difference de log-lead qui avait besoin du mode bloquant
        // pour diagnostiquer l'incident du 19/10. Pas de donnee personnelle
        // en jeu dans ce flux (pas de nom/telephone), impact limite si une
        // requete se perd silencieusement.
        'blocking' => false,
    ]);
    return new WP_REST_Response(['status' => 'ok'], 200);
}

// L'endpoint public de diagnostic /wp-json/cme/v1/log-lead-debug (ajoute
// pendant l'incident IAM du 19/10, voir CLAUDE.md) a ete retire le
// 26/10/2026 -- l'incident est resolu depuis longtemps et un endpoint
// public inutile, meme sans donnee personnelle, n'a plus de raison de
// rester expose. Le transient cme_tracking_last_error continue d'etre
// ecrit ci-dessus (bookkeeping interne, plus aucune route ne le lit).

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

// ── CARTOGRAPHIE DES CLICS DANS LE CONTENU DES ARTICLES (26/10/2026) ───────
// Scope volontairement limite a is_singular('post') : la notion de "zone de
// contenu" (section, mots avant le clic) n'a de sens que dans un article,
// pas sur les pages outils/accueil. Buffer + envoi en lot (sendBeacon) sur
// masquage/fermeture de la page plutot qu'un appel par clic, pour rester a
// un volume de requetes raisonnable sur une visite qui peut cliquer sur
// plusieurs liens internes dans le meme article.
add_action('wp_footer', function () {
    if (!is_singular('post')) {
        return;
    }
    echo "<script id=\"cme-tracking-clics-contenu\">\n";
    echo <<<'JS'
(function () {
  'use strict';
  var API_INTERACTION = '/wp-json/cme/v1/log-interaction';
  var FILE = [];
  // Identifiant anonyme de CETTE visite de page (pas de cookie, pas de
  // persistance entre pages) -- sert uniquement a regrouper les evenements
  // d'un meme lot, pas a suivre un visiteur dans le temps.
  var SESSION_ID = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);

  function pourcentageScroll() {
    try {
      var h = document.documentElement;
      var total = h.scrollHeight - h.clientHeight;
      return total > 0 ? Math.round((h.scrollTop || window.scrollY || 0) / total * 100) : 0;
    } catch (e) { return 0; }
  }

  function empiler(evt) {
    try {
      evt.timestamp = new Date().toISOString();
      evt.session_id = SESSION_ID;
      evt.source_page = window.location.href;
      evt.source_post_id = String(window.CME_POST_ID || '');
      evt.user_agent = (navigator.userAgent || '').slice(0, 120);
      FILE.push(evt);
      if (FILE.length >= 20) { vider(); }   // garde-fou taille de lot
    } catch (e) {}
  }

  function vider() {
    try {
      if (!FILE.length) { return; }
      var lot = FILE.slice();
      FILE.length = 0;
      var body = JSON.stringify(lot);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(API_INTERACTION, new Blob([body], { type: 'application/json' }));
      } else if (window.fetch) {
        fetch(API_INTERACTION, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body, keepalive: true }).catch(function () {});
      }
    } catch (e) {}
  }

  // Filet de securite : vide le buffer meme sur une tres longue lecture
  // sans changement de visibilite (rare, mais le volume reste negligeable).
  window.setInterval(vider, 15000);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') { vider(); }
  });
  window.addEventListener('pagehide', vider);

  function texteTronque(el, max) {
    var t = (el && (el.textContent || el.getAttribute('alt') || '') || '').trim().replace(/\s+/g, ' ');
    return t.length > max ? t.slice(0, max) + '…' : t;
  }

  // Section = texte du dernier titre h2/h3 rencontre avant l'element, en
  // parcourant les freres precedents puis en remontant -- approximation
  // simple, suffisante pour savoir "dans quelle partie de l'article".
  function sectionDe(el) {
    try {
      var zone = el.closest ? el.closest('.entry-content') : null;
      if (!zone) { return ''; }
      var courant = el;
      while (courant && courant !== zone) {
        var frere = courant.previousElementSibling;
        while (frere) {
          if (/^H[23]$/.test(frere.tagName)) { return texteTronque(frere, 100); }
          frere = frere.previousElementSibling;
        }
        courant = courant.parentElement;
      }
      return '';
    } catch (e) { return ''; }
  }

  // Mots avant = taille approximative (en mots) du texte de .entry-content
  // precedant l'element clique -- proxy de "position dans l'article".
  function motsAvant(el) {
    try {
      var zone = el.closest ? el.closest('.entry-content') : null;
      if (!zone) { return 0; }
      var range = document.createRange();
      range.setStart(zone, 0);
      range.setEndBefore(el);
      var texte = range.toString().trim();
      return texte ? texte.split(/\s+/).length : 0;
    } catch (e) { return 0; }
  }

  function prefixeSilo() {
    return window.location.pathname.split('/').filter(Boolean)[0] || '';
  }

  document.addEventListener('click', function (evt) {
    try {
      var cible = evt.target.closest ? evt.target.closest('.entry-content a[href], .entry-content img') : null;
      if (!cible) { return; }
      var zone = cible.closest('.entry-content');
      if (!zone) { return; }

      var type, texte;
      if (cible.tagName === 'IMG') {
        type = 'image';
        texte = texteTronque(cible, 150) || (cible.getAttribute('alt') || '').slice(0, 150);
      } else {
        var href = cible.getAttribute('href') || '';
        type = /^https?:\/\//i.test(href) && href.indexOf(window.location.hostname) === -1 ? 'lien_externe' : 'lien_interne';
        texte = texteTronque(cible, 150);
      }

      empiler({
        type_evenement: 'clic_contenu',
        cible: type,
        section: sectionDe(cible),
        texte: texte,
        position_contenu: motsAvant(cible),
        scroll_pct: pourcentageScroll(),
        silo: prefixeSilo()
      });
    } catch (e) {}
  }, true);
})();
JS;
    echo "\n</script>\n";
});
