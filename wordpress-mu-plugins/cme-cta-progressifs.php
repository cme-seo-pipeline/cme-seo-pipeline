<?php
/**
 * Plugin Name: CME - Formulaire de contact progressif
 * Description: Insere un mini-formulaire de contact interactif (type Typeform,
 * une question a la fois) environ toutes les 230 mots (~1 minute de lecture)
 * dans le corps de chaque article, avec les couleurs du silo. Remplace les
 * anciens boutons CTA qui renvoyaient vers /contactez-un-expert/ : desormais
 * le visiteur remplit directement un mini-formulaire dans l'article, sans
 * changer de page. Mode apercu par defaut : visible uniquement avec ?cta60=1
 * dans l'URL. Pour desactiver : supprimer ce fichier.
 *
 * CHANTIER DU 22/10/2026 (remplacement bouton -> formulaire) :
 *  - Demande explicite de l'operateur : plus de banniere flottante (Zendure,
 *    app Android -- retirees separement, voir CLAUDE.md), et le bouton CTA
 *    "Contactez un expert" devient un vrai mini-formulaire integre a
 *    l'article, pas juste un lien de plus vers la page de contact.
 *  - Pourquoi pas le shortcode WPForms directement : WordPress/WPForms
 *    decide COTE SERVEUR, avant le rendu de la page, s'il faut charger son
 *    CSS/JS/nonces, en detectant le shortcode dans le contenu stocke de
 *    l'article AU MOMENT DU RENDU. Un shortcode insere cote client par ce
 *    mu-plugin (apres le chargement de la page) arrive trop tard : WPForms
 *    n'aurait jamais chargé ses propres assets, et le formulaire ne
 *    fonctionnerait pas. D'ou un mini-formulaire maison (HTML/CSS/JS pur,
 *    sans dependance), seule option fiable pour une insertion dynamique.
 *  - Ce mecanisme est modulaire (une seule fonction creer() generatrice,
 *    reutilisee a chaque position) et s'applique automatiquement a TOUS
 *    les articles -- anciens et nouveaux -- sans avoir a retoucher le
 *    contenu stocke de chaque article un par un : le cote "retroactif"
 *    demande par l'operateur est couvert par construction, puisque ce
 *    script tourne deja sur chaque page article existante.
 *  - Champs : nom et prenom, telephone -- reduit de 4 a 2 questions le
 *    24/10/2026 a la demande explicite de l'operateur (email et code postal
 *    retires), pour minimiser la friction au remplissage. La case CGU/RGPD
 *    reste sur la derniere etape de saisie (desormais "telephone"). Les
 *    colonnes email/code_postal de leads_convertis et de l'onglet Sheets
 *    restent vides pour ces soumissions (gerees cote serveur sans erreur,
 *    aucune migration necessaire).
 *  - Soumission : poste directement vers le relais deja deploye et deja
 *    valide en prod, /wp-json/cme/v1/log-lead (voir cme-tracking-conversion.php),
 *    qui republie vers l'API Cloud Run -> table leads_convertis. Aucun
 *    nouveau code backend necessaire. tool = 'contact-expert-inline' pour
 *    distinguer ces soumissions des autres (formulaire page de contact,
 *    appel telephonique).
 *  - Cote pipeline.py : l'ancienne insertion de CTA statique a la
 *    publication (inserer_ctas_repartis) a ete desactivee pour les
 *    nouveaux articles, afin de ne pas superposer un vieux bouton statique
 *    ET le nouveau formulaire dynamique sur le meme article. Voir
 *    CLAUDE.md pour le detail et le script de nettoyage retroactif des
 *    anciens boutons deja publies.
 *
 * AJOUT DU 26/10/2026 (progression du formulaire -- demande operateur) :
 * journalise, pour chaque occurrence du formulaire, sa visibilite reelle
 * (IntersectionObserver), la progression etape par etape, et l'abandon
 * eventuel entre l'etape "nom/prenom" et l'etape "telephone" -- donnee
 * absente jusqu'ici (seules les soumissions COMPLETES etaient journalisees,
 * via envoyerLead/log-lead). Meme relais que le nouveau tracker de clics de
 * cme-tracking-conversion.php (/wp-json/cme/v1/log-interaction), buffer
 * local independant (pas de dependance d'ordre de chargement entre les deux
 * fichiers). Voir CLAUDE.md, section "Cartographie des clics et progression
 * du formulaire".
 */
if (!defined('ABSPATH')) {
    exit;
}

add_action('wp_footer', function () {
    if (!is_singular('post')) {
        return;
    }
    // Identifiant de l'article courant, pour l'attribution du lead cote
    // BigQuery (source_post_id) -- seule valeur interpolee cote PHP, le
    // reste du script est un bloc JS statique (nowdoc) plus bas.
    echo "<script id=\"cme-cta-progressifs-data\">var CME_POST_ID=" . (int) get_the_ID() . ";</script>\n";
    echo "<script id=\"cme-cta-progressifs\">\n";
    echo <<<'JS'
(function () {
  'use strict';

  // ── REGLAGES ────────────────────────────────────────────────────────────
  var MODE = 'actif';         // 'apercu' : visible seulement avec ?cta60=1 | 'actif' : tous les visiteurs | 'off'
  var MOTS_PAR_BOUTON = 230;  // environ une minute de lecture
  var MAX_BOUTONS = 30;       // garde-fou technique, au-dessus du maximum attendu (~23)
  var MOTS_FIN_MIN = 120;     // pas de formulaire s'il reste moins de mots que cela
  var API_LEAD = '/wp-json/cme/v1/log-lead';   // relais deja deploye (cme-tracking-conversion.php)

  // Couleurs UNIFIEES sur tout le site (22/10/2026, a la demande du porteur de
  // projet) -- avant, chaque silo avait son propre gradient (bleu/ambre/vert).
  // Desormais une seule identite visuelle, reprise du logo du site (fond
  // navy #0a1120 -> bleu accent #60a5fa) pour que le formulaire soit tout de
  // suite reconnu comme "le site officiel" partout, quel que soit le silo.
  // Bouton d'action en orange/ambre (deja present sur le site, silo aides) :
  // contraste chaud sur fond froid, volontairement different du fond pour
  // que le bouton "ressorte" visuellement -- c'est ce contraste de couleur,
  // pas l'harmonie avec le fond, qui pousse le plus au clic sur un CTA.
  var FORMULAIRE_FOND1 = '#0f172a';     // navy, proche du logo (#0a1120)
  var FORMULAIRE_FOND2 = '#1e3a8a';     // bleu de marque, deja utilise gaz/electricite
  var FORMULAIRE_ACCENT = '#f59e0b';    // ambre, deja utilise silo aides -- couleur du bouton

  var GAZ = { texte: 'Comparez les offres Gaz au meilleur prix' };
  var ELEC = { texte: 'Comparez les offres Électricité au meilleur prix' };
  var AIDES = { texte: 'Calculez vos aides à la rénovation' };
  var SOLAIRE = { texte: 'Estimez votre installation solaire' };
  // ZENDURE (partenariat d'affiliation Awin) et la banniere flottante "app/expert"
  // ont ete retires le 22/10/2026 a la demande explicite du porteur de projet --
  // plus aucune banniere flottante sur le site, quelle qu'elle soit. Le bouton CTA
  // qui renvoyait vers /contactez-un-expert/ est remplace ici par un mini-formulaire
  // integre (voir creer() plus bas) : plus de lien sortant du tout non plus. Code
  // retire reste dans l'historique git si l'un ou l'autre devait reprendre un jour.
  var PAR_PREFIXE = { 'gaz': [GAZ], 'electricite': [ELEC], 'aide-energetique': [AIDES], 'renovation-energetique': [AIDES], 'solaire': [SOLAIRE] };

  // Reduit a 2 questions le 24/10/2026 (demande operateur : minimiser la
  // friction) -- email et code_postal retires. "prenom" porte desormais le
  // nom ET le prenom en un seul champ (cle technique inchangee pour rester
  // compatible avec le schema BigQuery/Sheets existant sans migration).
  var ETAPES = [
    { champ: 'prenom', icone: '👋', label: 'Vos nom et prénom ?', type: 'text', placeholder: 'Nom et prénom' },
    { champ: 'telephone', icone: '📱', label: 'Votre numéro de téléphone ?', type: 'tel', placeholder: '06 12 34 56 78' }
  ];
  // Lien vers la vraie page legale du site, meme URL et meme esprit de formule
  // que les cases RGPD des anciens simulateurs (wordpress-plugins/simulateur-*),
  // pour rester cohérent avec ce qui existe déjà ailleurs sur le site.
  var URL_CADRE_LEGAL = 'https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/';

  // ── OUTILS ──────────────────────────────────────────────────────────────
  function mots(el) {
    var t = (el.textContent || '').trim();
    return t ? t.split(/\s+/).length : 0;
  }
  function estCta(el) {
    return el.tagName === 'DIV' && /linear-gradient/.test(el.getAttribute('style') || '');
  }
  function estVide(el) {
    return el.tagName === 'DIV' && el.children.length === 0 && !(el.textContent || '').trim();
  }
  // Etats :focus/:hover impossibles a poser avec de simples attributs style="" :
  // une petite feuille de style injectee une seule fois (idempotent) pour toute
  // la page, plutot qu'une balise <style> par formulaire. Contribue a la
  // conversion : un champ qui reagit visuellement au clic/survol se sent plus
  // "vivant" et incite davantage a continuer qu'un champ statique.
  function injecterStyles() {
    if (document.getElementById('cme-mf-styles')) { return; }
    var style = document.createElement('style');
    style.id = 'cme-mf-styles';
    style.textContent =
      '.cme-mf-input:focus{border-color:' + FORMULAIRE_FOND2 + '!important;box-shadow:0 0 0 3px rgba(30,58,138,.15)!important;}' +
      '.cme-mf-suiv:hover{background:#d97706!important;}' +
      '.cme-mf-rgpd-case{accent-color:' + FORMULAIRE_FOND2 + ';width:16px;height:16px;}';
    document.head.appendChild(style);
  }

  // ── CARTOGRAPHIE : progression etape par etape + abandon (26/10/2026) ───
  // Buffer local independant de celui de cme-tracking-conversion.php (pas de
  // dependance d'ordre de chargement entre mu-plugins) -- meme principe,
  // meme relais.
  var API_INTERACTION = '/wp-json/cme/v1/log-interaction';
  var FILE_INTERACTIONS = [];
  var SESSION_ID = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  // Dernier etat connu, mis a jour par CHAQUE instance de formulaire sur la
  // page -- sert uniquement a detecter un abandon au moment ou le visiteur
  // quitte/masque la page (on ne sait pas a l'avance lequel des formulaires
  // de la page il a utilise, donc on retient le plus recent).
  var DERNIER_ETAT = null;

  function viderInteractions() {
    try {
      if (!FILE_INTERACTIONS.length) { return; }
      var lot = FILE_INTERACTIONS.slice();
      FILE_INTERACTIONS.length = 0;
      var body = JSON.stringify(lot);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(API_INTERACTION, new Blob([body], { type: 'application/json' }));
      } else if (window.fetch) {
        fetch(API_INTERACTION, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body, keepalive: true }).catch(function () {});
      }
    } catch (e) {}
  }
  function journaliserInteraction(evt) {
    try {
      evt.timestamp = new Date().toISOString();
      evt.session_id = SESSION_ID;
      evt.source_page = window.location.href;
      evt.source_post_id = String(window.CME_POST_ID || '');
      evt.user_agent = (navigator.userAgent || '').slice(0, 120);
      FILE_INTERACTIONS.push(evt);
      if (FILE_INTERACTIONS.length >= 20) { viderInteractions(); }
    } catch (e) {}
  }
  // Enregistre une seule fois (pas par instance de formulaire) : abandon =
  // la derniere etape atteinte etait "telephone" (idx>=1) sans avoir
  // complete (idx < ETAPES.length, donc pas encore arrive a "merci").
  window.setInterval(viderInteractions, 15000);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState !== 'hidden') { return; }
    if (DERNIER_ETAT && DERNIER_ETAT.idx > 0 && DERNIER_ETAT.idx < ETAPES.length) {
      journaliserInteraction({
        type_evenement: 'form_abandon',
        position_contenu: DERNIER_ETAT.position,
        etape: String(DERNIER_ETAT.idx),
        silo: DERNIER_ETAT.silo
      });
      viderInteractions();
      DERNIER_ETAT = null;   // evite un double comptage si la page redevient visible puis se cache encore
    } else {
      viderInteractions();
    }
  });
  window.addEventListener('pagehide', viderInteractions);

  // ── ENVOI DU LEAD (reutilise le relais deja deploye et deja valide en prod) ──
  function envoyerLead(valeurs, position, silo) {
    try {
      var payload = {
        tool: 'contact-expert-inline',
        prenom: valeurs.prenom || '',
        telephone: valeurs.telephone || '',
        details: JSON.stringify({ position: position, silo: silo }),
        source_post_id: String(window.CME_POST_ID || ''),
        source_page: window.location.href
      };
      var body = JSON.stringify(payload);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(API_LEAD, new Blob([body], { type: 'application/json' }));
      } else if (window.fetch) {
        fetch(API_LEAD, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body, keepalive: true }).catch(function () {});
      }
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push({ event: 'generate_lead_inline', position: position, silo: silo });
    } catch (e) {}
  }

  function demarrer() {
    try {
      if (MODE === 'off') { return; }
      if (MODE === 'apercu' && !/[?&]cta60=1(&|$)/.test(window.location.search)) { return; }
      // A partir d'ici, en mode apercu, chaque arret est explique dans la console du navigateur.
      function arret(raison) {
        if (MODE === 'apercu' && window.console) { window.console.log('cme-cta60 : arret, ' + raison); }
      }
      if (!document.body || !document.body.classList.contains('single-post')) { arret('classe single-post absente de <body>'); return; }

      var article = document.querySelector('article.type-post');
      var zone = article ? article.querySelector('.entry-content') : null;
      if (!zone) { arret('article.type-post .entry-content introuvable'); return; }
      if (zone.getAttribute('data-cta60')) { arret('deja execute sur cette page'); return; }

      var prefixe = window.location.pathname.split('/').filter(Boolean)[0];
      var offres = PAR_PREFIXE[prefixe];
      if (!offres || !offres.length) { arret("prefixe d'URL inconnu : " + prefixe); return; }   // pas de formulaire plutot qu'une mauvaise destination
      zone.setAttribute('data-cta60', '1');
      injecterStyles();

      // ── GENERATEUR DE MINI-FORMULAIRE (type Typeform, une question a la fois) ──
      // Une seule fonction, reutilisee a chaque position : c'est ce qui rend ce
      // mecanisme modulaire plutot que de dupliquer du HTML par position.
      function creer(n) {
        var offre = offres[(n - 1) % offres.length];
        var d = document.createElement('div');
        d.className = 'cme-cta60';
        d.setAttribute('data-pos', String(n));
        d.style.cssText = 'background:linear-gradient(135deg,' + FORMULAIRE_FOND1 + ',' + FORMULAIRE_FOND2 + ');border-radius:16px;margin:26px 0;overflow:hidden;clear:both;max-width:100%;box-sizing:border-box;';

        var etapesHtml = ETAPES.map(function (e, i) {
          var derniere = i === ETAPES.length - 1;
          return '<div class="cme-mf-etape" data-champ="' + e.champ + '" style="display:' + (i === 0 ? 'block' : 'none') + ';">' +
            '<label style="display:block;font-weight:700;font-size:15px;color:#111827;margin-bottom:10px;"><span style="font-size:20px;margin-right:8px;">' + e.icone + '</span>' + e.label + '</label>' +
            '<input type="' + e.type + '" class="cme-mf-input" placeholder="' + e.placeholder + '" style="width:100%;box-sizing:border-box;padding:12px 14px;border:2px solid #e5e7eb;border-radius:10px;font-size:16px;outline:none;transition:border-color .15s,box-shadow .15s;">' +
            (derniere ?
              '<label class="cme-mf-rgpd" style="display:flex;align-items:flex-start;gap:8px;margin-top:14px;font-size:12px;color:#6b7280;line-height:1.5;cursor:pointer;">' +
                '<input type="checkbox" class="cme-mf-rgpd-case" style="margin-top:2px;flex-shrink:0;">' +
                '<span>J’accepte d’être recontacté(e) par un conseiller et le traitement de mes données, conformément à notre <a href="' + URL_CADRE_LEGAL + '" target="_blank" rel="noopener" style="color:' + FORMULAIRE_FOND2 + ';text-decoration:underline;">politique de confidentialité</a>.</span>' +
              '</label>'
              : '') +
            '<div class="cme-mf-erreur" style="color:#dc2626;font-size:13px;margin-top:6px;display:none;"></div>' +
          '</div>';
        }).join('');

        d.innerHTML =
          '<div style="padding:18px 20px 10px;">' +
            '<div style="color:#fff;font-weight:700;font-size:16px;margin-bottom:6px;">' + offre.texte + '</div>' +
            '<div style="color:rgba(255,255,255,.8);font-size:12px;margin-bottom:10px;">🔒 Vos données restent confidentielles · un conseiller vous recontacte sous 24h</div>' +
            '<div style="height:4px;background:rgba(255,255,255,.3);border-radius:2px;overflow:hidden;">' +
              '<div class="cme-mf-progres" style="height:100%;width:25%;background:#fff;transition:width .25s;"></div>' +
            '</div>' +
          '</div>' +
          '<div style="background:#fff;padding:20px;">' +
            '<div class="cme-mf-etapes">' + etapesHtml +
              '<div class="cme-mf-etape" data-champ="merci" style="display:none;text-align:center;padding:6px 0;">' +
                '<div style="font-size:28px;">✅</div>' +
                '<div style="font-weight:700;font-size:15px;color:#111827;margin-top:8px;">Merci, un expert vous recontacte rapidement.</div>' +
              '</div>' +
            '</div>' +
            '<div class="cme-mf-nav" style="display:flex;justify-content:space-between;align-items:center;margin-top:16px;gap:10px;">' +
              '<button type="button" class="cme-mf-prec" style="background:none;border:none;color:#6b7280;font-size:14px;font-weight:600;cursor:pointer;padding:8px;visibility:hidden;">← Précédent</button>' +
              '<button type="button" class="cme-mf-suiv" style="background:' + FORMULAIRE_ACCENT + ';color:#1f2937;font-weight:700;font-size:15px;padding:11px 24px;border:none;border-radius:9px;cursor:pointer;white-space:nowrap;">Suivant →</button>' +
            '</div>' +
          '</div>';

        // ── navigation entre etapes (ferme sur d, n, prefixe) ──
        var idx = 0;
        var valeurs = {};
        var noeudsEtapes = Array.prototype.slice.call(d.querySelectorAll('.cme-mf-etape'));
        var barreProgres = d.querySelector('.cme-mf-progres');
        var btnPrec = d.querySelector('.cme-mf-prec');
        var btnSuiv = d.querySelector('.cme-mf-suiv');
        var btnNav = d.querySelector('.cme-mf-nav');

        function inputActif() {
          return noeudsEtapes[idx].querySelector('.cme-mf-input');
        }
        function majProgres() {
          var pct = Math.min(100, Math.round(((idx + 1) / ETAPES.length) * 100));
          barreProgres.style.width = pct + '%';
        }
        function valider(champ, valeur) {
          valeur = (valeur || '').trim();
          if (champ === 'prenom') { return valeur.length >= 2 ? '' : 'Entrez vos nom et prénom.'; }
          if (champ === 'telephone') { return valeur.replace(/\D/g, '').length >= 8 ? '' : 'Numéro invalide.'; }
          return '';
        }
        function afficherErreur(msg) {
          var erreurEl = noeudsEtapes[idx].querySelector('.cme-mf-erreur');
          if (!erreurEl) { return; }
          if (msg) { erreurEl.textContent = msg; erreurEl.style.display = 'block'; }
          else { erreurEl.style.display = 'none'; }
        }
        function afficherEtape(el) {
          // Petite transition d'entree (fade-in) plutot qu'un affichage brut --
          // display reste pilote en JS (simple et fiable), seule l'opacite est
          // animee via la feuille de style partagee / transition inline.
          el.style.display = 'block';
          el.style.opacity = '0';
          window.requestAnimationFrame(function () {
            el.style.transition = 'opacity .2s ease';
            el.style.opacity = '1';
          });
        }
        function allerA(nouvelIdx) {
          noeudsEtapes[idx].style.display = 'none';
          idx = nouvelIdx;
          DERNIER_ETAT = { position: n, idx: idx, silo: prefixe };
          if (idx >= ETAPES.length) {
            journaliserInteraction({ type_evenement: 'form_etape', position_contenu: n, etape: 'termine', silo: prefixe });
            DERNIER_ETAT = null;   // termine : plus rien a detecter comme abandon pour cette instance
            afficherEtape(noeudsEtapes[ETAPES.length]);   // etape "merci"
            btnNav.style.display = 'none';
            barreProgres.style.width = '100%';
            return;
          }
          journaliserInteraction({ type_evenement: 'form_etape', position_contenu: n, etape: String(idx), silo: prefixe });
          afficherEtape(noeudsEtapes[idx]);
          btnPrec.style.visibility = idx === 0 ? 'hidden' : 'visible';
          btnSuiv.textContent = idx === ETAPES.length - 1 ? 'Envoyer →' : 'Suivant →';
          majProgres();
          var inp = inputActif();
          if (inp) { window.setTimeout(function () { inp.focus(); }, 50); }
        }
        function suivant() {
          var champActuel = ETAPES[idx].champ;
          var inp = inputActif();
          var val = inp ? inp.value : '';
          var erreur = valider(champActuel, val);
          if (!erreur && idx === ETAPES.length - 1) {
            var caseRgpd = noeudsEtapes[idx].querySelector('.cme-mf-rgpd-case');
            if (caseRgpd && !caseRgpd.checked) { erreur = 'Merci d’accepter la politique de confidentialité pour continuer.'; }
          }
          if (erreur) { afficherErreur(erreur); return; }
          afficherErreur('');
          valeurs[champActuel] = val.trim();
          if (idx === ETAPES.length - 1) {
            envoyerLead(valeurs, n, prefixe);
            allerA(ETAPES.length);
          } else {
            allerA(idx + 1);
          }
        }
        function precedent() {
          if (idx === 0) { return; }
          allerA(idx - 1);
        }

        btnSuiv.addEventListener('click', suivant);
        btnPrec.addEventListener('click', precedent);
        d.addEventListener('keydown', function (evt) {
          if (evt.key === 'Enter') { evt.preventDefault(); suivant(); }
        });

        majProgres();
        journaliserInteraction({ type_evenement: 'form_etape', position_contenu: n, etape: '0', silo: prefixe });

        // Visibilite reelle (pas juste "present dans le DOM" -- insere via
        // JS, le formulaire existe souvent avant d'etre scrolle en vue) :
        // une seule fois par instance, seuil 50% visible.
        if (window.IntersectionObserver) {
          var observateurVue = new IntersectionObserver(function (entrees) {
            for (var k = 0; k < entrees.length; k++) {
              if (entrees[k].isIntersecting) {
                journaliserInteraction({ type_evenement: 'form_vu', position_contenu: n, silo: prefixe });
                observateurVue.disconnect();
                break;
              }
            }
          }, { threshold: 0.5 });
          window.setTimeout(function () { observateurVue.observe(d); }, 0);   // apres insertion dans le DOM
        }

        return d;
      }

      var enfants = Array.prototype.slice.call(zone.children);
      var i;
      // apres[i] : mots restant apres l'element i avant le prochain formulaire existant (ou la fin)
      var apres = [];
      var acc = 0;
      for (i = enfants.length - 1; i >= 0; i--) {
        apres[i] = acc;
        if (estCta(enfants[i])) { acc = 0; } else { acc += mots(enfants[i]); }
      }

      var cumul = 0;
      var poses = 0;
      for (i = 0; i < enfants.length; i++) {
        var el = enfants[i];
        if (estCta(el)) { cumul = 0; continue; }   // un formulaire existant remet le compteur a zero
        cumul += mots(el);
        if (cumul < MOTS_PAR_BOUTON) { continue; }
        if (poses >= MAX_BOUTONS) { break; }
        if (!/^(P|UL|OL|TABLE|FIGURE|BLOCKQUOTE)$/.test(el.tagName)) { continue; }   // jamais apres un titre, ni au milieu d'un bloc
        var suivantEl = enfants[i + 1];
        if (!suivantEl || estCta(suivantEl) || estVide(suivantEl)) { continue; }
        if (apres[i] < MOTS_FIN_MIN) { continue; }   // trop pres d'un formulaire existant ou de la fin
        zone.insertBefore(creer(poses + 1), suivantEl);
        poses++;
        cumul = 0;
      }

      if (MODE === 'apercu' && window.console) {
        window.console.log('cme-cta60 : ' + poses + ' formulaire(s) pose(s), silo ' + prefixe);
      }
    } catch (e) {
      if (window.console) { window.console.error('cme-cta60 : erreur ignoree', e); }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', demarrer);
  } else {
    demarrer();
  }
})();

JS;
    echo "\n</script>\n";
});
