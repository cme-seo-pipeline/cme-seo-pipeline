<?php
/**
 * Plugin Name: CME - Formulaire de contact progressif
 * Description: Insere un mini-formulaire de contact interactif -- variante
 * 'contact' : 3 ECRANS de 2 champs chacun depuis le 24/11/2026 (schema
 * "2 -> 2 -> 2", voir chantier tout en bas) ; variante 'appel' : UN SEUL
 * ECRAN inchange (nom/prenom + telephone affiches ensemble, depuis le
 * 04/11/2026) -- case RGPD sur la derniere etape de saisie dans les deux
 * cas -- a une cadence croissante (300, 500, 700, 900, 1100 mots, puis tous
 * les 400 mots, plafonnee a 7 occurrences) dans le corps de chaque article,
 * avec les couleurs unifiees du site. Remplace les anciens boutons CTA qui
 * renvoyaient vers /contactez-un-expert/ : desormais le visiteur remplit
 * directement un mini-formulaire dans l'article, sans changer de page. Mode
 * apercu par defaut : visible uniquement avec ?cta60=1 dans l'URL. Pour
 * desactiver : supprimer ce fichier.
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
 *
 * AJOUT DU 01/11/2026 (demande operateur) : `temps_ms` (millisecondes
 * depuis le chargement de la page) sur chaque evenement form_vu/form_etape/
 * form_abandon -- pour savoir, pas seulement QUELLE position (n-ieme
 * formulaire) mais a quel INSTANT de la lecture le formulaire est vu/
 * engage/abandonne/soumis. Necessite la colonne `temps_ms` sur
 * interactions_contenu (scripts-maintenance/ajouter_colonne_temps_ms_interactions.py,
 * meme prealable que pour cme-tracking-conversion.php, voir CLAUDE.md).
 *
 * AJOUT DU 01/11/2026, suite (demande operateur) : nouveau mini-formulaire
 * "avant d'appeler", meme principe que le formulaire de contact ci-dessus
 * (nom/prenom + telephone, meme case RGPD obligatoire, meme validation),
 * mais dont la DERNIERE etape n'affiche pas un message "merci" -- elle
 * affiche un vrai bouton "Appeler maintenant" (lien tel:) : le lead est
 * capture AVANT que l'appel ne soit lance, et le visiteur garde la main sur
 * le moment ou l'appel part reellement (decision operateur, voir CLAUDE.md).
 * Objectif explicite : "l'ajustement au niveau du deploiement se fait une
 * seule fois" -- d'ou un parametre `variante` ajoute a creer() plutot qu'un
 * second generateur de formulaire duplique ; tout le reste (styles, RGPD,
 * validation, navigation, tracking de progression) est partage a 100% entre
 * les deux variantes.
 * Perimetre : articles uniquement (is_singular('post'), comme le formulaire
 * de contact), PAS le numero affiche en header/footer -- celui-ci reste un
 * lien tel: direct, inchange, a la demande explicite de l'operateur.
 * Frequence : UNE SEULE occurrence par article (pas periodique comme le
 * formulaire de contact), ajoutee en toute fin de contenu -- c'est la que
 * l'intention d'appel est la plus forte (lecteur qui a lu tout l'article),
 * et ca n'entre pas en concurrence avec les formulaires de contact
 * periodiques deja en place et deja mesures.
 * Pas de contournement (lien d'appel direct) sur ce bloc : formulaire
 * obligatoire pour commencer, a la demande explicite de l'operateur --
 * revisable plus tard sur la base de donnees reelles si la friction s'avere
 * trop forte.
 * Lead : meme relais que le formulaire de contact (/wp-json/cme/v1/log-lead),
 * mais `tool = 'appel-expert-inline'` (distinct de 'contact-expert-inline'
 * et de 'appel-telephone', voir cme-tracking-conversion.php) pour isoler ce
 * nouveau type de conversion dans les analyses -- et relaye vers le MEME
 * onglet Google Sheets que le formulaire de contact (meme fonction PHP cote
 * serveur, scope elargi, voir cme-tracking-conversion.php), avec source_page
 * et le tracking habituel (source_post_id, position, silo).
 *
 * CHANTIER DU 04/11/2026 (formulaire a un seul ecran + nouvelle cadence,
 * UNIFIE sur tous les silos/tous les articles -- demande explicite de
 * l'operateur, decidee sur la base des donnees de retention/clics/
 * abandon accumulees du 28/10 au 04/11, voir claude/objectif-100-leads-mois.md
 * et CLAUDE.md) :
 *  - Formulaire a UN SEUL ECRAN : nom/prenom ET telephone affiches en meme
 *    temps (plus de type Typeform "une question a la fois"), case RGPD
 *    sous les champs, UN SEUL bouton ("Envoyer" pour la variante contact,
 *    "Appeler maintenant" pour la variante appel -- meme comportement que
 *    le popup header deja en prod : le lead est envoye PUIS l'appel declenche
 *    par window.location.href = 'tel:...', en un seul clic). Motivation
 *    chiffree : 4 abandons sur 6 sessions ayant atteint l'ancienne derniere
 *    etape (telephone), soit ~67% -- la friction se jouait juste avant la
 *    soumission, pas a l'entree du formulaire.
 *  - Nouvelle cadence de placement (variante contact uniquement, le bloc
 *    "avant d'appeler" reste une occurrence unique en fin d'article,
 *    inchange) : 1er formulaire a 300 mots (encore 88% de retention a ce
 *    stade, pas de concurrence avec les images les plus cliquees, groupees
 *    a 100-170 mots) ; tous les 200 mots jusqu'a 1200 mots (zone ou se
 *    concentrait 100% de la conversion mesuree sous l'ancienne cadence a
 *    ~230 mots) ; tous les 400 mots au-dela (public residuel en forte
 *    baisse de retention, rendement marginal plus faible). Plafonne a 7
 *    occurrences meme sur les articles tres longs, pour ne jamais
 *    "wallpaperer" un article. Voir prochainSeuilContact() plus bas.
 *  - Tracking simplifie en consequence (plus d'etape intermediaire
 *    "telephone atteinte" puisqu'il n'y a plus qu'un seul ecran) :
 *    form_vu (visible) et form_etape=termine (soumis) suffisent ;
 *    form_abandon est redefini -- "vu mais jamais soumis" au lieu de
 *    "etape telephone atteinte sans soumettre" (etape='vu' au lieu d'un
 *    numero d'etape). Rupture de continuite ASSUMEE avec les indicateurs
 *    mesures du 28/10 au 04/11 (positions 1/2/3/5, taux d'abandon ~67%,
 *    cadence a 230 mots) : nouveau point de mesure prevu a 30 jours
 *    plutot qu'a 7-10 jours, decision explicite de l'operateur.
 *
 * CORRECTIF DU 04/11/2026, suite -- angle mort "bloc Colonnes" :
 * la boucle de placement du formulaire "contact" ne regardait que les
 * ENFANTS DIRECTS de .entry-content (zone.children), jamais une recherche
 * recursive. Un article dont le corps est redige avec un bloc Gutenberg
 * "Colonnes" (<div class="wp-block-columns"><div class="wp-block-column">
 * ...<p>...</p>...</div></div>) a donc tous ses <p>/<ul>/<ol>/<table>/
 * <figure>/<blockquote> reels NON eligibles (ce sont des enfants du <div>
 * wp-block-column, jamais des enfants directs de .entry-content), quelle
 * que soit la longueur totale de l'article -- confirme sur
 * attestation-de-contrat-delectricite (4461 mots, 0 formulaire "contact"
 * jamais pose) et 16 autres articles (audit exhaustif,
 * scripts-maintenance/auditer_angle_mort_colonnes_cta.py). Le bloc "avant
 * d'appeler" n'etait pas concerne (zone.appendChild(...) inconditionnel,
 * sans condition de tag), ce qui expliquait l'ecart observe (le bloc
 * "appel" apparait normalement, jamais le "contact", sur les memes
 * articles).
 * Corrige en "deplipant" (enfantsEffectifs()) tout <div class="wp-block-
 * columns"> / <div class="wp-block-column"> avant de construire la liste
 * de candidats -- la boucle de placement travaille desormais sur les
 * elements reels (<p>, <table>...) qu'ils contiennent, pas sur le
 * conteneur opaque. L'insertion elle-meme se fait sur le PARENT REEL de
 * l'element de reference (suivantEl.parentNode), plus sur `zone`
 * directement, puisque cet element peut desormais etre imbrique a
 * l'interieur d'un wp-block-column -- Node.insertBefore exige que le
 * noeud de reference soit un enfant DIRECT du noeud sur lequel on
 * l'appelle. Totalement retro-compatible : un article sans bloc Colonnes
 * n'a aucun <div> qui matche, enfantsEffectifs() renvoie alors exactement
 * la meme liste que zone.children, et suivantEl.parentNode === zone dans
 * ce cas (meme comportement qu'avant ce correctif).
 * Perimetre volontairement restreint a wp-block-columns/wp-block-column
 * (seule cause confirmee par l'audit a cette date) -- pas de
 * generalisation a tout <div> (ex. wp-block-group, ou un div d'embed/
 * widget) sans preuve similaire, pour ne pas inserer un formulaire a
 * l'interieur d'un bloc qui n'aurait pas la meme nature purement
 * structurelle.
 *
 * CORRECTIF DU 11/11/2026, suite -- angle mort "<article> brute" :
 * classer_cause_racine_17_angle_mort.py (04/11) avait identifie une DEUXIEME
 * cause distincte, laissee de cote ce soir-la : 6 articles (id=3489, 3488,
 * 3491, 3384, 3385, 3387) ont tout leur contenu reel enveloppe dans un
 * UNIQUE <article class=""> imbrique -- probablement un artefact d'import/
 * copie-collage, puisqu'une balise <article> a l'interieur du
 * post_content stocke n'a rien de semantique ici (le theme pose deja sa
 * propre balise <article class="type-post"> EN DEHORS de .entry-content,
 * voir document.querySelector('article.type-post') plus bas -- celle-ci
 * n'est jamais affectee par ce correctif). Resultat avant correctif :
 * .entry-content n'a QU'UN SEUL enfant direct (cet <article>), de tagName
 * 'ARTICLE' -- jamais P/UL/OL/TABLE/FIGURE/BLOCKQUOTE -- donc la boucle de
 * placement s'arretait immediatement sans jamais poser le moindre
 * formulaire "contact", quelle que soit la longueur reelle de l'article
 * (confirme : 0 formulaire sur les 6, de 1994 a 2849 mots).
 * Meme correctif, meme mecanisme que ci-dessus (enfantsEffectifs() deplie
 * desormais aussi tout <article>, pas seulement wp-block-columns/
 * wp-block-column) -- reutilise exactement la meme recursion et la meme
 * insertion sur le parent reel (suivantEl.parentNode.insertBefore),
 * aucune nouvelle mecanique necessaire. Totalement retro-compatible pour
 * les memes raisons que le correctif du 04/11 : un article sans <article>
 * imbrique n'est pas affecte. Perimetre etendu a <article> (sans
 * condition de classe, par opposition a wp-block-columns qui exige la
 * classe) car cette fois la preuve est specifique au TAG, observee sur
 * les 6 articles cites, et le seul <article> jamais rencontre par ce
 * script est soit le wrapper du theme (hors de .entry-content, jamais un
 * candidat), soit cet artefact d'import -- aucun troisieme cas connu.
 *
 * COMPARATEUR ENERGIE AU 1ER EMPLACEMENT (16/11/2026) -- demande operateur
 * explicite : remplacer UNIQUEMENT la 1ere occurrence du mini-formulaire
 * "contact-expert-inline" par le widget comparateur-energie (plugin
 * wordpress-plugins/comparateur-energie/), sur TOUS les silos, anciens et
 * nouveaux articles -- les occurrences suivantes (2e, 3e...) restent
 * creer(n,'contact') inchange ; le bloc "avant d'appeler" (variante 'appel')
 * et le popup du bouton telephone du header (cme-tracking-conversion.php)
 * ne sont pas concernes. Implementation cote client, meme principe de
 * couverture retroactive "gratuite" que le reste de ce fichier -- aucune
 * reecriture du contenu stocke de chaque article. Voir
 * comparateurDisponible()/creerComparateur()/initialiserComparateur() plus
 * bas, et le point d'entree expose window.cmeCmpInit par
 * comparateur-energie.js, qui doit lui-meme etre charge sur chaque article
 * (gate assoupli dans comparateur-energie.php : cme_cmp_enqueue_assets()
 * tourne desormais aussi sur is_singular('post'), pas seulement sur les
 * pages portant le shortcode reel). Filet de securite volontaire : si le
 * bootstrap (window.CME_CMP_BOOT/cmeCmpInit) est indisponible pour une
 * raison quelconque, ce 1er emplacement retombe simplement sur l'ancien
 * mini-formulaire -- jamais de placeholder "Chargement..." bloque a
 * l'ecran, jamais de capture de lead perdue a cette position.
 *
 * CORRECTIF (16/11/2026, meme jour) -- data-eg toujours 'dual' : une
 * premiere version de creerComparateur() faisait varier data-eg selon le
 * silo (gaz->'gaz', electricite->'elec'), a tort -- EDEF='gaz'/'elec' ne
 * presectionne pas un onglet, il VERROUILLE tout le parcours sur une seule
 * energie (aucun selecteur ni onglet de bascule, voir comparateur-energie.js).
 * Constate en prod par l'operateur juste apres deploiement : silo Gaz ->
 * comparatif gaz uniquement, silo Electricite -> comparatif elec
 * uniquement. Demande explicite : laisser le lecteur choisir lui-meme, un
 * seul comparateur bi-energie partout, aucune presupposition par silo --
 * data-eg = 'dual' sans exception desormais.
 *
 * CHANTIER DU 24/11/2026 (formulaire "contact-expert-inline" etendu a 6
 * champs, schema "2 -> 2 -> 2") -- demande operateur explicite, perimetre
 * STRICTEMENT limite a la variante 'contact' (le mini-formulaire periodique
 * dans le corps des articles) : la variante 'appel' ("avant d'appeler", fin
 * d'article) et le popup du bouton telephone du header
 * (cme-tracking-conversion.php) ne sont PAS concernes, inchanges a
 * l'identique.
 *  - Champs et ordre EXACTS demandes par l'operateur, groupes par paires de
 *    2 sur 3 ecrans : (1) nom et prenom + telephone, (2) appartement ou
 *    maison + proprietaire ou locataire, (3) code postal + adresse e-mail.
 *    Revient donc sur le principe "un seul ecran" du 04/11/2026, mais
 *    UNIQUEMENT pour cette variante -- pas un retour au Typeform
 *    "un-champ-a-la-fois" d'avant le 04/11 non plus : un compromis
 *    intermediaire (2 champs par ecran) propre a cette demande. La
 *    variante 'appel' reste a 1 seul ecran/2 champs, totalement inchangee
 *    (voir ETAPES_APPEL plus bas -- son code de rendu dans creer() est une
 *    branche separee de celle de 'contact', par securite : zero logique
 *    partagee qui pourrait regresser 'appel' en modifiant 'contact').
 *  - "Appartement ou maison" et "proprietaire ou locataire" sont des choix
 *    a 2 options (boutons a selectionner), pas des champs texte libres --
 *    meilleure qualification, zero ambiguite de saisie. Validation code
 *    postal (5 chiffres) et email (regex basique) ajoutee, memes principes
 *    que la validation deja en place sur prenom/telephone.
 *  - Indicateur de progression (3 points) ajoute en haut du formulaire --
 *    dans l'esprit de la barre de progression du tout premier formulaire
 *    (22/10/2026), disparue lors des simplifications successives.
 *  - Navigation : bouton "Suivant ->" sur les 2 premiers ecrans, "Envoyer
 *    ->" sur le dernier (ou la case RGPD, toujours sur la DERNIERE etape de
 *    saisie, inchangeant ce principe). Entree (clavier) = etape suivante,
 *    meme convention que l'ancien Typeform d'avant le 04/11/2026.
 *  - Tracking de progression etendu pour 'contact' uniquement : form_etape
 *    avec etape='1' (ecran 2 atteint) et etape='2' (ecran 3 atteint), en
 *    plus de form_vu/form_etape=termine deja en place -- redonne une vraie
 *    granularite d'abandon par ecran (DERNIER_ETAT.etape, utilise par le
 *    handler form_abandon), perdue lors du passage a l'ecran unique du
 *    04/11/2026. La variante 'appel' garde exactement son comportement
 *    actuel (etape toujours 'vu' jusqu'a 'termine', aucun ecran
 *    intermediaire -- rien ne change pour elle).
 *  - Donnees : 4 nouveaux champs dans le payload envoyerLead() pour la
 *    variante 'contact' uniquement (type_logement, statut_occupation,
 *    code_postal, email -- prenom/telephone inchanges) -- payload de la
 *    variante 'appel' strictement identique a avant (prenom/telephone
 *    seuls). Necessite 2 nouvelles colonnes BigQuery sur leads_convertis
 *    (type_logement, statut_occupation -- email/code_postal existaient
 *    deja) via scripts-maintenance/ajouter_colonnes_logement_leads.py, et
 *    un redeploiement de tracking-api/server.py (route /api/log-lead,
 *    action operateur, pas de CI/CD Cloud Run dans ce repo) AVANT le
 *    deploiement cPanel de ce fichier -- sinon ces 2 champs arriveraient
 *    au relais mais ne seraient pas repris dans la ligne BigQuery ecrite
 *    (le payload serait silencieusement tronque a ce que le code actuel du
 *    relais sait deja faire). 2 nouvelles colonnes Google Sheets ajoutees
 *    en derniere position de l'onglet "Leads Formulaire Article"
 *    (apps-scripts/cme-formulaire-article-leads.gs), meme convention que
 *    "CTA" -- necessite aussi un redeploiement operateur de ce script Apps
 *    Script (hors de portee de ce sandbox, script.google.com).
 *  - PREPARATION UNIQUEMENT a ce stade : build + validation locale (php -l,
 *    node --check sur le bloc JS extrait), PAS de deploiement cPanel --
 *    deploiement differe a la demande de l'operateur, suivant l'ordre
 *    ci-dessus (BigQuery -> Cloud Run -> Apps Script -> cPanel, dans cet
 *    ordre precis pour qu'aucun relais n'ecrive vers une colonne/un onglet
 *    qui n'existe pas encore).
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
  var MAX_FORMULAIRES_CONTACT = 7;   // plafond volontaire (04/11/2026) -- jamais "wallpaperer" un article tres long
  var MOTS_FIN_MIN = 120;     // pas de formulaire s'il reste moins de mots que cela
  var API_LEAD = '/wp-json/cme/v1/log-lead';   // relais deja deploye (cme-tracking-conversion.php)

  // Cadence de placement du formulaire CONTACT (04/11/2026, voir docblock) --
  // seuil en mots lus depuis le DEBUT de l'article (position ABSOLUE, pas une
  // distance depuis le formulaire precedent) pour le (poses+1)-ieme
  // formulaire deja pose : 300, 500, 700, 900, 1100 (pas de 200 mots), puis
  // 1500, 1900, 2300... (pas de 400 mots) au-dela.
  function prochainSeuilContact(poses) {
    if (poses < 5) { return 300 + poses * 200; }
    return 1100 + (poses - 4) * 400;
  }

  // CTA "avant d'appeler" (01/11/2026) -- une seule occurrence par article,
  // voir docblock plus haut. Meme numero que le bouton du header
  // (wordpress-mu-plugins/cme-header-tel-style.php), affiche a l'identique.
  var MOTS_MIN_CTA_APPEL = 300;   // pas de CTA appel sur un article trop court (stub)
  var TEL_NUMERO = '+33189713648';
  var TEL_AFFICHAGE = '01 89 71 36 48';
  var TEXTE_APPEL = '📞 Besoin d’une réponse immédiate ? Parlez à un conseiller énergie';

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

  // Personnalisation par SOUS-SILO (12/11/2026, demande operateur : messages
  // plus "frappants", avec une promesse de prise en charge specifique au
  // sujet reel de l'article, plutot que le message generique par silo
  // ci-dessus qui reste identique sur ~1000 articles). Niveau 1 d'un
  // chantier en deux temps (voir CLAUDE.md, section "Personnalisation des
  // messages CTA") : ceci est purement cote client, sans nouvelle donnee
  // backend -- le sous-silo est deja dans le 2e segment du chemin d'URL
  // (ex. /aide-energetique/aide-isolation/). Niveau 2 (promesse unique par
  // ARTICLE, pas par sous-silo) prevu comme chantier separe ulterieurement.
  //
  // Cles au format 'prefixe-silo/slug-sous-silo', VERIFIEES contre les
  // vrais slugs WordPress le 12/11/2026 (scripts-maintenance/lister_categories_wp.py,
  // pont GitHub Actions) -- pas devinees : certaines categories "Aide
  // Énergétique" ont ete creees manuellement en wp-admin (ex. "Aide pompe
  // à chaleur", "Aide isolation"), donc leur slug WordPress reel n'etait
  // pas garanti identique a une simple sanitisation du nom. Couvre TOUS
  // les sous-silos ayant deja des articles publies (pas seulement les
  // sous-silos du quota quotidien QUOTAS_SOUS_SILO, qui n'en est qu'un
  // sous-ensemble) -- un sous-silo absent de cette table retombe
  // simplement sur le message de silo generique ci-dessus (PAR_PREFIXE),
  // jamais d'erreur ni de formulaire manquant.
  var PAR_SOUS_SILO = {
    // Gaz
    'gaz/bouteilles': 'Trouvez le meilleur prix de bouteille de gaz près de chez vous',
    'gaz/chauffage-gaz': 'Optimisez votre chauffage au gaz : comparez et économisez',
    'gaz/comparatifs-fournisseurs-gaz': 'Comparez les fournisseurs de gaz et changez en 5 minutes',
    'gaz/contrat-gaz': 'Votre contrat de gaz est-il encore le plus avantageux ?',
    'gaz/demenagement-gaz': 'Déménagement : ouvrez votre nouveau contrat gaz sans coupure',
    'gaz/facture-gaz': 'Facture de gaz trop élevée ? Obtenez votre comparatif gratuit',
    // Électricité
    'electricite/chauffage-electricite': 'Réduisez votre facture de chauffage électrique : comparez',
    'electricite/comparatifs-fournisseurs-electricite': 'Comparez les fournisseurs d’électricité et économisez',
    'electricite/compteur': 'Un souci avec votre compteur électrique ? Un conseiller vous guide',
    'electricite/contrat-electricite': 'Votre contrat d’électricité est-il toujours le plus avantageux ?',
    'electricite/demenagement': 'Déménagement : activez votre électricité sans interruption',
    'electricite/facture-electricite': 'Facture d’électricité en hausse ? Comparez en 2 minutes',
    'electricite/heures-pleines-creuses': 'Heures pleines/creuses : optimisez votre contrat et économisez',
    // Aide Énergétique
    'aide-energetique/aide-isolation': 'Isolation : vérifiez votre éligibilité aux aides en 2 minutes',
    'aide-energetique/aide-pompe-a-chaleur': 'Pompe à chaleur éligible aux aides ? Vérifiez votre montant',
    'aide-energetique/aides-chaudiere': 'Changement de chaudière : calculez vos aides disponibles',
    'aide-energetique/aides-chauffe-eau-thermodynamique': 'Chauffe-eau thermodynamique : estimez votre aide',
    'aide-energetique/aides-combles-perdus': 'Isolation des combles perdus : calculez votre prime',
    'aide-energetique/aides-renovation-toiture': 'Rénovation de toiture : découvrez vos aides disponibles',
    'aide-energetique/cheque-energie': 'Chèque énergie : vérifiez votre éligibilité et vos droits',
    'aide-energetique/eco-pret-a-taux-zero': 'Éco-PTZ : simulez votre prêt à taux zéro en 2 minutes',
    'aide-energetique/maprimerenov': 'MaPrimeRénov’ : calculez le montant de votre aide',
    'aide-energetique/prime-energie': 'Prime Énergie : vérifiez le montant auquel vous avez droit',
    'aide-energetique/tva-reduite': 'TVA réduite travaux : vérifiez votre éligibilité',
    // Rénovation Énergétique (silo distinct, meme principe)
    'renovation-energetique/audit-energetique': 'Audit énergétique : obtenez un diagnostic gratuit',
    'renovation-energetique/bilan-energetique': 'Bilan énergétique gratuit : identifiez vos économies',
    'renovation-energetique/chaudiere': 'Remplacer votre chaudière ? Obtenez un devis et vos aides',
    'renovation-energetique/chauffe-eau-thermodynamique': 'Chauffe-eau thermodynamique : devis et aides en 2 minutes',
    'renovation-energetique/isolation': 'Isolation de votre logement : devis gratuit et aides',
    'renovation-energetique/poele': 'Installer un poêle ? Comparez les offres et vos aides',
    'renovation-energetique/pompe-a-chaleur': 'Pompe à chaleur : devis gratuit et simulation d’aides',
    'renovation-energetique/renovation-globale': 'Rénovation globale : simulez vos aides en 2 minutes',
    // Solaire
    'solaire/batterie-panneaux-solaires': 'Batterie solaire : calculez votre rentabilité en 2 minutes',
    'solaire/chauffe-eau-solaire': 'Chauffe-eau solaire : devis gratuit et simulation d’aides',
    'solaire/kit-solaire': 'Kit solaire : estimez votre installation et vos économies',
    'solaire/panneaux-solaires': 'Panneaux solaires : obtenez votre devis gratuit en 2 minutes',
    'solaire/systeme-solaire-combine': 'Système solaire combiné : simulez votre installation'
  };

  // Variante 'appel' ("avant d'appeler") -- INCHANGEE depuis le 04/11/2026 :
  // 2 champs affiches SIMULTANEMENT, un seul ecran. "prenom" porte le nom ET
  // le prenom en un seul champ (cle technique inchangee pour rester
  // compatible avec le schema BigQuery/Sheets existant). Non concernee par
  // le chantier du 24/11/2026 (voir docblock) -- utilisee par la branche
  // estAppel de creer() uniquement.
  var ETAPES_APPEL = [
    { champ: 'prenom', icone: '👋', label: 'Vos nom et prénom ?', type: 'text', placeholder: 'Nom et prénom' },
    { champ: 'telephone', icone: '📱', label: 'Votre numéro de téléphone ?', type: 'tel', placeholder: '06 12 34 56 78' }
  ];

  // Variante 'contact' (24/11/2026, demande operateur -- voir docblock) :
  // 6 champs, groupes par paires de 2 sur 3 ECRANS ("2 -> 2 -> 2"). Chaque
  // sous-tableau = un ecran, affiche un a la fois (navigation "Suivant ->").
  // Ordre et regroupement EXACTEMENT ceux demandes. type:'choix' = 2 boutons
  // a selectionner (pas de saisie libre) ; les autres types se comportent
  // comme avant (<input>). La case RGPD s'attache toujours au DERNIER ecran
  // (ici : code postal + email), meme principe que ETAPES_APPEL.
  var PAGES_CONTACT = [
    [
      { champ: 'prenom', icone: '👋', label: 'Vos nom et prénom ?', type: 'text', placeholder: 'Nom et prénom' },
      { champ: 'telephone', icone: '📱', label: 'Votre numéro de téléphone ?', type: 'tel', placeholder: '06 12 34 56 78' }
    ],
    [
      { champ: 'type_logement', icone: '🏠', label: 'Vous habitez en ?', type: 'choix', options: [
          { valeur: 'appartement', texte: 'Appartement' },
          { valeur: 'maison', texte: 'Maison' }
        ] },
      { champ: 'statut_occupation', icone: '🔑', label: 'Vous êtes ?', type: 'choix', options: [
          { valeur: 'proprietaire', texte: 'Propriétaire' },
          { valeur: 'locataire', texte: 'Locataire' }
        ] }
    ],
    [
      { champ: 'code_postal', icone: '📍', label: 'Votre code postal ?', type: 'text', inputmode: 'numeric', placeholder: '75001' },
      { champ: 'email', icone: '✉️', label: 'Votre adresse e-mail ?', type: 'email', placeholder: 'vous@exemple.fr' }
    ]
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
  // Correctif du 04/11/2026 (angle mort "bloc Colonnes", voir docblock) --
  // un conteneur purement structurel (Gutenberg "Colonnes") ne doit jamais
  // etre traite comme un bloc opaque : on "deplie" ses enfants a la place.
  // Etendu le 11/11/2026 (angle mort "<article> brute", voir docblock) --
  // meme logique pour une balise <article> imbriquee (artefact d'import,
  // jamais le wrapper du theme qui vit en dehors de .entry-content).
  function estConteneurLayout(el) {
    if (!el) { return false; }
    if (el.tagName === 'ARTICLE') { return true; }
    if (el.tagName !== 'DIV') { return false; }
    var classes = (el.className || '').split(/\s+/);
    return classes.indexOf('wp-block-columns') !== -1 || classes.indexOf('wp-block-column') !== -1;
  }
  // Construit la liste de candidats en depliant recursivement tout
  // conteneur de layout (cf. estConteneurLayout) -- tout le reste
  // (formulaires CTA, divs non-layout, balises atomiques) reste un
  // element unique, a sa place, exactement comme avant ce correctif.
  function enfantsEffectifs(zone) {
    var resultat = [];
    function deplier(liste) {
      for (var j = 0; j < liste.length; j++) {
        var el = liste[j];
        if (estConteneurLayout(el)) {
          deplier(Array.prototype.slice.call(el.children));
        } else {
          resultat.push(el);
        }
      }
    }
    deplier(Array.prototype.slice.call(zone.children));
    return resultat;
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
      '.cme-mf-rgpd-case{accent-color:' + FORMULAIRE_FOND2 + ';width:16px;height:16px;}' +
      // Boutons de choix (24/11/2026, variante 'contact' -- appartement/
      // maison, proprietaire/locataire) : etat hover, meme esprit que les
      // autres etats interactifs de ce fichier.
      '.cme-mf-choix-btn:hover{border-color:' + FORMULAIRE_ACCENT + '!important;}';
    document.head.appendChild(style);
  }

  // ── CARTOGRAPHIE : progression etape par etape + abandon (26/10/2026) ───
  // Buffer local independant de celui de cme-tracking-conversion.php (pas de
  // dependance d'ordre de chargement entre mu-plugins) -- meme principe,
  // meme relais.
  var API_INTERACTION = '/wp-json/cme/v1/log-interaction';
  var FILE_INTERACTIONS = [];
  var SESSION_ID = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  // Reference de temps pour `temps_ms` (01/11/2026, demande operateur) --
  // meme principe que dans cme-tracking-conversion.php, fichier distinct
  // donc variable distincte (pas de partage d'etat entre les deux scripts).
  var DEBUT = Date.now();
  // Dernier etat connu, mis a jour par CHAQUE instance de formulaire sur la
  // page -- sert uniquement a detecter un abandon au moment ou le visiteur
  // quitte/masque la page (on ne sait pas a l'avance lequel des formulaires
  // de la page il a utilise, donc on retient le plus recent). Depuis le
  // 04/11/2026 (formulaire a un seul ecran) : plus d'etape intermediaire a
  // retenir, juste "vu" (vrai) ou pas -- voir docblock, redefinition de
  // form_abandon.
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
      evt.temps_ms = Date.now() - DEBUT;
      FILE_INTERACTIONS.push(evt);
      if (FILE_INTERACTIONS.length >= 20) { viderInteractions(); }
    } catch (e) {}
  }
  // Enregistre une seule fois (pas par instance de formulaire). Redefini le
  // 04/11/2026 (formulaire a un seul ecran, voir docblock) : abandon = le
  // formulaire a ete VU (DERNIER_ETAT.vu, mis par l'IntersectionObserver
  // dans creer()) mais jamais soumis (DERNIER_ETAT remis a null au moment
  // de l'envoi reussi, voir envoyer() dans creer()) -- avant il fallait
  // avoir atteint l'etape "telephone" sans avoir complete ; il n'y a plus
  // qu'un seul ecran, donc plus qu'un seul etat possible a detecter.
  window.setInterval(viderInteractions, 15000);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState !== 'hidden') { return; }
    if (DERNIER_ETAT && DERNIER_ETAT.vu) {
      journaliserInteraction({
        type_evenement: 'form_abandon',
        position_contenu: DERNIER_ETAT.position,
        // Depuis le 24/11/2026 : reflete le dernier ecran reellement atteint
        // pour la variante 'contact' ('0'/'1'/'2', mis a jour a chaque
        // passage d'ecran dans creer()) -- avant, toujours 'vu' quel que
        // soit l'etat. La variante 'appel' n'a pas d'ecran intermediaire :
        // DERNIER_ETAT.etape y reste toujours 'vu', comportement identique
        // a avant ce chantier (repli explicite au cas ou etape serait
        // absent, memes raisons).
        etape: DERNIER_ETAT.etape || 'vu',
        silo: DERNIER_ETAT.silo,
        cible: DERNIER_ETAT.variante
      });
      viderInteractions();
      DERNIER_ETAT = null;   // evite un double comptage si la page redevient visible puis se cache encore
    } else {
      viderInteractions();
    }
  });
  window.addEventListener('pagehide', viderInteractions);

  // ── ENVOI DU LEAD (reutilise le relais deja deploye et deja valide en prod) ──
  // variante='appel' (01/11/2026) : meme relais, `tool` distinct pour isoler
  // les leads "avant d'appeler" du formulaire de contact classique dans les
  // analyses et dans leads_convertis -- voir docblock.
  function envoyerLead(valeurs, position, silo, variante) {
    try {
      var estAppel = variante === 'appel';
      var payload = {
        tool: estAppel ? 'appel-expert-inline' : 'contact-expert-inline',
        prenom: valeurs.prenom || '',
        telephone: valeurs.telephone || '',
        details: JSON.stringify({ position: position, silo: silo }),
        source_post_id: String(window.CME_POST_ID || ''),
        source_page: window.location.href
      };
      if (!estAppel) {
        // Nouveaux champs (24/11/2026, voir PAGES_CONTACT/docblock) --
        // variante 'contact' uniquement. La variante 'appel' garde un
        // payload strictement identique a avant ce chantier.
        payload.type_logement = valeurs.type_logement || '';
        payload.statut_occupation = valeurs.statut_occupation || '';
        payload.code_postal = valeurs.code_postal || '';
        payload.email = valeurs.email || '';
      }
      var body = JSON.stringify(payload);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(API_LEAD, new Blob([body], { type: 'application/json' }));
      } else if (window.fetch) {
        fetch(API_LEAD, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body, keepalive: true }).catch(function () {});
      }
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push({ event: estAppel ? 'generate_lead_appel_inline' : 'generate_lead_inline', position: position, silo: silo });
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

      var segments = window.location.pathname.split('/').filter(Boolean);
      var prefixe = segments[0];
      var offres = PAR_PREFIXE[prefixe];
      if (!offres || !offres.length) { arret("prefixe d'URL inconnu : " + prefixe); return; }   // pas de formulaire plutot qu'une mauvaise destination
      // Sous-silo (12/11/2026) : surclasse le texte de silo generique quand
      // le 2e segment de l'URL correspond a une entree connue de
      // PAR_SOUS_SILO ; sinon repli silencieux sur le message de silo
      // (comportement identique a avant cette date).
      var texteSousSilo = PAR_SOUS_SILO[prefixe + '/' + segments[1]];
      zone.setAttribute('data-cta60', '1');
      injecterStyles();

      // ── GENERATEUR DE MINI-FORMULAIRE (UN SEUL ECRAN depuis le 04/11/2026) ──
      // Une seule fonction, reutilisee a chaque position : c'est ce qui rend ce
      // mecanisme modulaire plutot que de dupliquer du HTML par position.
      function creer(n, variante) {
        variante = variante || 'contact';
        var estAppel = variante === 'appel';
        var offre = offres[(n - 1) % offres.length];
        var texteIntro = estAppel ? TEXTE_APPEL : (texteSousSilo || offre.texte);
        var texteReassurance = estAppel
          ? '🔒 Vos données restent confidentielles · un conseiller vous répond immédiatement au téléphone'
          : '🔒 Vos données restent confidentielles · un conseiller vous recontacte sous 24h';
        var d = document.createElement('div');
        d.className = 'cme-cta60';
        d.setAttribute('data-pos', String(n));
        d.style.cssText = 'background:linear-gradient(135deg,' + FORMULAIRE_FOND1 + ',' + FORMULAIRE_FOND2 + ');border-radius:16px;margin:26px 0;overflow:hidden;clear:both;max-width:100%;box-sizing:border-box;';

        var rgpdHtml =
          '<label class="cme-mf-rgpd" style="display:flex;align-items:flex-start;gap:8px;margin:2px 0 14px;font-size:12px;color:#6b7280;line-height:1.5;cursor:pointer;">' +
            '<input type="checkbox" class="cme-mf-rgpd-case" style="margin-top:2px;flex-shrink:0;">' +
            '<span>J’accepte d’être recontacté(e) par un conseiller et le traitement de mes données, conformément à notre <a href="' + URL_CADRE_LEGAL + '" target="_blank" rel="noopener" style="color:' + FORMULAIRE_FOND2 + ';text-decoration:underline;">politique de confidentialité</a>.</span>' +
          '</label>';

        function champHtml(e) {
          if (e.type === 'choix') {
            var boutonsHtml = e.options.map(function (opt) {
              return '<button type="button" class="cme-mf-choix-btn" data-champ="' + e.champ + '" data-valeur="' + opt.valeur + '" style="flex:1;padding:12px 10px;border:2px solid #e5e7eb;border-radius:10px;background:#fff;font-size:14px;font-weight:600;color:#374151;cursor:pointer;transition:border-color .15s,background .15s,color .15s;">' + opt.texte + '</button>';
            }).join('');
            return '<div class="cme-mf-champ" style="margin-bottom:12px;">' +
              '<label style="display:block;font-weight:700;font-size:14px;color:#111827;margin-bottom:6px;"><span style="font-size:18px;margin-right:6px;">' + e.icone + '</span>' + e.label + '</label>' +
              '<div class="cme-mf-choix-groupe" style="display:flex;gap:10px;">' + boutonsHtml + '</div>' +
            '</div>';
          }
          return '<div class="cme-mf-champ" style="margin-bottom:12px;">' +
            '<label style="display:block;font-weight:700;font-size:14px;color:#111827;margin-bottom:6px;"><span style="font-size:18px;margin-right:6px;">' + e.icone + '</span>' + e.label + '</label>' +
            '<input type="' + e.type + '" class="cme-mf-input" data-champ="' + e.champ + '" placeholder="' + e.placeholder + '"' + (e.inputmode ? ' inputmode="' + e.inputmode + '"' : '') + ' style="width:100%;box-sizing:border-box;padding:12px 14px;border:2px solid #e5e7eb;border-radius:10px;font-size:16px;outline:none;transition:border-color .15s,box-shadow .15s;">' +
          '</div>';
        }

        var corpsWrap = document.createElement('div');
        corpsWrap.className = 'cme-mf-corps';
        corpsWrap.style.cssText = 'background:#eff6ff;padding:20px;';

        if (estAppel) {
          // ── VARIANTE 'appel' : INCHANGEE depuis le 04/11/2026 (2 champs, 1 seul ecran) ──
          var champsHtmlAppel = ETAPES_APPEL.map(champHtml).join('');
          corpsWrap.innerHTML =
            '<div class="cme-mf-formulaire">' +
              champsHtmlAppel + rgpdHtml +
              '<div class="cme-mf-erreur" style="color:#dc2626;font-size:13px;margin-bottom:10px;display:none;"></div>' +
              '<button type="button" class="cme-mf-suiv" style="width:100%;background:' + FORMULAIRE_ACCENT + ';color:#1f2937;font-weight:700;font-size:16px;padding:13px 24px;border:none;border-radius:9px;cursor:pointer;">📞 Appeler maintenant</button>' +
            '</div>';

          function validerAppel(champ, valeur) {
            valeur = (valeur || '').trim();
            if (champ === 'prenom') { return valeur.length >= 2 ? '' : 'Entrez vos nom et prénom.'; }
            if (champ === 'telephone') { return valeur.replace(/\D/g, '').length >= 8 ? '' : 'Numéro invalide.'; }
            return '';
          }
          function afficherErreurAppel(msg) {
            var erreurEl = corpsWrap.querySelector('.cme-mf-erreur');
            if (!erreurEl) { return; }
            if (msg) { erreurEl.textContent = msg; erreurEl.style.display = 'block'; }
            else { erreurEl.style.display = 'none'; }
          }
          function envoyerAppel() {
            var inputs = Array.prototype.slice.call(corpsWrap.querySelectorAll('.cme-mf-input'));
            var valeurs = {};
            var premiereErreur = '';
            for (var k = 0; k < inputs.length; k++) {
              var champ = inputs[k].getAttribute('data-champ');
              var val = inputs[k].value;
              var erreur = validerAppel(champ, val);
              if (erreur && !premiereErreur) { premiereErreur = erreur; }
              valeurs[champ] = val.trim();
            }
            if (!premiereErreur) {
              var caseRgpd = corpsWrap.querySelector('.cme-mf-rgpd-case');
              if (caseRgpd && !caseRgpd.checked) { premiereErreur = 'Merci d’accepter la politique de confidentialité pour continuer.'; }
            }
            if (premiereErreur) { afficherErreurAppel(premiereErreur); return; }
            afficherErreurAppel('');
            envoyerLead(valeurs, n, prefixe, variante);
            journaliserInteraction({ type_evenement: 'form_etape', position_contenu: n, etape: 'termine', silo: prefixe, cible: variante });
            DERNIER_ETAT = null;
            // Meme comportement que le popup du bouton telephone du header
            // (cme-tracking-conversion.php, deja en prod) : lead envoye PUIS
            // appel declenche dans le meme clic, pas d'ecran intermediaire.
            window.location.href = 'tel:' + TEL_NUMERO;
          }
          corpsWrap.querySelector('.cme-mf-suiv').addEventListener('click', envoyerAppel);
          corpsWrap.addEventListener('keydown', function (evt) {
            if (evt.key === 'Enter') { evt.preventDefault(); envoyerAppel(); }
          });
        } else {
          // ── VARIANTE 'contact' (24/11/2026) : 3 ecrans de 2 champs ("2 -> 2 -> 2") ──
          var pointsHtml = '<div class="cme-mf-progression" style="display:flex;gap:6px;margin-bottom:14px;">' +
            PAGES_CONTACT.map(function (_, idx) {
              return '<span class="cme-mf-point" data-idx="' + idx + '" style="height:5px;flex:1;border-radius:3px;background:rgba(15,23,42,.15);transition:background .2s;"></span>';
            }).join('') +
          '</div>';
          corpsWrap.innerHTML = pointsHtml + PAGES_CONTACT.map(function (page, idx) {
            var estDerniere = idx === PAGES_CONTACT.length - 1;
            var champsHtml = page.map(champHtml).join('');
            var piedHtml = estDerniere ? rgpdHtml : '';
            var texteBtn = estDerniere ? 'Envoyer →' : 'Suivant →';
            return '<div class="cme-mf-page" style="display:' + (idx === 0 ? '' : 'none') + ';">' +
              champsHtml + piedHtml +
              '<div class="cme-mf-erreur" style="color:#dc2626;font-size:13px;margin-bottom:10px;display:none;"></div>' +
              '<button type="button" class="cme-mf-suiv" style="width:100%;background:' + FORMULAIRE_ACCENT + ';color:#1f2937;font-weight:700;font-size:16px;padding:13px 24px;border:none;border-radius:9px;cursor:pointer;">' + texteBtn + '</button>' +
            '</div>';
          }).join('');

          var pagesEl = Array.prototype.slice.call(corpsWrap.querySelectorAll('.cme-mf-page'));
          var pageActuelle = 0;
          var valeursContact = {};

          function majProgression() {
            var points = corpsWrap.querySelectorAll('.cme-mf-point');
            for (var k = 0; k < points.length; k++) {
              points[k].style.background = k <= pageActuelle ? FORMULAIRE_ACCENT : 'rgba(15,23,42,.15)';
            }
          }
          majProgression();

          function marquerChoixSelectionne(groupeEl, valeur) {
            var boutons = groupeEl.querySelectorAll('.cme-mf-choix-btn');
            for (var k = 0; k < boutons.length; k++) {
              var actif = boutons[k].getAttribute('data-valeur') === valeur;
              boutons[k].style.borderColor = actif ? FORMULAIRE_ACCENT : '#e5e7eb';
              boutons[k].style.background = actif ? '#fffbeb' : '#fff';
              boutons[k].style.color = actif ? '#92400e' : '#374151';
            }
          }
          corpsWrap.addEventListener('click', function (evt) {
            var btn = evt.target.closest ? evt.target.closest('.cme-mf-choix-btn') : null;
            if (!btn) { return; }
            valeursContact[btn.getAttribute('data-champ')] = btn.getAttribute('data-valeur');
            marquerChoixSelectionne(btn.parentNode, btn.getAttribute('data-valeur'));
          });

          function validerChampContact(champDef, valeur) {
            valeur = (valeur || '').trim();
            if (champDef.type === 'choix') { return valeur ? '' : 'Merci de faire un choix.'; }
            if (champDef.champ === 'prenom') { return valeur.length >= 2 ? '' : 'Entrez vos nom et prénom.'; }
            if (champDef.champ === 'telephone') { return valeur.replace(/\D/g, '').length >= 8 ? '' : 'Numéro invalide.'; }
            if (champDef.champ === 'code_postal') { return valeur.replace(/\D/g, '').length === 5 ? '' : 'Code postal invalide.'; }
            if (champDef.champ === 'email') { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valeur) ? '' : 'E-mail invalide.'; }
            return '';
          }
          function afficherErreurPage(pageEl, msg) {
            var erreurEl = pageEl.querySelector('.cme-mf-erreur');
            if (!erreurEl) { return; }
            if (msg) { erreurEl.textContent = msg; erreurEl.style.display = 'block'; }
            else { erreurEl.style.display = 'none'; }
          }
          function afficherMerciContact() {
            corpsWrap.innerHTML =
              '<div style="text-align:center;padding:6px 0;">' +
                '<div style="font-size:28px;">✅</div>' +
                '<div style="font-weight:700;font-size:15px;color:#111827;margin-top:8px;">Merci, un expert vous recontacte rapidement.</div>' +
              '</div>';
          }
          function validerPageActuelle() {
            var pageEl = pagesEl[pageActuelle];
            var page = PAGES_CONTACT[pageActuelle];
            var premiereErreur = '';
            for (var k = 0; k < page.length; k++) {
              var champDef = page[k];
              var valeurActuelle;
              if (champDef.type === 'choix') {
                valeurActuelle = valeursContact[champDef.champ] || '';
              } else {
                var inputEl = pageEl.querySelector('.cme-mf-input[data-champ="' + champDef.champ + '"]');
                valeurActuelle = inputEl ? inputEl.value : '';
                valeursContact[champDef.champ] = valeurActuelle.trim();
              }
              var erreur = validerChampContact(champDef, valeurActuelle);
              if (erreur && !premiereErreur) { premiereErreur = erreur; }
            }
            if (!premiereErreur && pageActuelle === PAGES_CONTACT.length - 1) {
              var caseRgpd = pageEl.querySelector('.cme-mf-rgpd-case');
              if (caseRgpd && !caseRgpd.checked) { premiereErreur = 'Merci d’accepter la politique de confidentialité pour continuer.'; }
            }
            if (premiereErreur) { afficherErreurPage(pageEl, premiereErreur); return false; }
            afficherErreurPage(pageEl, '');
            return true;
          }
          function allerPageSuivante() {
            if (!validerPageActuelle()) { return; }
            if (pageActuelle === PAGES_CONTACT.length - 1) {
              envoyerLead(valeursContact, n, prefixe, variante);
              journaliserInteraction({ type_evenement: 'form_etape', position_contenu: n, etape: 'termine', silo: prefixe, cible: variante });
              DERNIER_ETAT = null;   // termine : plus rien a detecter comme abandon pour cette instance
              afficherMerciContact();
              return;
            }
            pagesEl[pageActuelle].style.display = 'none';
            pageActuelle++;
            pagesEl[pageActuelle].style.display = '';
            majProgression();
            journaliserInteraction({ type_evenement: 'form_etape', position_contenu: n, etape: String(pageActuelle), silo: prefixe, cible: variante });
            if (DERNIER_ETAT) { DERNIER_ETAT.etape = String(pageActuelle); }
            var premierInput = pagesEl[pageActuelle].querySelector('.cme-mf-input');
            if (premierInput) { premierInput.focus(); }
          }
          pagesEl.forEach(function (p) {
            p.querySelector('.cme-mf-suiv').addEventListener('click', allerPageSuivante);
          });
          corpsWrap.addEventListener('keydown', function (evt) {
            if (evt.key === 'Enter') { evt.preventDefault(); allerPageSuivante(); }
          });
        }

        d.innerHTML =
          '<div style="padding:18px 20px 10px;">' +
            '<div style="color:#fff;font-weight:700;font-size:16px;margin-bottom:6px;">' + texteIntro + '</div>' +
            '<div style="color:rgba(255,255,255,.8);font-size:12px;">' + texteReassurance + '</div>' +
          '</div>';
        d.appendChild(corpsWrap);

        // Visibilite reelle (pas juste "present dans le DOM" -- insere via
        // JS, le formulaire existe souvent avant d'etre scrolle en vue) :
        // une seule fois par instance, seuil 50% visible.
        if (window.IntersectionObserver) {
          var observateurVue = new IntersectionObserver(function (entrees) {
            for (var k = 0; k < entrees.length; k++) {
              if (entrees[k].isIntersecting) {
                journaliserInteraction({ type_evenement: 'form_vu', position_contenu: n, silo: prefixe, cible: variante });
                // etape initiale : 'vu' pour 'appel' (pas d'ecran
                // intermediaire, inchange) ; '0' pour 'contact' (1er des 3
                // ecrans, mis a jour a chaque allerPageSuivante() -- voir
                // plus haut) -- 24/11/2026.
                DERNIER_ETAT = { position: n, vu: true, silo: prefixe, variante: variante, etape: estAppel ? 'vu' : '0' };
                observateurVue.disconnect();
                break;
              }
            }
          }, { threshold: 0.5 });
          window.setTimeout(function () { observateurVue.observe(d); }, 0);   // apres insertion dans le DOM
        }

        return d;
      }

      // ── Comparateur energie au 1er emplacement (16/11/2026) ────────────
      // Demande operateur explicite : remplacer UNIQUEMENT la 1ere occurrence
      // du mini-formulaire "contact-expert-inline" (poses===0 dans la boucle
      // plus bas) par le widget comparateur-energie, sur TOUS les silos,
      // anciens et nouveaux articles -- les occurrences suivantes (2e, 3e...)
      // restent creer(n,'contact') inchange, jamais touchees. Insertion cote
      // CLIENT, meme principe de couverture retroactive "gratuite" que
      // creer() lui-meme (aucune reecriture du contenu stocke de chaque
      // article). window.cmeCmpInit est expose globalement par
      // comparateur-energie.js (wp_enqueue_script, meme page) -- fiable des
      // l'execution de ce script car DOMContentLoaded (qui declenche
      // demarrer()) ne peut se produire qu'apres l'execution de TOUS les
      // <script> synchrones de la page, quel que soit leur ordre relatif
      // d'impression en pied de page. Le nonce/l'URL ajax sont localises par
      // cme_cmp_enqueue_assets() (comparateur-energie.php) dans
      // window.CME_CMP_BOOT.
      //
      // Filet de securite volontaire : si CME_CMP_BOOT ou cmeCmpInit sont
      // indisponibles pour une raison quelconque (plugin desactive, echec
      // d'enqueue, script bloque...), on ne cree PAS le placeholder -- on
      // retombe sur l'ancien mini-formulaire a ce 1er emplacement, pour ne
      // jamais laisser un "⏳ Chargement..." bloque a l'ecran du visiteur, ni
      // perdre silencieusement la capture de lead a cette position.
      function comparateurDisponible() {
        return !!(window.CME_CMP_BOOT && window.CME_CMP_BOOT.nonce && window.CME_CMP_BOOT.ajax && window.cmeCmpInit);
      }
      function creerComparateur(prefixeSilo) {
        var uid = 'cmeinline' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
        // CORRECTIF (16/11/2026, suite) : toujours 'dual', quel que soit le
        // silo -- une premiere version faisait varier data-eg par silo
        // (gaz->'gaz', electricite->'elec'), en pensant a tort que EDEF ne
        // faisait que PRESELECTIONNER un onglet tout en laissant l'autre
        // accessible. Verifie dans comparateur-energie.js : EDEF='gaz'/'elec'
        // VERROUILLE entierement le parcours sur une seule energie (aucun
        // selecteur d'energie a l'etape 1, aucun onglet a l'etape 3 -- voir
        // les conditions `if(EDEF==='dual')`). Constate en prod par
        // l'operateur : silo Gaz -> comparatif gaz uniquement, silo
        // Electricite -> comparatif elec uniquement. Demande explicite :
        // laisser le lecteur choisir lui-meme, jamais de presupposition par
        // silo -- donc 'dual' partout, sans exception, prefixeSilo n'est
        // plus utilise (parametre garde pour l'appel existant, sans effet).
        var energieDefaut = 'dual';
        var d = document.createElement('div');
        d.id = uid;
        d.className = 'cme-comp';
        d.style.cssText = 'margin:28px 0;clear:both;';
        d.setAttribute('data-eg', energieDefaut);
        d.setAttribute('data-cme-nonce', window.CME_CMP_BOOT.nonce);
        d.setAttribute('data-ajax', window.CME_CMP_BOOT.ajax);
        d.setAttribute('data-cme-init', '1');   // deja initialise ci-dessous, evite un double-scan
        return d;
      }
      function initialiserComparateur(uid) {
        var el = document.getElementById(uid);
        if (!el) { return; }
        window.cmeCmpInit(uid, el.getAttribute('data-eg'), el.getAttribute('data-cme-nonce'), el.getAttribute('data-ajax'));
      }

      var enfants = enfantsEffectifs(zone);   // "deplie" les blocs Colonnes -- voir docblock, correctif du 04/11/2026
      var i;
      // apres[i] : mots restant apres l'element i avant le prochain formulaire existant (ou la fin)
      var apres = [];
      var acc = 0;
      for (i = enfants.length - 1; i >= 0; i--) {
        apres[i] = acc;
        if (estCta(enfants[i])) { acc = 0; } else { acc += mots(enfants[i]); }
      }

      // Cadence absolue (04/11/2026) : totalMotsVus ne se reinitialise JAMAIS
      // (sauf qu'on ne compte pas les mots d'un formulaire deja existant,
      // comme avant) -- le seuil a atteindre est calcule depuis le DEBUT de
      // l'article, pas depuis le dernier formulaire pose. Voir
      // prochainSeuilContact() dans les REGLAGES plus haut.
      var totalMotsVus = 0;
      var poses = 0;
      var comparateurPose = false;   // true si le 1er emplacement a bien recu le comparateur (pas le mini-formulaire)
      for (i = 0; i < enfants.length; i++) {
        var el = enfants[i];
        if (estCta(el)) { continue; }
        totalMotsVus += mots(el);
        if (poses >= MAX_FORMULAIRES_CONTACT) { break; }
        if (totalMotsVus < prochainSeuilContact(poses)) { continue; }
        if (!/^(P|UL|OL|TABLE|FIGURE|BLOCKQUOTE)$/.test(el.tagName)) { continue; }   // jamais apres un titre, ni au milieu d'un bloc
        var suivantEl = enfants[i + 1];
        if (!suivantEl || estCta(suivantEl) || estVide(suivantEl)) { continue; }
        if (apres[i] < MOTS_FIN_MIN) { continue; }   // trop pres d'un formulaire existant ou de la fin
        // suivantEl peut desormais etre imbrique dans un wp-block-column (voir
        // enfantsEffectifs() plus haut) -- insertBefore exige le PARENT REEL
        // de l'element de reference, jamais `zone` directement (qui echouerait
        // silencieusement/leverait si suivantEl n'est pas son enfant direct).
        var premierSlot = (poses === 0) && comparateurDisponible();
        var elementAInserer = premierSlot ? creerComparateur(prefixe) : creer(poses + 1, 'contact');
        suivantEl.parentNode.insertBefore(elementAInserer, suivantEl);
        if (premierSlot) { initialiserComparateur(elementAInserer.id); comparateurPose = true; }
        poses++;
      }

      // ── CTA "avant d'appeler" (01/11/2026) : une seule occurrence par
      // article, ajoutee en toute fin de contenu, voir docblock. N'affecte
      // pas la frequence/position des formulaires de contact ci-dessus
      // (traversee independante, aucun partage d'etat avec `poses`/`totalMotsVus`).
      var totalMots = 0;
      for (i = 0; i < enfants.length; i++) {
        if (!estCta(enfants[i])) { totalMots += mots(enfants[i]); }
      }
      var posesAppel = 0;
      if (totalMots >= MOTS_MIN_CTA_APPEL && enfants.length) {
        zone.appendChild(creer(poses + 1, 'appel'));
        posesAppel = 1;
      }

      if (MODE === 'apercu' && window.console) {
        window.console.log('cme-cta60 : ' + poses + ' formulaire(s) contact pose(s) (dont 1er = comparateur : ' + comparateurPose + '), ' + posesAppel + ' formulaire(s) appel pose(s), silo ' + prefixe);
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
