<?php
/**
 * Plugin Name: CME - Reduction visuelle du bouton telephone du header
 * Description: Reduit la taille du bouton/numero de telephone affiche en
 * header (visible au scroll), demande explicite de l'operateur le 25/10/2026.
 *
 * CONTEXTE (25/10/2026) : le bouton n'est PAS gere par un fichier de ce repo --
 * c'est un widget natif WordPress (zone "header-widget", id="block-58"),
 * meme famille que le widget du footer deja documente dans CLAUDE.md comme
 * invisible/non modifiable depuis ce repo. Verifie en lecture seule via le
 * pont GitHub Actions (scripts-maintenance/inspecter_bouton_telephone_header.py
 * + inspecter_css_btn_cta.py) :
 *   <a href="tel:+33189713648" class="btn-cta" style="font-size: 20px;">
 *     📞 01 89 71 36 48
 *   </a>
 * La classe .btn-cta est une classe de theme GENERIQUE/partagee (deja
 * documentee comme piege dans CLAUDE.md, section "Verifier un changement
 * live" -- plusieurs occurrences possibles sur une meme page) :
 *   .btn-cta { padding:15px 10px; font-size:16px; ... }
 * D'OU LE SCOPING STRICT ci-dessous sur ".header-widget .btn-cta"
 * uniquement -- ne doit jamais toucher un autre bouton .btn-cta ailleurs
 * sur le site (anciens simulateurs, autres widgets, etc.).
 *
 * Valeurs choisies (a ajuster si le resultat visuel ne convient pas,
 * simple changement de ces deux nombres puis redeploiement cPanel) :
 *   - font-size : 20px -> 14px (inline sur l'element, d'ou le !important
 *     necessaire pour le surpasser depuis une feuille de style externe)
 *   - padding   : 15px 10px -> 8px 10px (garde la largeur, reduit la
 *     hauteur, qui contribue le plus a la sensation de "gros bouton")
 *
 * Deploiement : meme contrainte que les autres mu-plugins de ce projet --
 * non versionne automatiquement sur le serveur. cloudshell download,
 * upload cPanel dans /wp-content/mu-plugins/, purge des 2 caches
 * LiteSpeed (cPanel + wp-admin), verifier avec ?t=$RANDOM.
 */
if (!defined('ABSPATH')) {
    exit;
}

add_action('wp_head', function () {
    echo "<style id=\"cme-header-tel-style\">\n"
       . ".header-widget .btn-cta{font-size:14px!important;padding:8px 10px!important;}\n"
       . "</style>\n";
});
