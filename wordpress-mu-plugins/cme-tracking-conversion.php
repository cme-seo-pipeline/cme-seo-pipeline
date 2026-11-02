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
 *
 * AJOUT DU 01/11/2026 (demande operateur) : capturer aussi le TEMPS ecoule
 * depuis le chargement de la page, pas seulement la position en mots/scroll
 * -- pour decider ou/quand placer le 1er formulaire (ex. hypothese
 * "apres ~15 secondes de lecture, soit ~150 mots"). La position seule ne
 * dit rien sur la vitesse de lecture reelle des visiteurs. Deux ajouts :
 *   1) `temps_ms` sur chaque evenement clic_contenu existant.
 *   2) Nouveau tracker 'lecture_position' : jalons de lecture (tous les
 *      100 mots lus environ, pas un echantillonnage par intervalle de
 *      temps -- plus pertinent pour correler position et temps), avec le
 *      temps ecoule a chaque jalon. Voir CLAUDE.md pour le detail.
 * Necessite la colonne `temps_ms` sur interactions_contenu
 * (scripts-maintenance/ajouter_colonne_temps_ms_interactions.py, ALTER
 * TABLE idempotent -- a executer une seule fois avant ce deploiement).
 *
 * AJOUT DU 01/11/2026, suite (demande operateur) : le relais Sheets ci-dessous
 * (cme_relayer_log_lead(), voir plus bas) accepte desormais aussi
 * `tool = 'appel-expert-inline'` -- le nouveau mini-formulaire "avant
 * d'appeler" de cme-cta-progressifs.php (meme perimetre articles, memes
 * champs nom/prenom+telephone, mais la derniere etape devient un bouton
 * tel: reel plutot qu'un message "merci"). Decision operateur explicite :
 * ces leads doivent arriver dans le MEME onglet Google Sheets que le
 * formulaire de contact, avec source_page et le tracking habituel -- pas de
 * nouvel onglet ni de nouveau relais, simple elargissement du filtre
 * existant. Le numero affiche en header/footer n'est pas concerne (reste un
 * lien tel: direct, inchange) : seul le tracking generique "clic sur
 * n'importe quel tel:" plus bas (tool='appel-telephone', sans nom/telephone
 * saisis) continue de s'appliquer a ce numero, comme avant.
 *
 * AJOUT DU 01/11/2026, suite (revirement demande operateur) : le point
 * ci-dessus ("le numero du header reste un lien direct, inchange") est
 * invalide par une demande operateur explicite et contraire, formulee
 * juste apres avoir teste le point precedent en prod -- le bouton du
 * header DOIT desormais etre intercepte lui-meme. Voir plus bas, section
 * "POPUP APPEL SUR LE BOUTON DU HEADER" : clic sur un lien tel: a
 * l'interieur de `.header-widget` -> popup formulaire (nom+telephone+RGPD,
 * un seul ecran, pas de pas-a-pas) -> bouton "Appeler" qui envoie le lead
 * (`tool = 'appel-header-formulaire'`, ajoute au meme filtre Sheets que
 * ci-dessus) puis declenche l'appel reel. Scope explicitement demande :
 * tout le site (le widget header apparait sur toutes les pages, pas
 * seulement les articles) -- d'ou l'implementation ici plutot que dans
 * cme-cta-progressifs.php (limite aux articles). Le nouveau bloc "avant
 * d'appeler" en fin d'article (cme-cta-progressifs.php, voir plus haut)
 * N'A PAS ete retire : l'operateur n'a pas demande sa suppression, les
 * deux mecanismes coexistent pour l'instant (a retirer si l'operateur le
 * demande apres l'avoir vu en prod).
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

    // Relais secondaire vers Google Sheets -- 'contact-expert-inline'
    // (22/10/2026), 'appel-expert-inline' (01/11/2026), 'appel-header-formulaire'
    // (01/11/2026) et desormais 'contact-expert-formulaire' (02/11/2026,
    // demande operateur explicite : regrouper le vrai formulaire de contact
    // /contactez-un-expert/ dans le MEME onglet que les 3 outils inline --
    // voir CLAUDE.md). Ce dernier n'a de valeur dans le Sheet que depuis le
    // correctif du 02/11 qui capture desormais prenom/telephone/email/
    // code_postal au moment de la soumission (voir capturerChampsFormulaireContact()
    // plus bas) -- avant ce correctif ces 4 champs etaient systematiquement
    // vides, ce qui aurait produit des lignes inutilisables dans ce Sheet.
    // Pas pour les clics tel: directs (tool='appel-telephone'), qui restent
    // anonymes et ne passent pas par ce relais. Meme forme d'appel que
    // l'existant wordpress-plugins/simulateur-solaire/simulateur-solaire.php
    // (wp_remote_get avec payload en query string, bloquant -- invisible
    // pour le visiteur, appel serveur-a-serveur en arriere-plan comme
    // celui ci-dessus).
    if (CME_APPS_SCRIPT_LEADS_INLINE_URL) {
        $donnees = json_decode($payload, true);
        $outil = is_array($donnees) ? ($donnees['tool'] ?? '') : '';
        if (in_array($outil, ['contact-expert-inline', 'appel-expert-inline', 'appel-header-formulaire', 'contact-expert-formulaire'], true)) {
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

  // ── POPUP APPEL SUR LE BOUTON DU HEADER (01/11/2026, demande operateur) ──
  // Le bouton tel: du widget header (zone `.header-widget`, voir CLAUDE.md
  // "Bouton telephone du header") apparait sur TOUTES les pages du site --
  // scope demande explicitement par l'operateur, d'ou l'implementation ici
  // (fichier sitewide) plutot que dans cme-cta-progressifs.php (articles
  // uniquement). Scope par ANCETRE `.header-widget`, jamais par la classe
  // `.btn-cta` seule -- meme piege deja documente (classe de theme
  // partagee, potentiellement plusieurs occurrences sur une page) pour
  // cme-header-tel-style.php. Un seul ecran (pas un pas-a-pas comme le
  // mini-formulaire des articles) : les 2 champs affiches ensemble + case
  // RGPD, bouton "Appeler" explicite (pas "Envoyer") qui capture le lead
  // PUIS declenche l'appel reel -- demande operateur explicite.
  var TEL_HEADER_NUMERO = '+33189713648';       // meme numero que le bouton lui-meme
  var TEL_HEADER_AFFICHAGE = '01 89 71 36 48';
  var URL_CADRE_LEGAL_POPUP = 'https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/';
  var FOND1_POPUP = '#0f172a';
  var FOND2_POPUP = '#1e3a8a';
  var ACCENT_POPUP = '#f59e0b';
  var popupAppelEl = null;

  function prefixeSiloPopup() {
    return window.location.pathname.split('/').filter(Boolean)[0] || '';
  }

  function creerPopupAppel() {
    var overlay = document.createElement('div');
    overlay.id = 'cme-popup-appel';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,.6);z-index:999999;display:none;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;';
    overlay.innerHTML =
      '<div style="background:#fff;border-radius:16px;max-width:380px;width:100%;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.3);">' +
        '<div style="background:linear-gradient(135deg,' + FOND1_POPUP + ',' + FOND2_POPUP + ');padding:18px 20px;position:relative;">' +
          '<button type="button" class="cme-popup-fermer" style="position:absolute;top:8px;right:10px;background:none;border:none;color:rgba(255,255,255,.75);font-size:22px;cursor:pointer;line-height:1;padding:6px;">✕</button>' +
          '<div style="color:#fff;font-weight:700;font-size:16px;padding-right:24px;">📞 Avant d’appeler</div>' +
          '<div style="color:rgba(255,255,255,.8);font-size:12px;margin-top:4px;">Laissez vos coordonnées, un conseiller vous accompagne.</div>' +
        '</div>' +
        '<div style="background:#eff6ff;padding:20px;">' +
          '<label style="display:block;font-weight:700;font-size:13px;color:#111827;margin-bottom:6px;">Nom et prénom</label>' +
          '<input type="text" class="cme-popup-prenom" placeholder="Nom et prénom" style="width:100%;box-sizing:border-box;padding:11px 13px;border:2px solid #e5e7eb;border-radius:9px;font-size:15px;outline:none;margin-bottom:12px;">' +
          '<label style="display:block;font-weight:700;font-size:13px;color:#111827;margin-bottom:6px;">Téléphone</label>' +
          '<input type="tel" class="cme-popup-telephone" placeholder="06 12 34 56 78" style="width:100%;box-sizing:border-box;padding:11px 13px;border:2px solid #e5e7eb;border-radius:9px;font-size:15px;outline:none;margin-bottom:10px;">' +
          '<label style="display:flex;align-items:flex-start;gap:8px;margin-bottom:10px;font-size:12px;color:#6b7280;line-height:1.5;cursor:pointer;">' +
            '<input type="checkbox" class="cme-popup-rgpd" style="margin-top:2px;flex-shrink:0;">' +
            '<span>J’accepte d’être recontacté(e) par un conseiller et le traitement de mes données, conformément à notre <a href="' + URL_CADRE_LEGAL_POPUP + '" target="_blank" rel="noopener" style="color:' + FOND2_POPUP + ';text-decoration:underline;">politique de confidentialité</a>.</span>' +
          '</label>' +
          '<div class="cme-popup-erreur" style="color:#dc2626;font-size:13px;margin-bottom:8px;display:none;"></div>' +
          '<button type="button" class="cme-popup-appeler" style="width:100%;background:' + ACCENT_POPUP + ';color:#1f2937;font-weight:700;font-size:15px;padding:12px;border:none;border-radius:9px;cursor:pointer;">📞 Appeler · ' + TEL_HEADER_AFFICHAGE + '</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(overlay);

    function fermer() { overlay.style.display = 'none'; }
    overlay.querySelector('.cme-popup-fermer').addEventListener('click', fermer);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) { fermer(); } });
    overlay.addEventListener('keydown', function (e) { if (e.key === 'Escape') { fermer(); } });

    overlay.querySelector('.cme-popup-appeler').addEventListener('click', function () {
      var prenom = overlay.querySelector('.cme-popup-prenom').value.trim();
      var telephone = overlay.querySelector('.cme-popup-telephone').value.trim();
      var rgpd = overlay.querySelector('.cme-popup-rgpd').checked;
      var erreurEl = overlay.querySelector('.cme-popup-erreur');
      var erreur = '';
      if (prenom.length < 2) { erreur = 'Entrez vos nom et prénom.'; }
      else if (telephone.replace(/\D/g, '').length < 8) { erreur = 'Numéro invalide.'; }
      else if (!rgpd) { erreur = 'Merci d’accepter la politique de confidentialité pour continuer.'; }
      if (erreur) { erreurEl.textContent = erreur; erreurEl.style.display = 'block'; return; }
      erreurEl.style.display = 'none';

      try {
        var payload = {
          tool: 'appel-header-formulaire',
          prenom: prenom,
          telephone: telephone,
          details: JSON.stringify({ silo: prefixeSiloPopup() }),
          source_post_id: String(window.CME_POST_ID || ''),
          source_page: window.location.href
        };
        var body = JSON.stringify(payload);
        if (navigator.sendBeacon) {
          navigator.sendBeacon(TRACK_API, new Blob([body], { type: 'application/json' }));
        } else if (window.fetch) {
          fetch(TRACK_API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body, keepalive: true }).catch(function () {});
        }
        dataLayerPush({ event: 'generate_lead_appel_header', phone_number: TEL_HEADER_NUMERO });
      } catch (e) {}

      fermer();
      // Appel reel declenche APRES capture du lead -- l'utilisateur garde
      // malgre tout l'impression d'un enchainement immediat (pas d'attente
      // visible, sendBeacon ne bloque pas).
      window.location.href = 'tel:' + TEL_HEADER_NUMERO;
    });

    return overlay;
  }

  function ouvrirPopupAppel() {
    if (!popupAppelEl) { popupAppelEl = creerPopupAppel(); }
    popupAppelEl.style.display = 'flex';
    popupAppelEl.querySelector('.cme-popup-erreur').style.display = 'none';
    popupAppelEl.querySelector('.cme-popup-prenom').value = '';
    popupAppelEl.querySelector('.cme-popup-telephone').value = '';
    popupAppelEl.querySelector('.cme-popup-rgpd').checked = false;
    window.setTimeout(function () { popupAppelEl.querySelector('.cme-popup-prenom').focus(); }, 50);
  }

  // ── CLIC SUR LE NUMERO DE TELEPHONE (tel:, n'importe ou sur le site) ──────
  function surClicDocument(evt) {
    try {
      var lien = evt.target.closest ? evt.target.closest('a[href^="tel:"]') : null;
      if (!lien) { return; }
      var numero = lien.getAttribute('href').replace(/^tel:/, '');
      // Bouton du header (01/11/2026, demande operateur) : CE lien precis
      // (scope par ancetre `.header-widget`) est intercepte par le popup
      // ci-dessus avant de lancer l'appel. Tous les AUTRES liens tel: du
      // site (dont le bouton "Appeler maintenant" du nouveau CTA en fin
      // d'article, cme-cta-progressifs.php, volontairement distinct)
      // gardent le comportement direct existant ci-dessous.
      if (lien.closest('.header-widget')) {
        evt.preventDefault();
        ouvrirPopupAppel();
        return;
      }
      dataLayerPush({ event: 'click_to_call', phone_number: numero });
      journaliser({ tool: 'appel-telephone', telephone: numero });
    } catch (e) {}
  }
  document.addEventListener('click', surClicDocument, true);

  // ── SOUMISSION DU FORMULAIRE DE CONTACT (WPForms) ──────────────────────────
  // CORRECTIF du 02/11/2026 : un double comptage reel a ete confirme en prod
  // (scripts-maintenance/verifier_leads_formulaire_contact_expert.py, 4
  // lignes en base pour 2 soumissions reelles) -- l'hypothese du docblock
  // ("voie 1/2 ne se declenchent que pour une confirmation inline, pas une
  // redirection") etait fausse : l'evenement jQuery wpformsAjaxSubmitSuccess
  // se declenche bel et bien AVANT la redirection vers /demande-confirmee/,
  // avec un formId mal forme ("[object Object]"). La garde en memoire
  // FORMULAIRE_DEJA_TRACKE ne peut pas l'empecher : voie 1 tourne sur la
  // page d'origine, voie 3 sur /demande-confirmee/ -- deux chargements de
  // page distincts, donc deux contextes JS distincts, la variable memoire
  // est reinitialisee entre les deux. Seule une garde PERSISTANTE (meme
  // principe que celle que voie 3 utilisait deja seule, cle
  // sessionStorage) survit a la navigation et deduplique vraiment, quelle
  // que soit la voie qui se declenche en premier.
  var FORMULAIRE_DEJA_TRACKE = {};
  function surSoumissionFormulaire(formId, champsCaptures) {
    var cle = String(formId || 'inconnu');
    if (FORMULAIRE_DEJA_TRACKE[cle]) { return; }   // evite un double declenchement dans la MEME page (voie 1 + voie 2)
    FORMULAIRE_DEJA_TRACKE[cle] = true;
    try {
      if (sessionStorage.getItem('cme_lead_formulaire_contact_trackee') === '1') { return; }
      sessionStorage.setItem('cme_lead_formulaire_contact_trackee', '1');
    } catch (e) {}
    var champs = champsCaptures || {};
    dataLayerPush({ event: 'generate_lead', form_id: cle, form_type: 'contact-expert' });
    journaliser({
      tool: 'contact-expert-formulaire',
      prenom: champs.prenom || '',
      telephone: champs.telephone || '',
      email: champs.email || '',
      code_postal: champs.code_postal || '',
      details: JSON.stringify({ form_id: cle })
    });
  }

  // AJOUT du 02/11/2026 (demande operateur -- regrouper ces leads avec les 3
  // outils inline dans le meme onglet Sheets implique d'avoir les memes
  // champs) : capture nom/telephone/email/code postal depuis le VRAI
  // formulaire WPForms #472 au moment de la soumission -- jusqu'ici le
  // tracking ne faisait que detecter QU'une soumission avait eu lieu, sans
  // jamais lire les valeurs saisies. Capture generique par CLASSE DE CHAMP
  // WPForms (wpforms-field-phone/-email/-name/-text), pas par un nom/id
  // d'input (WPForms les genere de maniere generique et positionnelle,
  // "wpforms[fields][N]", sans rapport avec le type du champ -- seule la
  // classe du conteneur est un signal fiable, independant de la langue des
  // libelles).
  // Capturee au moment du 'submit' natif (capture phase, document), AVANT
  // que WPForms n'intercepte en AJAX -- c'est le seul instant ou les 2
  // voies qui restent sur la page d'origine (1 et 2) peuvent encore lire
  // les valeurs ; la voie 3 (page de confirmation, apres redirection) n'a
  // plus acces au formulaire d'origine, et repart donc sans ces champs --
  // degradation sans casse, strictement pas pire qu'avant ce correctif.
  //
  // CORRECTIF du 03/11/2026, suite a un test reel en navigation privee :
  // le champ "Telephone" du formulaire live n'utilise PAS le type WPForms
  // dedie (pas de classe wpforms-field-phone) -- c'est un champ texte
  // simple, comme le code postal. L'ancienne heuristique "par elimination,
  // le 1er champ texte restant = code_postal" prenait donc le telephone
  // (place avant dans le formulaire) et ecrasait le vrai code postal, qui
  // n'etait jamais capture. Remplace par une detection PAR LE CONTENU de
  // chaque champ texte restant plutot que par sa position : un telephone
  // francais a entre 9 et 14 chiffres, un code postal en a exactement 5 --
  // aucune ambiguite pratique entre les deux formats.
  function estTelephoneProbable(valeur) {
    var chiffres = valeur.replace(/\D/g, '');
    return chiffres.length >= 9 && chiffres.length <= 14;
  }
  function estCodePostalProbable(valeur) {
    return /^\d{5}$/.test(valeur.trim());
  }
  function capturerChampsFormulaireContact(form) {
    var champs = { prenom: '', telephone: '', email: '', code_postal: '' };
    try {
      var texteRestant = [];
      var conteneurs = form.querySelectorAll('.wpforms-field');
      for (var i = 0; i < conteneurs.length; i++) {
        var c = conteneurs[i];
        var cls = c.className || '';
        var champsInput = c.querySelectorAll('input, textarea');
        if (!champsInput.length) { continue; }
        if (cls.indexOf('wpforms-field-phone') !== -1) {
          champs.telephone = (champsInput[0].value || '').trim();
        } else if (cls.indexOf('wpforms-field-email') !== -1) {
          champs.email = (champsInput[0].value || '').trim();
        } else if (cls.indexOf('wpforms-field-name') !== -1) {
          var morceaux = [];
          for (var j = 0; j < champsInput.length; j++) {
            var v = (champsInput[j].value || '').trim();
            if (v) { morceaux.push(v); }
          }
          champs.prenom = morceaux.join(' ');
        } else if (cls.indexOf('wpforms-field-text') !== -1 || cls.indexOf('wpforms-field-number') !== -1) {
          var val = (champsInput[0].value || '').trim();
          if (val) { texteRestant.push(val); }
        }
      }
      // Classe par contenu les champs texte restants (telephone mal type +
      // code postal, typiquement). Priorite au telephone s'il n'a pas deja
      // ete trouve via la classe dediee ci-dessus.
      for (var k = 0; k < texteRestant.length; k++) {
        var valeur = texteRestant[k];
        if (!champs.telephone && estTelephoneProbable(valeur)) {
          champs.telephone = valeur;
        } else if (!champs.code_postal && estCodePostalProbable(valeur)) {
          champs.code_postal = valeur;
        }
      }
      // Filet de securite : un champ texte restant qui ne correspond a
      // aucun des deux formats attendus est tout de meme conserve plutot
      // que perdu silencieusement (ex. code postal non-francais, format
      // inattendu) -- va dans code_postal s'il reste vide, jamais dans
      // telephone pour ne pas re-introduire l'ecrasement corrige ici.
      if (!champs.code_postal) {
        for (var m = 0; m < texteRestant.length; m++) {
          if (texteRestant[m] !== champs.telephone) { champs.code_postal = texteRestant[m]; break; }
        }
      }
    } catch (e) {}
    return champs;
  }

  var DERNIERS_CHAMPS_CAPTURES = {};
  document.addEventListener('submit', function (evt) {
    try {
      var form = evt.target;
      if (!form || !form.id || form.id.indexOf('wpforms-form-') !== 0) { return; }
      DERNIERS_CHAMPS_CAPTURES = capturerChampsFormulaireContact(form);
    } catch (e) {}
  }, true);

  // Voie 1 : evenement jQuery officiel de WPForms sur soumission AJAX reussie
  // (ne se declenche que si la confirmation est un message inline, pas une
  // redirection -- voir voie 3 ci-dessous pour ce dernier cas).
  try {
    if (window.jQuery) {
      window.jQuery(document).on('wpformsAjaxSubmitSuccess', function (event, formId) {
        surSoumissionFormulaire(formId, DERNIERS_CHAMPS_CAPTURES);
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
              surSoumissionFormulaire(id, DERNIERS_CHAMPS_CAPTURES);
            }
          }
        }
      });
      observateur.observe(document.body, { childList: true, subtree: true });
    }
  } catch (e) {}

  // Voie 3 (ajoutee suite au test du 19/10) : la confirmation du formulaire
  // #472 redirige reellement vers /demande-confirmee/ -- la page d'origine
  // est quittee avant que les voies 1/2 ne puissent reagir (ou APRES avoir
  // deja reagi, voir le correctif du 02/11 sur la garde partagee dans
  // surSoumissionFormulaire() ci-dessus, qui deduplique maintenant entre
  // les voies plutot qu'une garde locale ici redondante avec elle).
  try {
    if (window.location.pathname.indexOf('/demande-confirmee') !== -1) {
      surSoumissionFormulaire('472-page-confirmation');
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
  // Reference de temps pour `temps_ms` (01/11/2026) -- a quel point du
  // chargement de la page chaque evenement survient. Date.now() plutot que
  // performance.now() : coherent avec SESSION_ID et le timestamp ISO
  // envoyes par ailleurs, pas besoin de precision sub-ms ici.
  var DEBUT = Date.now();

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
        silo: prefixeSilo(),
        temps_ms: Date.now() - DEBUT
      });
    } catch (e) {}
  }, true);

  // ── JALONS DE LECTURE : position (en mots) ET temps pour y arriver
  // (01/11/2026, demande operateur) ──────────────────────────────────────
  // But : savoir, pour une position donnee (ex. 150 mots), le temps
  // REELLEMENT mis pour l'atteindre -- la position seule (deja captee sur
  // les clics ci-dessus) ne dit rien de la vitesse de lecture. Jalon tous
  // les ~100 mots plutot qu'un intervalle de temps fixe : borne le volume
  // d'evenements a la LONGUEUR de l'article (quelques dizaines max), pas a
  // la duree de la visite (un lecteur qui reste 10 minutes sur place sans
  // avancer ne doit pas generer d'evenements supplementaires).
  var PAS_MOTS = 100;
  var dernierJalon = 0;
  var zoneArticle = null;

  function initJalonsLecture() {
    zoneArticle = document.querySelector('article.type-post .entry-content');
  }

  // Position de lecture approximee par l'element le plus proche du HAUT du
  // viewport (premiere ligne visible = ce que le lecteur est en train de
  // lire), puis motsAvant() sur cet element -- meme technique que pour les
  // clics, appliquee a un point de la zone plutot qu'a l'element clique.
  function elementEnHautDuViewport() {
    try {
      var marge = Math.round(window.innerHeight * 0.2);   // ~20% sous le haut de l'ecran, zone de lecture active
      var noeuds = zoneArticle.querySelectorAll('p, h2, h3, li, blockquote');
      for (var i = 0; i < noeuds.length; i++) {
        var rect = noeuds[i].getBoundingClientRect();
        if (rect.bottom >= marge) { return noeuds[i]; }
      }
      return noeuds.length ? noeuds[noeuds.length - 1] : null;
    } catch (e) { return null; }
  }

  var enAttenteJalon = false;
  function verifierJalonLecture() {
    if (!zoneArticle || enAttenteJalon) { return; }
    enAttenteJalon = true;
    window.requestAnimationFrame(function () {
      enAttenteJalon = false;
      try {
        var el = elementEnHautDuViewport();
        if (!el) { return; }
        var motsLus = motsAvant(el);
        var jalonCourant = Math.floor(motsLus / PAS_MOTS) * PAS_MOTS;
        if (jalonCourant <= dernierJalon) { return; }
        dernierJalon = jalonCourant;
        empiler({
          type_evenement: 'lecture_position',
          position_contenu: jalonCourant,
          scroll_pct: pourcentageScroll(),
          silo: prefixeSilo(),
          temps_ms: Date.now() - DEBUT
        });
      } catch (e) {}
    });
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    initJalonsLecture();
  } else {
    document.addEventListener('DOMContentLoaded', initJalonsLecture);
  }
  window.addEventListener('scroll', verifierJalonLecture, { passive: true });
})();
JS;
    echo "\n</script>\n";
});
