<?php
/**
 * Plugin Name: CME - Boutons CTA progressifs
 * Description: Insere un bouton CTA environ toutes les 230 mots (~1 minute de lecture) dans le corps de chaque article, avec la destination du silo (gaz et electricite : comparateur, aides et renovation : simulateur d'aides, solaire : devis solaire). Mode apercu par defaut : visible uniquement avec ?cta60=1 dans l'URL. Pour desactiver : supprimer ce fichier.
 */
if (!defined('ABSPATH')) {
    exit;
}

add_action('wp_footer', function () {
    if (!is_singular('post')) {
        return;
    }
    echo "<script id=\"cme-cta-progressifs\">\n";
    echo <<<'JS'
(function () {
  'use strict';

  // ── REGLAGES ────────────────────────────────────────────────────────────
  var MODE = 'actif';         // 'apercu' : visible seulement avec ?cta60=1 | 'actif' : tous les visiteurs | 'off'
  var MOTS_PAR_BOUTON = 230;  // environ une minute de lecture
  var MAX_BOUTONS = 30;       // garde-fou technique, au-dessus du maximum attendu (~23)
  var MOTS_FIN_MIN = 120;     // pas de bouton s'il reste moins de mots que cela
  var BASE = 'https://www.comprendre-mon-energie.fr';

  var GAZ = { url: BASE + '/comparateur-energie-electricite-gaz/', texte: 'Comparez les offres Gaz au meilleur prix', bouton: 'Comparer les offres gaz', c1: '#1e3a8a', c2: '#3b82f6' };
  var ELEC = { url: BASE + '/comparateur-energie-electricite-gaz/', texte: 'Comparez les offres Électricité au meilleur prix', bouton: 'Comparer les offres électricité', c1: '#1e3a8a', c2: '#3b82f6' };
  var AIDES = { url: BASE + '/simulateur-aides-renovation-energetique/', texte: 'Calculez vos aides à la rénovation', bouton: 'Simuler mes aides', c1: '#78350f', c2: '#f59e0b' };
  var SOLAIRE = { url: BASE + '/devis-panneau-solaire/', texte: 'Estimez votre installation solaire', bouton: 'Simuler mon projet solaire', c1: '#052e16', c2: '#16a34a' };
  var PAR_PREFIXE = { 'gaz': GAZ, 'electricite': ELEC, 'aide-energetique': AIDES, 'renovation-energetique': AIDES, 'solaire': SOLAIRE };

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
      var offre = PAR_PREFIXE[prefixe];
      if (!offre) { arret("prefixe d'URL inconnu : " + prefixe); return; }   // pas de bouton plutot qu'une mauvaise destination
      zone.setAttribute('data-cta60', '1');

      var m = (article.className || '').match(/(?:^|\s)post-(\d+)(?:\s|$)/);
      var idArticle = m ? m[1] : '';

      function creer(n) {
        var d = document.createElement('div');
        d.className = 'cme-cta60';
        d.setAttribute('data-pos', String(n));
        d.style.cssText = 'background:linear-gradient(135deg,' + offre.c1 + ',' + offre.c2 + ');border-radius:12px;padding:14px 18px;margin:26px 0;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;box-sizing:border-box;max-width:100%;clear:both;';
        var t = document.createElement('span');
        t.style.cssText = 'color:#fff;font-weight:700;font-size:17px;line-height:1.3;flex:1 1 220px;';
        t.textContent = offre.texte;
        var a = document.createElement('a');
        a.href = offre.url + '?' + (idArticle ? 'src_post=' + idArticle + '&' : '') + 'pos=' + n;
        a.textContent = offre.bouton + ' →';
        a.style.cssText = 'background:#fff;color:' + offre.c1 + ';font-weight:700;font-size:15px;padding:11px 22px;border-radius:9px;text-decoration:none;white-space:nowrap;display:inline-block;';
        d.appendChild(t);
        d.appendChild(a);
        return d;
      }

      var enfants = Array.prototype.slice.call(zone.children);
      var i;
      // apres[i] : mots restant apres l'element i avant le prochain bouton existant (ou la fin)
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
        if (estCta(el)) { cumul = 0; continue; }   // un bouton existant remet le compteur a zero
        cumul += mots(el);
        if (cumul < MOTS_PAR_BOUTON) { continue; }
        if (poses >= MAX_BOUTONS) { break; }
        if (!/^(P|UL|OL|TABLE|FIGURE|BLOCKQUOTE)$/.test(el.tagName)) { continue; }   // jamais apres un titre, ni au milieu d'un bloc
        var suivant = enfants[i + 1];
        if (!suivant || estCta(suivant) || estVide(suivant)) { continue; }
        if (apres[i] < MOTS_FIN_MIN) { continue; }   // trop pres d'un bouton existant ou de la fin
        zone.insertBefore(creer(poses + 1), suivant);
        poses++;
        cumul = 0;
      }

      if (MODE === 'apercu' && window.console) {
        window.console.log('cme-cta60 : ' + poses + ' bouton(s), destination ' + offre.url);
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
