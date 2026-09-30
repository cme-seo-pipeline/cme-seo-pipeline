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
  // Premier partenaire d'affiliation (Awin, programme Zendure EU) -- lien de suivi fourni par
  // Awin, copie EXACTEMENT tel quel : lienExact=true empeche creer() d'y ajouter src_post/pos,
  // par prudence sur la commission d'un tout premier partenariat. Code promo (-5%, AF5E24) et
  // date de retrait alignees sur la date la plus proche vue dans les deux emails Awin (rappel :
  // "closes October 8th" ; detail du code : "Ends 01/11/2026") -- on retire par securite a la
  // premiere des deux plutot que de risquer d'afficher un code expire.
  var ZENDURE_FIN = new Date('2026-11-01T23:59:59');   // date confirmee par le porteur de projet (detail du code Awin : "Ends 01/11/2026")
  // ZENDURE n'est plus insere dans le texte (retire le jour meme, remplace par le bouton flottant
  // ci-dessous) -- l'objet reste defini car SILOS_ZENDURE_FLOTTANT le reutilise plus bas.
  var ZENDURE = {
    url: 'https://www.awin1.com/cread.php?awinmid=68786&awinaffid=3103124&campaign=&ued=https%3A%2F%2Fzendure.fr%2F',
    texte: 'Zendure SolarFlow : stockez votre énergie solaire (code AF5E24 = -5%)',
    accroche: 'Vous suivez Comprendre Mon Énergie ? Profitez de notre partenariat avec Zendure, spécialiste du stockage d\u2019énergie solaire, et du code AF5E24 (-5%) \u2b07',
    bouton: 'Découvrir Zendure',
    c1: '#052e16', c2: '#16a34a',
    lienExact: true,
    // Bannieres officielles Awin (campagne FR 9.16-10.8, "Copy Code" du 30/09/2026).
    // Chaque image garde SON PROPRE lien de suivi (s= different) -- jamais permuter
    // une image avec le lien de l'autre.
    banniereDesktop: { url: 'https://www.awin1.com/cread.php?s=4898018&v=68786&q=568335&r=3103124', img: 'https://www.awin1.com/cshow.php?s=4898018&v=68786&q=568335&r=3103124', largeur: 728, hauteur: 90 },
    banniereMobile: { url: 'https://www.awin1.com/cread.php?s=4898015&v=68786&q=568335&r=3103124', img: 'https://www.awin1.com/cshow.php?s=4898015&v=68786&q=568335&r=3103124', largeur: 320, hauteur: 50 }
  };
  var PAR_PREFIXE = { 'gaz': [GAZ], 'electricite': [ELEC], 'aide-energetique': [AIDES], 'renovation-energetique': [AIDES], 'solaire': [SOLAIRE] };

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
      var offres = PAR_PREFIXE[prefixe];
      if (!offres || !offres.length) { arret("prefixe d'URL inconnu : " + prefixe); return; }   // pas de bouton plutot qu'une mauvaise destination
      zone.setAttribute('data-cta60', '1');

      var m = (article.className || '').match(/(?:^|\s)post-(\d+)(?:\s|$)/);
      var idArticle = m ? m[1] : '';

      function creer(n) {
        var offre = offres[(n - 1) % offres.length];
        var d = document.createElement('div');
        d.className = 'cme-cta60';
        d.setAttribute('data-pos', String(n));
        d.style.cssText = 'background:linear-gradient(135deg,' + offre.c1 + ',' + offre.c2 + ');border-radius:12px;padding:14px 18px;margin:26px 0;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;box-sizing:border-box;max-width:100%;clear:both;';
        var t = document.createElement('span');
        t.style.cssText = 'color:#fff;font-weight:700;font-size:17px;line-height:1.3;flex:1 1 220px;';
        t.textContent = offre.texte;
        var a = document.createElement('a');
        if (offre.lienExact) {
          a.href = offre.url;   // lien d'affiliation externe : jamais modifie, priorite a la commission
        } else {
          var sep = offre.url.indexOf('?') === -1 ? '?' : '&';
          a.href = offre.url + sep + (idArticle ? 'src_post=' + idArticle + '&' : '') + 'pos=' + n;
        }
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

  // ── BOUTON FLOTTANT ZENDURE (silos Solaire, Aide Energetique, Renovation) ──
  // Distinct du systeme de bandeaux dans le texte ci-dessus : position fixe (bas d'ecran),
  // apparait une seule fois 60 secondes apres l'arrivee sur la page (pas de reapparition en
  // boucle, pour ne jamais ressembler a un interstitiel intrusif), fermeture manuelle possible.
  // S'arrete tout seul apres ZENDURE_FIN, comme le reste de l'offre Zendure.
  var SILOS_ZENDURE_FLOTTANT = ['gaz', 'electricite', 'aide-energetique', 'renovation-energetique', 'solaire'];
  var DELAI_ZENDURE_FLOTTANT_MS = 30000;

  function demarrerZendureFlottant() {
    try {
      if (MODE === 'off') { return; }
      if (MODE === 'apercu' && !/[?&]cta60=1(&|$)/.test(window.location.search)) { return; }
      if (new Date() > ZENDURE_FIN) { return; }
      if (!document.body || !document.body.classList.contains('single-post')) { return; }
      var prefixe = window.location.pathname.split('/').filter(Boolean)[0];
      if (SILOS_ZENDURE_FLOTTANT.indexOf(prefixe) === -1) { return; }
      if (document.getElementById('cme-zendure-flottant')) { return; }

      function afficher() {
        if (new Date() > ZENDURE_FIN) { return; }   // re-verifie a chaque reapparition, pas seulement au chargement
        if (document.getElementById('cme-zendure-flottant')) { return; }
        var d = document.createElement('div');
        d.id = 'cme-zendure-flottant';
        d.style.cssText = 'position:fixed;left:0;right:0;bottom:0;width:100%;z-index:99999;background:linear-gradient(135deg,' + ZENDURE.c1 + ',' + ZENDURE.c2 + ');box-shadow:0 -4px 18px rgba(0,0,0,.2);box-sizing:border-box;';

        if (ZENDURE.banniereDesktop && ZENDURE.banniereMobile) {
          var b = (window.innerWidth || document.documentElement.clientWidth) < 600
                  ? ZENDURE.banniereMobile : ZENDURE.banniereDesktop;
          var conteneurImg = document.createElement('div');
          conteneurImg.style.cssText = 'text-align:center;padding:10px 44px 10px 10px;';
          var accroche = document.createElement('div');
          accroche.style.cssText = 'color:#fff;font-weight:700;font-size:15px;line-height:1.4;margin-bottom:8px;';
          accroche.textContent = ZENDURE.accroche;
          var img = document.createElement('img');
          img.src = b.img;
          img.width = b.largeur;
          img.height = b.hauteur;
          img.alt = ZENDURE.texte;
          img.style.cssText = 'display:inline-block;max-width:100%;height:auto;border:0;vertical-align:middle;';
          var lienImg = document.createElement('a');
          lienImg.href = b.url;   // lien d'affiliation propre a CETTE banniere : jamais modifie, jamais permute
          lienImg.rel = 'sponsored';
          lienImg.appendChild(img);
          conteneurImg.appendChild(accroche);
          conteneurImg.appendChild(lienImg);
          d.appendChild(conteneurImg);

        } else {
          var interieur = document.createElement('div');
          interieur.style.cssText = 'max-width:900px;margin:0 auto;padding:16px 48px 16px 18px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;position:relative;';
          var texte = document.createElement('div');
          texte.style.cssText = 'color:#fff;font-weight:700;font-size:15px;line-height:1.35;flex:1 1 240px;';
          texte.textContent = ZENDURE.texte;
          var a = document.createElement('a');
          a.href = ZENDURE.url;   // lien d'affiliation externe : jamais modifie, priorite a la commission
          a.textContent = ZENDURE.bouton + ' →';
          a.style.cssText = 'display:inline-block;background:#fff;color:' + ZENDURE.c1 + ';font-weight:700;font-size:14px;padding:9px 18px;border-radius:9px;text-decoration:none;white-space:nowrap;';
          interieur.appendChild(texte);
          interieur.appendChild(a);
          d.appendChild(interieur);
        }

        var fermer = document.createElement('button');
        fermer.setAttribute('aria-label', 'Fermer');
        fermer.textContent = '×';
        fermer.style.cssText = 'position:absolute;top:6px;right:10px;background:none;border:none;color:#fff;font-size:22px;line-height:1;cursor:pointer;padding:4px 6px;z-index:1;';
        fermer.onclick = function () {
          d.remove();
          window.setTimeout(afficher, DELAI_ZENDURE_FLOTTANT_MS);   // reapparait apres une fermeture, sur demande explicite
        };
        d.style.position = 'fixed';   // garanti meme si ZENDURE.image a modifie le flux ci-dessus
        d.appendChild(fermer);
        document.body.appendChild(d);
      }

      window.setTimeout(afficher, DELAI_ZENDURE_FLOTTANT_MS);
    } catch (e) {
      if (window.console) { window.console.error('cme-zendure-flottant : erreur ignoree', e); }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', demarrer);
    document.addEventListener('DOMContentLoaded', demarrerZendureFlottant);
  } else {
    demarrer();
    demarrerZendureFlottant();
  }
})();

JS;
    echo "\n</script>\n";
});
