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
 *  - Champs repris de la base de donnees existante (table leads_convertis /
 *    API Cloud Run deja en place) : prenom, telephone, email, code_postal.
 *    HYPOTHESE A CONFIRMER : ce n'est pas forcement exactement la liste de
 *    champs du vrai formulaire WPForms #472 sur /contactez-un-expert/, que
 *    ce sandbox ne peut pas inspecter (pas d'acces au site live). A ajuster
 *    si l'operateur confirme une liste differente.
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

  var ETAPES = [
    { champ: 'prenom', label: 'Quel est votre prénom ?', type: 'text', placeholder: 'Votre prénom' },
    { champ: 'telephone', label: 'Votre numéro de téléphone ?', type: 'tel', placeholder: '06 12 34 56 78' },
    { champ: 'email', label: 'Votre adresse email ?', type: 'email', placeholder: 'vous@exemple.fr' },
    { champ: 'code_postal', label: 'Votre code postal ?', type: 'text', placeholder: '75001' }
  ];

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

  // ── ENVOI DU LEAD (reutilise le relais deja deploye et deja valide en prod) ──
  function envoyerLead(valeurs, position, silo) {
    try {
      var payload = {
        tool: 'contact-expert-inline',
        prenom: valeurs.prenom || '',
        telephone: valeurs.telephone || '',
        email: valeurs.email || '',
        code_postal: valeurs.code_postal || '',
        details: JSON.stringify({ position: position, silo: silo }),
        source_post_id: String(window.CME_POST_ID || '')
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
          return '<div class="cme-mf-etape" data-champ="' + e.champ + '" style="display:' + (i === 0 ? 'block' : 'none') + ';">' +
            '<label style="display:block;font-weight:700;font-size:15px;color:#111827;margin-bottom:10px;">' + e.label + '</label>' +
            '<input type="' + e.type + '" class="cme-mf-input" placeholder="' + e.placeholder + '" style="width:100%;box-sizing:border-box;padding:12px 14px;border:2px solid #e5e7eb;border-radius:10px;font-size:16px;outline:none;">' +
            '<div class="cme-mf-erreur" style="color:#dc2626;font-size:13px;margin-top:6px;display:none;"></div>' +
          '</div>';
        }).join('');

        d.innerHTML =
          '<div style="padding:18px 20px 10px;">' +
            '<div style="color:#fff;font-weight:700;font-size:16px;margin-bottom:10px;">' + offre.texte + '</div>' +
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
          if (champ === 'prenom') { return valeur.length >= 2 ? '' : 'Entrez votre prénom.'; }
          if (champ === 'telephone') { return valeur.replace(/\D/g, '').length >= 8 ? '' : 'Numéro invalide.'; }
          if (champ === 'email') { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valeur) ? '' : 'Email invalide.'; }
          if (champ === 'code_postal') { return /^\d{5}$/.test(valeur) ? '' : 'Code postal invalide.'; }
          return '';
        }
        function afficherErreur(msg) {
          var erreurEl = noeudsEtapes[idx].querySelector('.cme-mf-erreur');
          if (!erreurEl) { return; }
          if (msg) { erreurEl.textContent = msg; erreurEl.style.display = 'block'; }
          else { erreurEl.style.display = 'none'; }
        }
        function allerA(nouvelIdx) {
          noeudsEtapes[idx].style.display = 'none';
          idx = nouvelIdx;
          if (idx >= ETAPES.length) {
            noeudsEtapes[ETAPES.length].style.display = 'block';   // etape "merci"
            btnNav.style.display = 'none';
            barreProgres.style.width = '100%';
            return;
          }
          noeudsEtapes[idx].style.display = 'block';
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
