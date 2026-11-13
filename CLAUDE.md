# CLAUDE.md — règles opérationnelles du projet CME SEO Pipeline

Ce fichier documente les règles et pièges spécifiques à ce projet, appris en
production. Le README.md décrit l'architecture ; ce fichier décrit comment
y travailler sans casser quelque chose.

## Contexte

Écosystème automatisé de génération de contenu SEO + génération de leads
pour comprendre-mon-energie.fr. Un seul opérateur (Oussama), travaille
principalement via Google Cloud Shell. Pipeline Python (GitHub Actions) qui
publie des articles sur WordPress (REST API) + BigQuery pour les données.

**⚠️ Ce repo est PUBLIC sur GitHub** (vérifié via `gh api repos/.../... --jq
'{private,visibility}'`), malgré ce qu'indique le README ("This repository
is private"). À corriger dans le README, et à garder en tête en permanence :
**aucun secret ne doit jamais être écrit en dur dans un fichier du repo**,
même temporairement, même dans un script de test ou un commentaire.

## Secrets — règle absolue

Tous les secrets (mot de passe WordPress, clés API, clé de service GCP)
vivent **uniquement** dans :
- **Google Secret Manager** (`seo-data-hub-cme`) — lu via
  `gcloud secrets versions access latest --secret=NOM --project=seo-data-hub-cme`
- **GitHub Actions secrets** (Settings → Secrets and variables → Actions) —
  lus par les workflows via `${{ secrets.NOM }}`

Jamais en dur dans un fichier du repo. Les scripts lisent les secrets via
variables d'environnement, avec un garde-fou explicite :
```python
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")
```
**Incident réel (15 oct. 2026)** : un mot de passe WordPress en clair a été
trouvé dans `scripts-maintenance/cta_retroactif.py` et
`cta_wordpress_complet.py` (repo public). Révoqué côté WordPress, les deux
scripts corrigés pour lire l'environnement. **Toujours vérifier qu'un script
de maintenance ne contient pas de secret en dur avant de le committer**,
surtout dans `scripts-maintenance/` (scripts écrits rapidement, souvent
copiés-collés entre eux).

Quand un secret change : le propager **aux deux endroits** (Secret Manager
ET GitHub Actions secrets) — un seul des deux suffit à casser soit les runs
manuels (Cloud Shell), soit le pipeline automatisé quotidien.

## Les CTA simulateurs → page de contact unique (chantier oct. 2026)

Les 3 anciens simulateurs (comparateur gaz/élec, simulateur aides
rénovation, devis solaire) ont été remplacés par une page de contact unique
(`/contactez-un-expert/`) comme destination de tous les CTA du site, sans
paramètre de tracking (`?src_post=`/`&pos=` retirés, décision explicite :
une seule destination, plus besoin de distinguer la source).

**Il existe TROIS emplacements distincts et indépendants où un lien CTA
peut vivre** — à vérifier/modifier TOUS LES TROIS à chaque future évolution
des CTA, aucun des trois ne couvre les autres :

1. **`pipeline/pipeline.py`** (`CTA_TOOLS`, `generer_cta_html()`,
   `inserer_ctas_repartis()`) — génère le bloc CTA baké en dur dans le
   contenu de **chaque nouvel article** au moment de la publication.
   N'affecte PAS les articles déjà publiés.
2. **`wordpress-mu-plugins/cme-cta-progressifs.php`** — mu-plugin déployé
   manuellement en cPanel (`/wp-content/mu-plugins/`), injecte des bandeaux
   CTA en JS côté client à chaque visite, sur TOUS les articles (anciens et
   nouveaux). **Pas versionné automatiquement sur le serveur** : toute
   modification de ce fichier dans le repo doit être téléchargée
   (`cloudshell download`) puis téléversée manuellement en cPanel (renommer
   l'ancien en `.bak` avec un nom horodaté pour ne pas écraser une sauvegarde
   existante, uploader le nouveau, purger le cache). Le lien ZENDURE
   (`lienExact: true`) est un partenariat d'affiliation Awin distinct, à ne
   jamais toucher dans ce contexte.
3. **Un widget global du footer** (zone `footer-widget-1`, bloc WordPress
   natif, visible dans le HTML sous forme `<aside id="block-NN"
   class="widget inner-padding widget_block">`) — édité à la main dans
   wp-admin → Apparence → Widgets (ou l'éditeur de site si FSE). S'affiche
   identique sur **toutes** les pages du site. Ni script Python ni mu-plugin
   ne peuvent le voir ou le modifier — c'est un contenu WordPress natif,
   hors `post_content`, hors fichier PHP du repo.

Pour corriger rétroactivement les articles déjà publiés :
`scripts-maintenance/fix_cta_liens_retroactif.py` (dry-run par défaut,
`--apply` pour écrire réellement, `--limite=N` pour cibler les N premiers
articles **qui ont réellement un lien à corriger** — pas les N premiers de
la liste, souvent les plus récents et déjà propres). **Piège découvert en
prod** : les blocs CTA n'ont pas tous le même ordre d'attributs dans la
balise `<a>` selon l'ancienneté du gabarit utilisé au moment de la
publication (`<a href="..." style="...">` vs `<a style="..." href="...">`)
— toute regex de détection/remplacement doit repérer le `href` **peu
importe sa position** parmi les attributs, jamais supposer qu'il est le
premier.

## CTA — arrêt des bannières flottantes (22/10/2026)

Décision explicite du porteur de projet, suite au diagnostic trafic/conversion
du 22/10 (doc Claude "Stratégie d'augmentation des clics CTA") : **plus
aucune bannière flottante sur le site**, quelle qu'elle soit. Concerne
uniquement `wordpress-mu-plugins/cme-cta-progressifs.php` — l'insertion
progressive dans le corps du texte (toutes les ~230 mots, fonction
`demarrer()`) n'est pas une bannière et n'a pas été retirée, mais **a été
transformée en mini-formulaire** le même jour, voir la section suivante
("Formulaire de contact progressif").

Deux mécanismes retirés du fichier (code + appels dans l'IIFE) :
- **Bannière flottante Zendure** (`demarrerZendureFlottant`, objet `ZENDURE`,
  `SILOS_ZENDURE_FLOTTANT`) — partenariat d'affiliation Awin (code promo
  AF5E24, -5%), qui devait de toute façon s'arrêter automatiquement le
  01/11/2026. **Implication business à garder en tête** : ça coupe le
  partenariat Awin ~10 jours avant son terme naturel — décision assumée par
  l'opérateur, mais à signaler si quelqu'un d'autre gère cette relation
  commerciale.
- **Bannière flottante app Android / "Contactez un expert"**
  (`demarrerAppFlottant`, `afficherApp`, `appSilence`/`appMemoriser`,
  variables `APP_*`/`EXPERT_HORS_ANDROID`/`EXPERT_URL`).

Code supprimé plutôt que commenté (reste consultable dans l'historique git,
commit du 22/10, si l'un des deux partenariats devait reprendre). `php -l`
validé après coup, aucune référence orpheline (`ZENDURE`, `demarrerAppFlottant`
etc. absents du fichier après coup, vérifié par grep).

**Déploiement — même contrainte que d'habitude pour ce fichier** (voir plus
bas) : non versionné automatiquement sur le serveur. L'opérateur doit
`cloudshell download` le fichier corrigé, renommer l'ancien en `.bak`
horodaté en cPanel, uploader le nouveau dans `/wp-content/mu-plugins/`,
purger les deux caches LiteSpeed, vérifier avec `?t=$RANDOM` sur un article
qui affichait une des deux bannières (silo gaz/électricité/aide/rénovation/
solaire) qu'aucune des deux n'apparaît plus après 30-60 secondes.

## Formulaire de contact progressif — remplacement du bouton CTA (22/10/2026)

Décision explicite du porteur de projet, le même jour que l'arrêt des
bannières ci-dessus : le bouton CTA "Contactez un expert" inséré toutes les
~230 mots ne doit plus renvoyer vers `/contactez-un-expert/`, mais devenir
**un mini-formulaire interactif intégré directement dans l'article**
(type Typeform, une question affichée à la fois), pour inciter au
remplissage sans faire quitter la page. Portée explicitement demandée :
**nouveaux articles ET rétroactif sur les articles déjà publiés** — pas une
option plus simple (ex. nouveaux articles uniquement), refusée.

**Pourquoi pas le shortcode WPForms directement** : WordPress/WPForms
décide côté serveur, **avant le rendu de la page**, s'il faut charger son
CSS/JS/nonces — en détectant le shortcode/bloc dans le contenu **stocké**
de l'article au moment du rendu. Un shortcode inséré côté client par ce
mu-plugin arrive après coup : WPForms n'aurait jamais chargé ses propres
assets, et le formulaire ne fonctionnerait pas (pas de soumission possible).
D'où un mini-formulaire maison (HTML/CSS/JS pur, sans dépendance), seule
option fiable pour une insertion dynamique côté client.

**Implémentation** (`wordpress-mu-plugins/cme-cta-progressifs.php`) :
- La fonction `creer(n)` (appelée par `demarrer()`, logique de répartition
  toutes les ~230 mots **inchangée**) génère désormais un mini-formulaire
  multi-étapes au lieu d'un bouton : barre de progression, un champ visible
  à la fois (`prenom` → `telephone` → `email` → `code_postal`), validation
  inline, navigation clavier (Entrée = étape suivante), étape finale "Merci"
  après soumission. Une seule fonction génératrice réutilisée à chaque
  position : c'est ce qui rend le mécanisme **modulaire** plutôt que de
  dupliquer du balisage par position.
- **Le rétroactif est couvert "gratuitement"** : ce mécanisme tourne déjà
  côté client sur chaque page article, ancienne ou nouvelle (`wp_footer` +
  `is_singular('post')`) — nul besoin de réécrire le contenu stocké de
  chaque article pour que le nouveau formulaire y apparaisse.
- **Champs retenus — hypothèse à confirmer par l'opérateur** : `prenom`,
  `telephone`, `email`, `code_postal`, repris du schéma déjà en place
  (`leads_convertis` / `tracking-api/server.py`), **pas nécessairement**
  la liste exacte des champs du vrai formulaire WPForms #472 sur
  `/contactez-un-expert/`, que ce sandbox ne peut pas inspecter (pas
  d'accès au site live). À ajuster si l'opérateur confirme une liste
  différente.
- **Soumission** : poste directement en JSON vers le relais déjà déployé
  et déjà validé en prod `/wp-json/cme/v1/log-lead` (voir
  `cme-tracking-conversion.php`), qui républie côté serveur vers l'API
  Cloud Run → table `leads_convertis`. **Aucun nouveau code backend
  nécessaire.** `tool = 'contact-expert-inline'` pour distinguer ces
  soumissions des autres (`contact-expert-formulaire`, `appel-telephone`).
  Pousse aussi `dataLayer.push({event: 'generate_lead_inline', ...})` —
  **à marquer comme Key Event dans GA4 si l'opérateur veut le suivre
  séparément du `generate_lead` existant** (Claude Code n'a pas accès à
  cette configuration).
- Un petit `<script>` séparé, interpolé côté PHP (`get_the_ID()`), expose
  `window.CME_POST_ID` pour l'attribution `source_post_id` du lead — seule
  valeur injectée côté serveur, le reste du script JS reste un bloc statique
  (nowdoc) comme avant.

**Côté pipeline** (`pipeline/pipeline.py`, fonction `publier_article()`) :
l'ancienne injection du CTA statique à la publication
(`inserer_ctas_repartis()`, appelée dans le PATCH juste après la création
du post) a été **désactivée** pour les nouveaux articles — elle serait
redondante avec le nouveau formulaire dynamique, et superposerait un vieux
bouton statique ET le nouveau formulaire sur le même article. La fonction
`inserer_ctas_repartis()`/`generer_cta_html()` n'a pas été supprimée du
fichier (gardée si ce choix devait être révisé), juste son appel.

**Nettoyage rétroactif** (`scripts-maintenance/nettoyer_anciens_cta_statiques.py`,
dry-run par défaut, `--apply` pour écrire, pattern habituel du projet) :
retire des articles déjà publiés les anciens blocs CTA statiques (gabarit
`generer_cta_html()` : `<div style="background:linear-gradient(...)">`
contenant `<h3>`/`<p>`/`<a>…Contactez un expert…</a>`), pour qu'ils ne
restent pas affichés en double avec le nouveau formulaire dynamique. Détection
via BeautifulSoup (pas de regex sur du HTML imbriqué — plus fiable face aux
variations de mise en forme, même piège de principe que l'ordre des
attributs `href` déjà documenté pour `fix_cta_liens_retroactif.py`, mais ici
il s'agit de retirer tout le bloc, pas de modifier un attribut). Testé avec
un échantillon HTML fabriqué localement (le vrai gabarit, un paragraphe
éditorial normal avec un lien interne, et un encart sans rapport) : retire
exactement le bloc CTA attendu, laisse le reste intact.

**Testé en lecture seule sur les données réelles le 22/10 via le pont
GitHub Actions** : 818 articles publiés au total, **803 avec au moins un
vieux bloc CTA statique à retirer, 1333 blocs au total** (3 par article
dans l'immense majorité des cas — cohérent avec `inserer_ctas_repartis()`
qui en posait jusqu'à 3). **Piège rencontré au premier essai** : le
workflow `maintenance-a-la-demande.yml` exige le **chemin complet**
`scripts-maintenance/<script>.py` en entrée (son étape de garde-fou rejette
tout chemin qui ne commence pas par `scripts-maintenance/`) — un premier
essai avec juste le nom de fichier a échoué silencieusement (aucun log
committé, le job échoue avant même d'atteindre l'étape qui écrit le log).

**Appliqué en conditions réelles le 26/10/2026** : test `--limite=5 --apply`
validé par l'opérateur (5 articles, 15 blocs, 0 erreur), puis `--apply`
sans limite sur le reste. **Piège rencontré** : le premier run complet
(646 articles restants) s'est fait annuler par une limite de temps du
workflow GitHub Actions (~30 min, `timeout-minutes` du job, pas une action
volontaire) après avoir déjà traité 645 articles avec succès (0 erreur) —
le script étant idempotent (ne retouche que les articles ayant encore
l'ancien bloc), un simple second `gh workflow run` avec les mêmes arguments
a repris automatiquement là où ça s'était arrêté et traité les 142
restants, cette fois sans dépasser le délai. **Total : 792 articles
nettoyés, 0 erreur sur l'ensemble**. Si un futur nettoyage de masse de ce
type dépasse la limite de temps du workflow, relancer simplement la même
commande plutôt que chercher à augmenter le timeout — plus simple et sans
risque de double-traitement grâce à l'idempotence du script.

**Déploiement — même contrainte que d'habitude** pour
`cme-cta-progressifs.php` : non versionné automatiquement sur le serveur.
Vu qu'il s'agit d'un composant interactif entièrement nouveau (jamais testé
visuellement, ce sandbox n'a pas d'accès navigateur/site live), **recommandé
avant un déploiement direct en mode `actif`** : repasser temporairement
`MODE` à `'apercu'` lors du premier upload cPanel, vérifier le rendu réel
sur un article de chaque silo avec `?cta60=1`, puis repasser `MODE` à
`'actif'` une fois validé visuellement — le mode apercu existe justement
pour ce genre de vérification à moindre risque.

**Déployé et validé en conditions réelles le 22/10** (confirmé par
l'opérateur, formulaire fonctionnel sur le site live).

**Couleurs unifiées (22/10/2026, suite)** : les 4 couleurs par silo
(bleu/ambre/vert selon gaz-électricité/aides/solaire) ont été remplacées
par **une identité visuelle unique sur tout le site** — demande explicite
de l'opérateur ("unifier les couleurs du formulaire... une couleur qui
correspond à l'identité du site et qui favorise la conversion"). Fond du
formulaire repris du vrai logo du site (navy `#0a1120`/bleu accent
`#60a5fa`, trouvés dans `scripts-maintenance/patch_logo_entete.py`, seule
source fiable de l'identité de marque accessible depuis ce sandbox — pas
d'accès au thème WordPress live) : dégradé `#0f172a` → `#1e3a8a`. Bouton
d'action en ambre `#f59e0b` (déjà utilisé côté silo aides ailleurs sur le
site) : contraste volontairement chaud sur fond froid plutôt qu'une
couleur assortie au fond, principe standard de conversion (un bouton qui
« ressort » visuellement du reste de la carte est cliqué davantage qu'un
bouton qui s'y fond). Texte du bouton en gris foncé (`#1f2937`, pas blanc)
pour un contraste lisible sur fond ambre. Le texte d'accroche reste
personnalisé par silo (`GAZ`/`ELEC`/`AIDES`/`SOLAIRE` ne portent plus que
`texte`, les couleurs ont été retirées de ces objets et centralisées dans
`FORMULAIRE_FOND1`/`FORMULAIRE_FOND2`/`FORMULAIRE_ACCENT`).

## Formulaire progressif — RGPD, Google Sheets et finitions UX (22/10/2026, suite)

Trois ajouts demandés par l'opérateur après le premier déploiement validé en
prod (couleurs unifiées + confirmation que le formulaire fonctionne) :

**1. Case RGPD obligatoire** (`cme-cta-progressifs.php`, dernière étape
`code_postal`) : case à cocher requise, bloque l'envoi si non cochée
(vérifiée dans `suivant()`, pas seulement côté style). Texte et lien repris
**à l'identique de l'existant** sur les anciens simulateurs
(`wordpress-plugins/simulateur-*`, qui avaient déjà cette case) :
`https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/`
(page réelle de politique de confidentialité/mentions légales du site —
seule URL légale trouvée dans le repo, à confirmer par l'opérateur si une
autre page existe entretemps).

**2. Relais vers Google Sheets** : les leads de ce formulaire arrivaient
uniquement dans BigQuery (`leads_convertis`), invisibles dans le classeur
Google Sheets que l'opérateur utilise déjà pour surveiller les leads des 3
anciens simulateurs + espace client (`SPREADSHEET_ID
1LBgHQPioaT0buv9rev5egywRDtE8hKIFHFVwjNqw00o`, un onglet par source, via
`apps-scripts/cme-*-leads.gs`). Nouveau fichier
**`apps-scripts/cme-formulaire-article-leads.gs`** suivant exactement ce
patron (même classeur, nouvel onglet "Leads Formulaire Article"). Branché
**côté serveur** dans `cme-tracking-conversion.php`
(`cme_relayer_log_lead()`, nouvelle constante
`CME_APPS_SCRIPT_LEADS_INLINE_URL`) via `wp_remote_get` avec le payload en
query string — même mécanisme que celui déjà utilisé par
`wordpress-plugins/simulateur-solaire/simulateur-solaire.php` pour son
propre relais vers Apps Script (code source du relais historique, pas
réécrit à la main), choisi plutôt qu'un second appel JS côté client pour
rester cohérent avec l'architecture existante et ne pas dupliquer la
logique de formatage du payload. **Scope volontairement restreint** au
`tool = 'contact-expert-inline'` : ne touche pas les clics `tel:` ni les
soumissions du vrai formulaire de contact, qui n'alimentaient pas de Sheet
avant et ne doivent pas commencer à y arriver sans qu'on l'ait demandé.
**Nécessite une action manuelle de l'opérateur** (pas faisable depuis ce
sandbox, pas d'accès à script.google.com) : déployer
`cme-formulaire-article-leads.gs` comme Web App (voir son commentaire
d'installation), copier l'URL `/exec` générée dans la constante
`CME_APPS_SCRIPT_LEADS_INLINE_URL` (actuellement vide = no-op silencieux,
n'affecte pas le relais Cloud Run existant), puis redéployer
`cme-tracking-conversion.php` en cPanel comme d'habitude.

**Bug annexe corrigé au passage** : le payload envoyé par le formulaire ne
contenait pas `source_page` (URL de l'article) — absent aussi bien du
nouvel onglet Sheets que de la colonne `leads_convertis.source_page` côté
BigQuery, alors que les autres sources de leads l'incluent toutes.
Ajouté dans `envoyerLead()` (`window.location.href`).

**3. Finitions UI/UX pour la conversion** (`cme-cta-progressifs.php`) :
- Icônes par étape (👋/📱/✉️/📍) pour une sensation plus humaine.
- Phrase de réassurance sous l'accroche ("🔒 Vos données restent
  confidentielles · un conseiller vous recontacte sous 24h").
- États `:focus` (champ actif, bordure + halo bleu marque) et `:hover`
  (bouton, ambre plus soncé) — impossibles à poser avec de simples
  attributs `style=""` en ligne, ajoutés via une petite feuille de style
  injectée **une seule fois par page** (`injecterStyles()`, idempotent via
  un id, pas une balise `<style>` par formulaire).
- Transition de fondu (`opacity`) à chaque changement d'étape plutôt qu'un
  bascule brut `display:none`/`block`.

**Déployé et validé en conditions réelles le 22/10** : `CME_APPS_SCRIPT_LEADS_INLINE_URL`
renseignée par l'opérateur
(`apps-scripts/cme-formulaire-article-leads.gs` déployé comme Web App),
les deux fichiers redéployés en cPanel. Confirmé par l'opérateur
(nouvelle ligne visible dans l'onglet "Leads Formulaire Article") ET
vérifié côté BigQuery via `scripts-maintenance/verifier_leads_formulaire_inline.py`
(pont GitHub Actions) : 4 lignes `tool='contact-expert-inline'` sur les
48h précédentes, dont un test à 15h20 UTC le 22/10 avec `source_page`
correctement renseignée (confirme au passage le correctif de ce champ,
absent des 2 tests les plus anciens de la même série, faits avant son
ajout). Les deux destinations (BigQuery + Sheets) reçoivent bien la même
soumission — chantier formulaire progressif entièrement clos et en
production à cette date.

## Formulaire progressif — réduction à 2 questions (24/10/2026)

Suite à l'analyse d'un vrai lead ("Lionel", 22/10 14:39:56, voir incident
Sheets ci-dessous) et à la demande explicite de l'opérateur : le
mini-formulaire inline (`cme-cta-progressifs.php`) passe de 4 questions
(prénom, téléphone, email, code postal) à **2 questions** (nom et prénom
— un seul champ, clé technique `prenom` inchangée pour rester compatible
sans migration —, puis téléphone), pour minimiser la friction au
remplissage. La case CGU/RGPD reste sur la **dernière étape de saisie**,
désormais "téléphone" (le code l'attache dynamiquement à `ETAPES[ETAPES.length-1]`,
donc aucun branchement supplémentaire nécessaire). Email et code postal
ont été explicitement écartés par l'opérateur (trade-off assumé : on perd
l'email comme canal de recontact, le téléphone suffit pour le rappel sous
24h annoncé dans le formulaire) — une proposition intermédiaire à 3
questions (en gardant un champ adresse) a été proposée puis refusée par
l'opérateur, qui a tranché pour 2 questions seulement.

Aucun changement côté `cme-tracking-conversion.php` (le relais republie le
payload brut, sans supposer la présence d'un champ) ni côté
`apps-scripts/cme-formulaire-article-leads.gs` (`ecrireSheet()` utilise déjà
`d.email || ''` / `d.code_postal || ''`, donc ces deux colonnes restent
simplement vides pour les nouvelles soumissions — pas de migration de
schéma nécessaire, ni côté BigQuery ni côté Sheets). Validé via `php -l`
et extraction du bloc JS (`node --check`) après modification.

**Même contrainte de déploiement que d'habitude** pour
`cme-cta-progressifs.php` : non versionné automatiquement sur le serveur,
`cloudshell download` + `.bak` horodaté + upload cPanel + purge des 2
caches LiteSpeed requis après ce commit pour que le changement soit visible
en prod.

**Déployé et validé en conditions réelles le 24/10** : l'opérateur a
redéployé le fichier en cPanel et confirmé visuellement le formulaire à 2
étapes (nom et prénom, puis téléphone) sur un article réel. Soumission de
test confirmée côté BigQuery (`scripts-maintenance/verifier_leads_formulaire_inline.py`,
ligne du 24/10 20:02:27 UTC) : `prenom="Oussama Blal"`, `telephone` rempli,
**`email` et `code_postal` bien vides** comme attendu, `source_page`/
`source_post_id`/`details` (position + silo) correctement renseignés —
réduction à 2 questions entièrement validée de bout en bout.

## Incident — lead réel non retrouvé dans Sheets (24/10/2026)

**Constat** : le lead "Lionel" (contact-expert-inline, 22/10 14:39:56 UTC,
`source_post_id=5502`, article sur les aides batterie solaire) n'apparaît
pas dans l'onglet Sheets "Leads Formulaire Article", alors qu'il est bien
présent dans BigQuery (`leads_convertis`). Diagnostic (lecture seule,
`scripts-maintenance/analyser_lead_parcours.py` + historique git) : **pas
un bug, un problème de séquencement**. Le commit `dea97ad` (22/10 14:35:32
UTC) a ajouté le code du relais Sheets dans `cme-tracking-conversion.php`
avec la constante `CME_APPS_SCRIPT_LEADS_INLINE_URL` encore **vide** ; la
vraie URL n'a été câblée que par le commit `0d7496f` (22/10 15:17:46 UTC),
soit **38 minutes après** la soumission de Lionel à 14:39:56. Même en
supposant un déploiement cPanel quasi instantané après le premier commit,
le relais Sheets ne pouvait physiquement pas fonctionner pour cette
soumission précise — ses coordonnées (prénom, téléphone, email, code
postal, article) restent donc **uniquement dans BigQuery**, pas dans le
Sheet de suivi quotidien. Confirmé par ailleurs via le parcours GA4 : 1
session, 2 pages vues, 0% de rebond sur l'article ce jour-là — cohérent
avec une vraie conversion, pas un artefact de test.

**Pas d'action corrective nécessaire sur le code** (le relais Sheets est
confirmé fonctionnel depuis, cf. section précédente "RGPD, Google Sheets
et finitions UX") — seulement un rattrapage manuel à faire par l'opérateur
si ce lead doit être suivi comme les autres (l'ajouter à la main dans
l'onglet Sheets, ou travailler directement depuis BigQuery pour celui-ci).
**Fait le 24/10** : l'opérateur a ajouté la ligne de Lionel manuellement
dans l'onglet Sheets, et a supprimé la ligne de test `QA-TEST-...` ajoutée
par la QA du tunnel (section suivante) — incident clos.

**QA complète du tunnel de conversion effectuée le 24/10** (lecture seule,
`scripts-maintenance/qa_tunnel_conversion_complet.py`, exécuté via le pont
GitHub Actions) : relais central WordPress → Cloud Run → BigQuery toujours
sain (confirmé deux fois le même jour), accès anonyme Cloud Run toujours
actif (pas de régression IAM type 19/10). **Limite documentée** : les URLs
Apps Script des anciens simulateurs `comparateur-energie` et
`simulateur-aides` sont stockées en `wp_options` (configurées via
l'admin WordPress), pas dans le repo — non testables depuis ce sandbox ni
depuis le runner GitHub Actions. Seul `simulateur-solaire` a son URL GAS
en dur dans le code (`simulateur-solaire.php` ligne 124), donc testable.
Noté au passage : `simulateur-solaire.php` envoie son `log-clic` en
`fetch()` cross-origin côté client directement vers Cloud Run, avec un
`.catch(function(){})` qui avale silencieusement tout échec (même famille
de fragilité que le bug cross-origin corrigé le 19/10 pour le tracking du
formulaire de contact/téléphone, mais jamais appliquée à cet ancien
simulateur) — à surveiller si une amélioration de ce simulateur est
demandée un jour, hors scope de cette session.

## Bouton téléphone du header — 4ᵉ emplacement natif WordPress découvert (25/10/2026)

Demande opérateur : réduire la taille du bouton téléphone affiché en
header (visible au scroll). Diagnostic (lecture seule, via le pont GitHub
Actions — `scripts-maintenance/inspecter_bouton_telephone_header.py` puis
`inspecter_css_btn_cta.py`) : ce bouton **n'est géré par aucun fichier de
ce repo**. C'est un **4ᵉ emplacement natif WordPress** à ajouter à la liste
des "TROIS emplacements CTA" documentée plus haut — en réalité il y en a
au moins quatre, celui-ci vit dans une zone de widget `header-widget`
(`<aside id="block-58" class="widget inner-padding widget_block">`),
structurellement identique au widget du footer déjà documenté
(édité à la main dans wp-admin → Apparence → Widgets ou l'éditeur de site
si FSE) :
```html
<a href="tel:+33189713648" class="btn-cta" style="font-size: 20px;">📞 01 89 71 36 48</a>
```
**Piège confirmé** : `.btn-cta` est une classe de **thème générique/partagée**
(`padding:15px 10px;font-size:16px;...`, trouvée dans la feuille de style
LiteSpeed minifiée) — exactement le piège déjà documenté dans "Vérifier un
changement live depuis Cloud Shell" (une classe CSS partagée peut avoir
plusieurs occurrences sur une page/le site). D'où le choix de ne **jamais**
toucher `.btn-cta` globalement.

**Solution retenue** : un nouveau mu-plugin dédié,
`wordpress-mu-plugins/cme-header-tel-style.php`, injecte un `<style>` dans
`wp_head` scopé strictement à `.header-widget .btn-cta` (jamais `.btn-cta`
seul) — `font-size:14px!important` (depuis 20px inline) et
`padding:8px 10px!important` (depuis 15px 10px), le `!important` étant
nécessaire pour surpasser le `style=""` inline existant sur l'élément.
Valeurs ajustables en une seule ligne si le rendu visuel ne convient pas
(ce sandbox n'a pas d'accès navigateur au site live pour prévisualiser).

**Même contrainte de déploiement que les autres mu-plugins** : non
versionné automatiquement sur le serveur — `cloudshell download`, upload
cPanel dans `/wp-content/mu-plugins/`, purge des 2 caches LiteSpeed,
vérifier avec `?t=$RANDOM`.

## Tracking de conversion (chantier oct. 2026, suite du chantier CTA)

Depuis la migration des CTA vers `/contactez-un-expert/`, plus aucun systeme
ne journalisait la conversion (ni soumission de formulaire, ni clic sur le
numero de telephone du header) -- confirme par `leads_convertis` au point
mort depuis aout 2026 et par la colonne `conversions` de GA4 (synchronisee
dans `01_raw.ga4_pages`) a zero partout, sur toute la periode. Voir le
document "CME — Diagnostic trafic & conversion" (doc Claude, oct. 2026) pour
le detail complet du diagnostic.

**`wordpress-mu-plugins/cme-tracking-conversion.php`** (nouveau, distinct de
`cme-cta-progressifs.php` -- portee differente : tracking site entier, pas
insertion de CTA limitee aux articles) journalise deux evenements :
- Soumission reussie du formulaire de contact (WPForms, formulaire #472 sur
  `/contactez-un-expert/`) -- ecoute `wpformsAjaxSubmitSuccess` (jQuery),
  avec un repli par `MutationObserver` sur l'apparition du message de
  confirmation, au cas ou l'evenement jQuery venait a changer.
- Clic sur n'importe quel lien `tel:` du site (delegation sur `document`,
  couvre le numero du header partout ou il apparait).

Chaque evenement pousse un `dataLayer.push(...)` (`generate_lead` /
`click_to_call` -- **a marquer manuellement comme Key Event dans
l'interface GA4**, Admin → Evenements, Claude Code n'a pas acces a cette
configuration) ET journalise cote serveur via `POST /api/log-lead` vers
`https://cme-tracking-api-217943559750.europe-west1.run.app` (meme table
`leads_convertis` que les 3 anciens simulateurs, `tool` = `contact-expert-formulaire`
ou `appel-telephone`), pour un suivi independant de la configuration GA4.

**Meme contrainte de deploiement que `cme-cta-progressifs.php`** : fichier
non versionne automatiquement sur le serveur. Apres toute modification,
l'operateur doit : `cloudshell download` le fichier, renommer l'ancien en
`.bak` horodate en cPanel, uploader le nouveau dans `/wp-content/mu-plugins/`,
purger les deux caches LiteSpeed (cPanel + wp-admin), verifier avec
`?t=$RANDOM`.

Verifie le 19/10 : les 3 anciens simulateurs sont toujours des pages live
(HTTP 200). **Correction d'une premiere verification erronee du meme
jour** : leur tracking (`log-lead`/`log-clic`, meme service Cloud Run
`cme-tracking-api` que le nouveau mu-plugin) n'etait PAS fonctionnel --
voir l'incident IAM ci-dessous, qui touchait les 4 outils simultanement
(3 simulateurs + nouveau tracking formulaire/tel), pas seulement un volume
naturellement bas du aux CTA deplaces.

### Incident reel (19/10/2026) : politique IAM vide sur `cme-tracking-api`

Le nouveau mu-plugin de tracking (formulaire + tel:) montrait `0` ligne en
base malgre des evenements GA4 reels (`generate_lead`/`click_to_call`
visibles et marquables comme Key Event). Diagnostic en 4 etapes (voir
`scripts-maintenance/diagnostiquer_relais_tracking.py`, utilise comme
outil reutilisable de debogage reseau via le pont GitHub Actions) :
1. Le JS envoyait en cross-origin (`sendBeacon` + `Content-Type:
   application/json`) directement vers Cloud Run -- echoue silencieusement
   (preflight CORS que `sendBeacon` ne gere pas de maniere fiable).
   **Corrige** par un relais same-origin WordPress
   (`/wp-json/cme/v1/log-lead`, voir `cme-tracking-conversion.php`) qui
   republie cote serveur (`wp_remote_post`) vers Cloud Run.
2. Toujours `0` ligne apres ce correctif -- le relais WordPress
   repondait `200 OK`, mais `wp_remote_post` echouait en silence
   (`blocking => false` avalait l'erreur). Passe en bloquant + stockage du
   resultat dans un transient, lisible via un endpoint de debug temporaire
   (`/wp-json/cme/v1/log-lead-debug`).
3. Cet endpoint a revele un `403 Forbidden` (page Google classique
   "Your client does not have permission..."), reproduit aussi en appelant
   Cloud Run **directement depuis un runner GitHub Actions** (IP totalement
   differente du cPanel) -- donc pas un blocage reseau specifique a
   l'hebergement, mais une restriction globale sur le service.
4. `gcloud run services get-iam-policy cme-tracking-api
   --region=europe-west1` a montre une politique **completement vide**
   (aucun `bindings`) -- le service exigeait une authentification que
   personne n'avait. Corrige avec :
   ```bash
   gcloud run services add-iam-policy-binding cme-tracking-api \
     --region=europe-west1 --project=seo-data-hub-cme \
     --member="allUsers" --role="roles/run.invoker"
   ```
   (`--ingress=all` avait aussi ete applique par precaution avant ce
   dernier test, mais la valeur etait deja `all` -- ce n'etait pas la
   cause). Confirme fonctionnel de bout en bout apres coup (requete directe
   -> relais WordPress -> Cloud Run -> ligne visible dans
   `leads_convertis`).

**Lecon** : si ce service Cloud Run est un jour redeploye
(`gcloud run deploy`) sans script d'infra-as-code figeant l'IAM, verifier
que `allUsers` / `roles/run.invoker` est toujours present -- un redeploiement
simple peut reinitialiser la politique IAM a vide selon la methode utilisee.

## Cache — deux couches distinctes à purger

LiteSpeed Cache existe à **deux niveaux séparés**, purger l'un ne purge pas
l'autre :
1. Le gestionnaire LiteSpeed Cache de **cPanel** (niveau serveur).
2. Le plugin **LiteSpeed Cache dans wp-admin** (Tableau de bord → LiteSpeed
   Cache → Toolbox → Purge All).

Une mise à jour de contenu via l'API REST WordPress ne vide pas forcément le
cache de page automatiquement. Après toute correction de contenu en masse
(script `--apply`) ou déploiement du mu-plugin, purger les deux, puis
vérifier avec un paramètre anti-cache (`?t=$RANDOM`) sur une page réelle.

## Vérifier un changement live depuis Cloud Shell

Pattern utilisé tout au long du chantier CTA, à réutiliser :
```bash
# Contenu brut stocké (contourne le cache, lit direct la base via l'API) :
curl -s "https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts/{ID}?context=edit" | python3 -c "import json,sys; print(json.load(sys.stdin)['content']['raw'])"

# Rendu public (peut être en cache, c'est ce que voit un visiteur) :
curl -s "https://www.comprendre-mon-energie.fr/{slug}/?t=$RANDOM" | grep -oE '.{0,120}MOTIF.{0,120}'
```
**Piège** : si la page entière est une seule ligne (HTML minifié), `sed`
par numéro de ligne échoue (ou pire, produit un numéro négatif que `sed`
interprète comme une option). Utiliser Python pour extraire un contexte en
caractères :
```bash
python3 -c "
content = open('/tmp/page.html', encoding='utf-8', errors='replace').read()
idx = content.find('MOTIF')
print(content[max(0, idx-900):idx+200])
"
```
Si une même recherche générique (ex. une classe CSS comme `btn-cta`) a
plusieurs occurrences sur la page, chercher directement le texte
discriminant (l'URL ou le libellé fautif), pas un identifiant générique
partagé par plusieurs blocs différents.

## Workflows GitHub Actions existants

| Fichier | Déclencheur | Rôle |
|---|---|---|
| `publication-quotidienne.yml` | cron quotidien | Publie les nouveaux articles (pipeline.py) |
| `audit-mensuel.yml` | 4x/mois (1, 8, 15, 22 — 3h UTC, décalé du 1er le 31/10/2026 puis passé de 1x à 4x/mois le 1/11/2026) + `workflow_dispatch` | Audit factuel des valeurs réglementaires citées dans les articles (`auditer_articles_action.py`) — **sans rapport avec les CTA**. Nom affiché dans l'onglet Actions mis à jour ("Audit reglementaire articles (4x/mois)"), fichier toujours nommé `audit-mensuel.yml` (seules des références en commentaire ailleurs dans le repo, aucune dépendance de code sur ce nom de fichier — pas renommé pour éviter une churn inutile) |
| `sync-clarity.yml`, `sync-clarity-par-page.yml` | — | Sync Microsoft Clarity |
| `sync-indicateurs.yml` | — | Rafraîchit les indicateurs réglementaires |
| `sync-leads-app.yml` | — | Sync leads vers l'app |
| `maintenance-a-la-demande.yml` | `workflow_dispatch` uniquement | Exécute un script de `scripts-maintenance/*.py` à la demande (déclenché par Claude Code via `gh workflow run`) ; commite le log d'exécution dans le repo (seul canal lisible par Claude Code, cf. section sandbox ci-dessous) |
| `audit-liens-hebdomadaire.yml` | cron hebdo (lundi 5h UTC) + `workflow_dispatch` | Audit exhaustif des liens (internes + externes) **dans le contenu** des articles (`auditer_liens_internes.py`) — résultat dans les logs du run, rien de commité |
| `audit-cannibalisation-mensuel.yml` | cron mensuel (1er du mois, 5h10 UTC) + `workflow_dispatch` | Détection de cannibalisation de mots-clés par requête GSC (`detecter_cannibalisation_gsc.py`) — résultat dans les logs du run, rien de commité |

Seul `maintenance-a-la-demande.yml` exécute un script de
`scripts-maintenance/` **sur demande explicite** (via `gh workflow run`,
typiquement déclenché par Claude Code) et commite son log, car c'est le
seul canal par lequel Claude Code peut relire le résultat (voir section
sandbox). Les deux audits SEO technique ci-dessus sont au contraire des
**workflows récurrents autonomes** : ils tournent seuls sur leur cron,
sans que Claude Code n'ait besoin de les déclencher ni d'en lire le
résultat — c'est l'opérateur qui consulte l'onglet Actions GitHub
directement. Ne pas les faire aussi commiter un log à chaque run
automatique, ce serait un commit par semaine/mois pour rien.

## SEO technique délégué — liens cassés & cannibalisation (chantier oct. 2026)

Contexte : les outils ORCAAS existants (`auditer_site_technique`,
`agent_orcaas_analyser_chevauchement`, sync indexation/RankMath dans
`pipeline/pipeline.py` + leurs endpoints dans `pipeline/server.py`) sont
**à l'abandon côté usage** et tournent sur Cloud Run (`seo-data-hub-cme`),
ce qui contribue à la facture Cloud. Décision explicite : ne pas les
étendre ni bâtir de nouveau crawler sur cette infrastructure. Les deux
nouveaux scripts ci-dessous tournent sur les runners GitHub Actions
(gratuits dans les limites habituelles), pas sur Cloud Run, et n'écrivent
dans aucune table BigQuery :

- **`scripts-maintenance/auditer_liens_internes.py`** — lit le contenu réel
  de chaque article publié (API REST WordPress), extrait TOUS les liens
  `<a href="...">` (internes et externes), et vérifie chacun en HTTP
  (HEAD, repli en GET si HEAD échoue/est bloqué). Couvre un trou que
  l'audit technique existant ne couvre pas : `auditer_site_technique` ne
  vérifie que les 437 pages **elles-mêmes** (via `wp_url_mapping`), pas les
  liens qu'elles contiennent. Même piège que `fix_cta_liens_retroactif.py`
  appliqué ici : le `href` n'est jamais supposé être le premier attribut
  de la balise `<a>`.
- **`scripts-maintenance/detecter_cannibalisation_gsc.py`** — vraie
  détection de cannibalisation par **requête GSC** (table
  `01_raw.gsc_queries` : colonnes `date, query, page, clics, impressions,
  ctr, position, silo, sous_silo`), distincte de
  `agent_orcaas_analyser_chevauchement` qui ne regarde que l'état
  d'indexation (`'Crawled - currently not indexed'`) entre pages voisines
  par préfixe d'URL. Ici : pour chaque requête réellement tapée par des
  internautes, si plusieurs pages du site se la disputent (au-dessus d'un
  seuil d'impressions anti-bruit), classe le cas en "forte" (la 2ᵉ page
  capte ≥25% des impressions ET se classe en position ≤30 — vraie
  hésitation de Google) ou "faible" (à surveiller). **Lecture seule dans
  les deux cas** — aucune correction automatique, la décision (fusionner,
  rediriger, différencier) reste éditoriale.

Validé en conditions réelles le 19/10 via le pont GitHub Actions : le
script de liens a trouvé un vrai 404 interne et un lien externe cassé sur
un échantillon de seulement 15 articles ; le script de cannibalisation a
remonté 41 requêtes en concurrence interne (dont 5 cas forts), avec un
schéma récurrent révélateur : plusieurs variantes quasi-identiques du même
article publiées à des dates différentes (ex. `changement-fournisseur-gaz`
vs `changement-fournisseur-gaz-0810` vs `...-0810-2`) — à investiguer côté
génération éditoriale (déduplication avant publication), au-delà du simple
constat récurrent.

**Cadence** (question posée explicitement à l'opérateur comme un choix
stratégique, pas un détail de rituel) : hebdomadaire pour les liens (les
liens cassés viennent surtout de pages tierces supprimées/renommées,
lent à apparaître, mais de nouveaux articles sortent chaque jour — une
semaine suffit à détecter sans tourner pour rien) ; mensuelle pour la
cannibalisation, alignée sur le rythme de `audit-mensuel.yml` (les données
GSC ont besoin de plusieurs semaines pour accumuler un signal fiable par
requête — une cadence plus courte ne ferait que répéter les mêmes cas).
Ajustable via `--jours=`/`--impressions-min=` en `workflow_dispatch` sans
toucher au code.

## Contraintes de l'environnement Claude Code (sandbox)

Le sandbox Claude Code (cette session) a un accès réseau restreint via un
proxy agent allowlisté :
- **Le site WordPress live n'est PAS joignable directement** depuis ce
  sandbox (`curl` échoue, `connect_rejected`).
- **`gcloud` n'a aucun compte authentifié** dans ce sandbox — impossible de
  lire Secret Manager ou d'interroger BigQuery directement d'ici.
- **`gh` CLI fonctionne partiellement** : `git clone`/`push`/`pull` et
  `gh workflow list` fonctionnent, mais l'accès aux endpoints de secrets
  GitHub Actions est bloqué par le proxy (403).

Conséquence pratique : toute action touchant le site WordPress live ou GCP
doit être soit (a) exécutée par l'opérateur via Cloud Shell (qui lui a les
accès complets), soit (b) déléguée à un workflow GitHub Actions déclenché
par Claude Code (`gh workflow run`) si un tel workflow existe et expose
l'action nécessaire — l'exécution a alors lieu sur les runners GitHub, qui
ont l'accès réseau complet et les secrets nécessaires.

## Attribution des commits

Chaque session Claude Code reçoit ses propres règles d'attribution de commit
via le contexte runtime (lignes `Co-Authored-By:` / `Claude-Session:` à
ajouter en fin de message de commit). Suivre la consigne donnée dans la
session en cours plutôt que de supposer un format figé ici.

## Apps Script — expiration hebdomadaire de l'API GSC/GA4 (tranché, oct. 2026)

**Diagnostic clos** (investigation du 19/10). Hypothèse initiale (clé de
service account GCP capée à 7 jours par une org policy
`iam.serviceAccountKeyExpiryHours`) **écartée définitivement** : la
politique effective sur le projet est `allowAll` (aucune contrainte), et
les 7 clés existantes du compte `cme-apps-script@seo-data-hub-cme.iam.gserviceaccount.com`
expirent soit en 2028 soit jamais (`9999-12-31`) — aucune ne suit un cycle
hebdomadaire.

**Vraie cause (confirmée par le commentaire de tête de
`apps-scripts/cme-auth.gs`)** : le symptôme "ça expire chaque semaine"
correspondait au comportement classique d'un **refresh token OAuth2
utilisateur** sur des scopes sensibles (Search Console, BigQuery) quand
l'écran de consentement OAuth du projet GCP est en statut "Testing" —
ce type de token expire après 7 jours tant que l'app n'est pas
vérifiée/publiée. Rien à voir avec une clé de compte de service.

**Déjà corrigé** : la migration vers l'authentification par JWT de compte
de service (`getServiceAccountToken_()` dans `cme-auth.gs`, utilisée par
`cme-ga4-to-bq.gs` et `cme-gsc-to-bq.gs`) élimine ce mécanisme — les
comptes de service ne sont pas soumis à l'expiration de refresh token à 7
jours. Confirmé en conditions réelles : `syncQuotidien` et
`syncGA4Quotidien` tournent automatiquement via déclencheur horaire sans
intervention manuelle depuis le 17/10 (3 jours consécutifs au 19/10, après
des lancements manuels de vérification les 14-16/10).

**Suivi recommandé** (léger, pas de nouveau code) :
- Confirmer que ça tient jusqu'à ~26/10 (un cycle hebdo complet depuis le
  14-16/10) sans aucune intervention manuelle.
- Vérifier que les notifications d'échec sont activées sur les
  déclencheurs Apps Script (éditeur → Déclencheurs → icône notification →
  "m'avertir immédiatement" en cas d'échec), pour être alerté par email si
  ça recasse un jour, sans avoir à repasser par l'onglet Exécutions chaque
  semaine.

## Duplication éditoriale — root cause et correctif (chantier oct. 2026)

**Diagnostic** : `scripts-maintenance/analyser_duplication_editoriale.py`
(lecture seule, regroupe les articles publiés par "forme" de titre dans le
même silo/sous-silo + avis editorial IA par cluster) a trouvé **42
clusters** d'articles quasi-dupliqués dans `historique_publications`,
jusqu'à 10 articles dans un seul cluster.

**Root cause confirmée le 20/10** : `verifier_doublons()` existait dans
`pipeline/pipeline.py` mais n'était **appelée nulle part** dans le code
(ni dans ce fichier, ni dans le legacy `pipeline.py` à la racine). Deux
chemins de publication distincts en étaient responsables :

1. **`publier_actualites_reglementaires()`** (Mode Actualité, déclenché
   quotidiennement par `sync-indicateurs.yml`) publiait un article par
   changement d'indicateur réglementaire détecté (`vue_changements_indicateurs`),
   sans aucune vérification. Plusieurs indicateurs distincts ciblant le
   même sous-silo (ex. plusieurs composantes tarifaires électricité qui
   changent le même jour) déclenchaient chacun leur propre article quasi-
   identique — cause confirmée du plus gros cluster (10 articles "Facture
   Électricité : hausse de X% en août 2026", publiés en 3 minutes le
   27/08/2026).
2. **`selectionner_silos_a_traiter()`** (quota quotidien principal, 14
   articles/jour) portait un commentaire explicite *"Pas de filtre
   doublon par titre : la rotation gère la diversité"* — faux en pratique
   si le même mot-clé GSC reste le mieux classé pour un sous-silo d'un
   run à l'autre : rien n'empêchait de le resélectionner. Cause des
   clusters "gaz naturel vs propane" et "chauffe-eau thermodynamique" (6
   articles chacun, étalés sur 1-2 mois) — et, confirmé par un test le
   20/10, **toujours actif cette semaine même** (10 mots-clés quasi-
   identiques publiés sur "Facture Électricité" entre le 16 et le 20/10).

**Corrigé** (commit `9e88067`) :
- `selectionner_silos_a_traiter()` exclut désormais directement dans sa
  requête SQL (`NOT IN`) les mots-clés déjà publiés pour ce même sous-
  silo dans la fenêtre anti-doublon (`config['fenetre_anti_doublon_jours']`,
  90 jours). Match en `LIKE` (pas égalité stricte) car un sous-silo avec
  quota > 1 peut être stocké suffixé (`"Bouteilles (2)"`) par le mécanisme
  d'anti-collision existant.
- `publier_actualites_reglementaires()` appelle maintenant
  `verifier_doublons()` avant de rédiger/publier chaque changement
  détecté, plus un garde en mémoire intra-run (un seul article par
  (sous-silo, jour), même si plusieurs indicateurs distincts changent le
  même jour).
- `verifier_doublons()` elle-même : une erreur BigQuery transitoire
  renvoyait silencieusement "pas de doublon" (`return False`) — dangereux
  maintenant qu'elle est réellement appelée en prod. Passée en fail-safe
  (`return True` sur erreur) : mieux vaut rater une publication ce jour-là
  (retentée au run suivant) que publier un doublon à nettoyer à la main.

Testé en lecture seule sur données réelles via
`scripts-maintenance/tester_fix_doublons.py` (le pont GitHub Actions, pas
Cloud Shell) avant le commit : `verifier_doublons()` renvoie bien `True`
pour un titre déjà publié et `False` pour un titre inédit ; la sous-
requête d'exclusion retrouve bien les publications récentes attendues.
**Validé en conditions réelles le 22/10 — insuffisant, voir section
suivante** : ce correctif couvrait bien les deux root causes identifiées
le 20/10, mais un **troisième** mécanisme de duplication, non détecté à
l'époque, continuait à produire des quasi-doublons quotidiens.

**Étape 2 (séparée, pas automatique)** : les 42 clusters déjà publiés
restent à traiter. `analyser_duplication_editoriale.py` ne fait que
proposer un plan d'enrichissement éditorial par cluster (fusionner avec
plan de contenu enrichi, ou différencier) — **lecture seule**, aucune
fusion ni redirection 301 n'est appliquée automatiquement. Nécessite une
relecture humaine avant toute application sur du contenu déjà publié et
indexé.

## Duplication éditoriale — suite (22/10/2026) : troisième root cause

**Constat** : `scripts-maintenance/verifier_doublons_post_fix.py` (lecture
seule, écrit pour valider le correctif du 20/10 en conditions réelles) a
montré que la duplication continuait **sans interruption** les 20, 21 et
22/10 — notamment des `mot_cle` strictement identiques republiés à moins
de 2 minutes d'intervalle, dans le **même run quotidien**, pour les
sous-silos à quota > 1 (`MaPrimeRénov'` et `Chèque énergie` le 20/10,
`Contrat Électricité` et `Facture Électricité` le 21/10, `Aides
chauffe-eau thermodynamique` les 20 et 21/10). Les deux root causes
corrigées le 20/10 sont restées valides (aucune régression sur ces
mécanismes précis) — c'est un **troisième** mécanisme, non identifié à
l'époque, qui en est responsable.

**Root cause confirmée** : `selectionner_silos_a_traiter()` ajoute un
suffixe anti-collision (`' (2)'`, `' (3)'`...) au nom de sous-silo quand
le quota journalier pour ce sous-silo est > 1 (ex. `"MaPrimeRénov' (2)"`
pour le 2ᵉ article du jour), afin que `generer_tous_briefs()` (qui groupe
par `Silo + Sous-Silo`) ne fusionne pas les deux sujets en un seul brief.
Mais ce suffixe est **toujours retiré avant écriture dans
`historique_publications`** (`rediger_et_publier()`, juste avant l'appel
à `publier_article()`, ligne `sous_silo_val = re.sub(r' \(\d+\)$', '',
sous_silo_val)`) — la table ne contient donc **jamais** de sous-silo
suffixé.

`verifier_et_differencier_sujet()` — la fonction censée comparer chaque
nouveau sujet aux articles déjà publiés sur le même sous-silo avant
rédaction, et demander à l'IA un angle différent en cas de chevauchement
— recevait pourtant ce sous-silo **suffixé** pour toute occurrence ≥ 2,
et filtrait sa requête BigQuery dessus tel quel (`WHERE sous_silo_strategique
= '{sous_silo_safe}'`, égalité stricte sur la valeur suffixée). Résultat :
pour toute occurrence ≥ 2 d'un sous-silo à quota > 1 — exactement le cas
où le risque de doublon est le plus élevé, puisque les deux occurrences
partagent le même contexte concurrentiel scrapé (même requête de niche
via `generate_niche_query`) — la requête ne trouvait **jamais aucune
ligne**, ni l'historique des jours précédents, ni même son propre
« jumeau » occurrence 1 publié quelques secondes plus tôt dans le même
run (déjà présent en base à ce moment, puisque `rediger_et_publier()`
traite les sujets un par un et écrit dans `historique_publications`
avant de passer au suivant). La fonction se comportait donc comme un
no-op silencieux à chaque fois qu'elle aurait dû servir.

**Corrigé** (même commit que ce constat) : `verifier_et_differencier_sujet()`
retire désormais le suffixe (`re.sub(r' \(\d+\)$', '', sous_silo)`) avant
de construire sa requête, exactement comme le fait déjà le filtre SQL de
`selectionner_silos_a_traiter()`. Étendu au passage pour différencier
aussi `mot_cle_principal` (pas seulement `titre_seo`) quand un
chevauchement est détecté — avant, un titre pouvait être reformulé tout
en ciblant exactement le même mot-clé, laissant la duplication SEO
(cannibalisation) intacte même quand le titre semblait différent.

Testé en lecture seule via `scripts-maintenance/tester_fix_differenciation_suffixe.py`
(pont GitHub Actions) : rejoue le cas réel du 20/10 (cluster `"MaPrimeRénov'
vs autres aides"`, 2 articles à 83 secondes d'intervalle) en appelant la
fonction corrigée avec un sous-silo suffixé et un brief quasi-identique à
l'occurrence 1 réelle déjà en base.

**Bug n°4 trouvé par ce test, corrigé dans la foulée** : premier essai en
échec — `400 Syntax error: concatenated string literals must be separated
by whitespace or comments`. Cause : l'échappement des apostrophes dans la
requête utilisait `.replace("'", "''")` (doublement du guillemet) au lieu
du style backslash déjà utilisé ailleurs dans le fichier (ex.
`selectionner_silos_a_traiter`, `.replace("'", "\\'")`). Pour un sous-silo
se terminant par une apostrophe (`"MaPrimeRénov'"`, le seul des 7 ciblés
dans ce cas), ça produit 3 guillemets simples consécutifs juste avant la
fermeture de la chaîne (`...v'''`), que BigQuery interprète comme
l'ouverture d'une chaîne triple-guillemets plutôt qu'une apostrophe
échappée — cassant la requête. Capturé par le `except` fail-open de la
fonction (donc jamais un crash visible), mais silencieusement un no-op
pour `MaPrimeRénov'` **depuis la création de cette fonction**, indépendamment
du bug de suffixe ci-dessus. Corrigé en passant au même style d'échappement
backslash partout dans la fonction.

Re-testé après ce second correctif : détecte maintenant le chevauchement
et renvoie un titre/mot-clé différents (avant les deux correctifs, la
fonction aurait renvoyé le brief rigoureusement inchangé pour ce
sous-silo, faute d'avoir pu exécuter la moindre requête).

**Pas encore validé en conditions réelles** — à vérifier après le
prochain run de `publication-quotidienne.yml` (le lendemain du commit)
qu'aucun sous-silo à quota > 1 ne produit plus de `mot_cle` identique ou
quasi-identique dans le même run.

**Leçon à généraliser** : toute fonction qui compare à
`historique_publications` (ou toute autre table où le suffixe anti-collision
n'est pas stocké) doit débaser le sous-silo reçu avant de filtrer dessus.
Si un futur mécanisme anti-doublon est ajouté ailleurs dans le pipeline et
reçoit potentiellement un sous-silo suffixé, vérifier systématiquement
qu'il fait de même.

## Cartographie des clics et progression du formulaire (26/10/2026)

Suite à la synthèse comportement-visiteurs du 25/10 (voir section précédente
sur l'objectif 1% de conversion), l'opérateur a demandé d'approfondir avec
une vraie **cartographie des zones de clic à l'intérieur des articles** et
le **détail des clics par session/article/silo**, avant d'ajuster quoi que
ce soit (ex. réduction à 150 mots du 1er formulaire).

**Constat préalable, important à garder en tête** : cette donnée n'existait
**nulle part** dans le projet. Vérifié avant d'écrire du code :
- L'API Data Export Clarity qu'on synchronise (`rafraichir_clarity_insights`/
  `rafraichir_clarity_par_page`, `pipeline/pipeline.py`) n'expose qu'un
  ensemble **fixe** de métriques agrégées (Browser/Country/Device/
  EngagementTime/RageClickCount/ScrollDepth/PopularPages/...) — aucune
  métrique de position ou de zone de clic.
- Les vraies heatmaps de clic existent **uniquement dans le tableau de bord
  Clarity** (interface web), pas dans l'API publique — donc invisibles
  depuis ce sandbox/le pont GitHub Actions.
- Aucune table BigQuery existante ne capture de clic généraliste par
  article (`ga4_pages` = agrégat de trafic, pas d'événements ;
  `historique_clics_comparateur` = spécifique aux clics d'offre du
  comparateur, pas généralisable).

**D'où une nouvelle instrumentation**, construite pour répondre à la fois à
la cartographie des clics ET à la question "faut-il fusionner les 2
questions du mini-formulaire / auto-avancer sans bouton" (qui nécessitait
elle aussi une donnée absente : le taux d'abandon entre l'étape nom/prénom
et l'étape téléphone) :

1. **Nouvelle table BigQuery `04_pipeline_seo.interactions_contenu`**
   (partitionnée par jour sur `timestamp`), créée par
   `scripts-maintenance/creer_table_interactions_contenu.py` —
   **script d'ÉCRITURE/DDL, pas lecture seule** (exception documentée),
   idempotent (`exists_ok=True`), à exécuter une seule fois via le pont
   GitHub Actions avant tout déploiement des fichiers ci-dessous. Schéma
   unifié (un seul type_evenement par ligne parmi `clic_contenu` /
   `form_vu` / `form_etape` / `form_abandon`) plutôt que plusieurs tables,
   pour rester simple au volume de données modeste du site.
2. **`tracking-api/server.py`** — nouvelle route `/api/log-interaction`
   (insertion en LOT, pas un événement à la fois) vers cette table.
3. **`wordpress-mu-plugins/cme-tracking-conversion.php`** :
   - nouveau relais same-origin `/wp-json/cme/v1/log-interaction` (même
     principe que `/log-lead`, mais non-bloquant côté `wp_remote_post` —
     volume potentiellement plus élevé qu'une conversion, et aucune
     donnée personnelle dans ce flux, donc impact limité si une requête
     se perd) ;
   - nouveau tracker JS, scope `is_singular('post')` uniquement : capture
     chaque clic sur un lien (interne/externe) ou une image **à
     l'intérieur de `.entry-content`**, avec la section (texte du dernier
     `<h2>`/`<h3>` avant le clic), le texte de l'élément, une position
     approximative (nombre de mots de contenu avant le clic) et le
     scroll% au moment du clic. Bufferisé côté client, envoyé en un seul
     `sendBeacon` au masquage/fermeture de la page (+ filet de sécurité
     toutes les 15s), pour ne pas multiplier les requêtes par visite.
4. **`wordpress-mu-plugins/cme-cta-progressifs.php`** — buffer
   indépendant (pas de dépendance d'ordre de chargement entre les deux
   mu-plugins), trois nouveaux événements par instance de mini-formulaire :
   - `form_etape` à '0' (rendu initial) et à chaque `allerA()` ('1' =
     étape téléphone atteinte, 'termine' = soumis) ;
   - `form_vu` via `IntersectionObserver` (seuil 50%) — distinct de "rendu
     dans le DOM" (le formulaire est inséré par JS dès le chargement,
     avant d'être forcément scrollé en vue) ;
   - `form_abandon`, déclenché une seule fois au masquage de la page si
     le dernier état connu (toutes instances confondues sur la page) est
     "étape téléphone atteinte" (`idx>0`) sans avoir atteint "terminé".

**Déploiement, dans cet ordre précis** (la table doit exister avant que le
relais Cloud Run n'essaie d'y insérer, sinon les lignes sont silencieusement
perdues côté `insert_rows_json`) :
1. Exécuter `creer_table_interactions_contenu.py` via le pont GitHub
   Actions (fait le 26/10, voir log).
2. Redéployer le service Cloud Run `cme-tracking-api` (nouvelle route
   `/api/log-interaction`) — **action opérateur**, pas de CI/CD Cloud Run
   dans ce repo (`gcloud run deploy cme-tracking-api --source tracking-api/
   --region=europe-west1 --project=seo-data-hub-cme`, ou la commande
   habituelle de l'opérateur si différente).
3. Déployer les deux mu-plugins modifiés en cPanel — même contrainte
   habituelle (`cloudshell download`, `.bak` horodaté, upload, purge des 2
   caches LiteSpeed, vérifier avec `?t=$RANDOM`).

**Pas encore exploitable** : la cartographie et les taux d'abandon par
étape nécessitent quelques jours de trafic réel pour être statistiquement
lisibles (~44 sessions/jour en moyenne au 25/10). Prochaine étape une fois
les données accumulées : écrire le script de synthèse lecture-seule sur
`interactions_contenu` (zones les plus cliquées par silo, clics/session par
article, taux d'abandon étape 1→2) et **seulement ensuite** trancher les
ajustements (seuil de mots du 1er formulaire, fusion des 2 champs,
auto-avance sur le téléphone) sur la base de cette donnée plutôt qu'à
l'intuition — c'est la séquence explicitement demandée par l'opérateur.

## Nettoyage du code legacy (26/10/2026)

Les deux points de la section "Divergence connue" ci-dessous ont été
traités à la demande de l'opérateur, une fois le chantier cartographie des
clics lancé et en attente d'accumuler des données :

- **`pipeline.py` racine (~85 Ko, legacy) supprimé** (`git rm`). Confirmé
  sans risque avant suppression : aucune référence dans les workflows
  GitHub Actions (`grep` sur `.github/workflows/`), dernier commit le
  touchant remonte au 18/07/2026 (bien avant le chantier CTA d'octobre),
  et le pipeline réellement exécuté par `publication-quotidienne.yml` est
  `pipeline/pipeline.py`. Les anciens scripts `scripts-maintenance/fix_*.py`
  qui font `open('pipeline.py', ...)` (fix_cta_accents, fix_cta_injection,
  fix_attribution_cta, fix_collision_slug, fix_retry_searchapi,
  fix_5_silos_par_run, fix_elimination_general, fix_planning_7j7,
  fix_logger_bq_parametrized) sont des patchs ponctuels **déjà appliqués
  historiquement** (ils opéraient par chemin relatif depuis la racine du
  repo, à l'époque où c'était encore le fichier actif) — ce ne sont pas des
  dépendances vivantes, laissés tels quels comme trace historique, sans
  lien avec le fichier supprimé.
- **Endpoint `/wp-json/cme/v1/log-lead-debug` retiré** de
  `cme-tracking-conversion.php` (ajouté pendant l'incident IAM du 19/10,
  inutile depuis la résolution de cet incident). Le transient interne
  `cme_tracking_last_error` continue d'être écrit par `cme_relayer_log_lead()`
  (bookkeeping sans impact), seule la route REST publique qui l'exposait a
  été retirée. `php -l` validé, aucune référence orpheline au nom de la
  route restante dans le code (uniquement dans les commentaires
  explicatifs de ce retrait).

**Déploiement** : comme toute modification de `cme-tracking-conversion.php`,
non versionné automatiquement sur le serveur — `cloudshell download`, `.bak`
horodaté, upload cPanel, purge des 2 caches LiteSpeed.

## Cartes titre — chevauchement mot-clé / nom du site (31/10/2026)

Signalé par l'opérateur : sur les images principales générées par
`generer_carte_titre()` (`pipeline/pipeline.py`), le mot-clé (bas gauche) et
"Comprendre Mon Énergie" (bas droit) partageaient la même ligne (`y=70`) —
un mot-clé long chevauchait visuellement le nom du site.

**Corrigé** : le mot-clé a désormais sa propre ligne (`y=130`), au-dessus du
nom du site et en dessous du bloc titre — élimine le chevauchement quelle
que soit sa longueur, plus une troncature défensive à 1 ligne (`textwrap`,
filet de sécurité, les mots-clés réels sont courts). Testé localement avant
déploiement (mot-clé court, mot-clé long, cas limite titre 4 lignes +
mot-clé long) : rendu correct dans les 3 cas, aucune régression sur le cas
court.

## Garde anti-duplication — LIMIT 15 insuffisant à volume élevé (31/10/2026)

Audit demandé par l'opérateur ("vu le volume qu'on va avoir les prochains
mois, il faut être rigoureux sur ce point"), avant toute nouvelle montée en
charge. `verifier_doublons_depuis_22_10.py` (lecture seule, pont GitHub
Actions) a rejoué la validation que le correctif du 22/10 (voir plus haut,
"Duplication éditoriale — suite") n'avait pas encore reçue en conditions
réelles.

**Bug confirmé, actif en prod depuis le 22/10** : `verifier_et_differencier_sujet()`
comparait le sujet proposé aux **15 publications les plus récentes** du
sous-silo (`ORDER BY date_publication DESC LIMIT 15`), sans filtre de date.
Avant la montée en quota du 20-27/10 ce LIMIT couvrait largement les 90
jours de la fenêtre anti-doublon ; depuis, pour la plupart des sous-silos à
quota > 1, les 15 publications les plus récentes ne couvrent plus que
**~7 à 10 jours en moyenne** (mesuré en prod, fonction `MIN(date_publication)
OVER (... ROWS BETWEEN 15 PRECEDING AND 1 PRECEDING)`). Conséquence directe,
mesurée : **17 mots-clés strictement identiques républiés entre le 22/10 et
le 31/10**, à 20-53 jours d'intervalle — à l'intérieur de la fenêtre
anti-doublon officielle de 90 jours, mais hors de ce que la fonction
pouvait voir. Plus le volume quotidien augmente, plus ce trou s'aggrave
mécaniquement (un LIMIT fixe sans filtre de date rétrécit la portée
temporelle réelle à mesure que le débit monte) — exactement le risque que
l'opérateur anticipait.

**Corrigé** (`verifier_et_differencier_sujet()`) en deux temps :
1. **Garde déterministe (SQL, pas de LLM)** : un mot-clé exactement
   identique (normalisé espaces/casse) déjà publié pour ce sous-silo dans
   les 90 jours bloque directement — pas besoin du jugement du LLM pour le
   cas le plus flagrant, celui trouvé en prod. La ligne qui a déclenché ce
   garde-fou est explicitement injectée dans l'échantillon envoyé au LLM
   (même si elle tombe hors du `LIMIT 40` qui suit), et `chevauchement` est
   forcé à `True` indépendamment de la réponse du LLM — en cas de LLM qui
   répondrait "non" malgré un match exact confirmé en SQL, la
   différenciation reste forcée.
2. **Échantillon LLM filtré par date, pas par rang** : la requête qui
   alimente le jugement sémantique (titres formulés différemment mais même
   sujet) est désormais filtrée sur la fenêtre anti-doublon de 90 jours
   (`LIMIT 40` qui ne sert plus qu'à plafonner la taille du prompt, jamais à
   tronquer silencieusement la période couverte).

Testé : smoke-test local (mock BigQuery + mock LLM, cas match exact et cas
"LLM répond non malgré un match exact" — l'override fonctionne) ; puis
rejoué en conditions réelles via `tester_fix_limite_differenciation.py`
(pont GitHub Actions, vrai BigQuery + vrai Anthropic) sur le cas réel qui
avait échappé (post_id=11366, "aides électricité 2026", sous-silo Contrat
Électricité) : le correctif détecte bien le doublon et produit un angle
différencié. **Validé en conditions réelles le 31/10.**

**Hors scope, signalé mais volontairement non corrigé** : le même audit a
trouvé 17 paires d'articles Solaire publiés le même jour, techniquement
différenciés (titres/mots-clés distincts) mais sur un angle très proche
(ex. deux articles "panneaux solaires 400W" le même jour, dimensionnement
vs ROI) — risque de cannibalisation fine, pas un doublon au sens strict.
Décision opérateur : **ne rien changer sur Solaire pour l'instant**, le
silo est en phase de test de requêtes ; réévaluer une fois les premiers
indicateurs GSC/Clarity (trafic organique, conversion) disponibles.

## Audit 404 / "effet d'écrasement" (31/10/2026)

Question opérateur, dans la continuité du point précédent : au vu du volume
de pages à venir (potentiellement des milliers sur un même sujet/mot-clé
avec des angles différents), deux risques identifiés explicitement par
l'opérateur — pages 404, et "effet d'écrasement" (Google qui ne retient
qu'une page parmi plusieurs proches).

**404 — audité, risque nul côté pipeline** : revue de `publier_article()`
et de l'ensemble du repo — aucun script ne supprime jamais un article
WordPress, aucun chemin de code ne PATCH le contenu d'un article existant.
Collision de slug toujours résolue par réutilisation de l'existant (même
titre) ou suffixe de date (titre différent), avec en dernier recours la
déduplication native de WordPress (jamais d'erreur). Seul vecteur de 404
réel sur le site : des liens cassés dans le contenu des articles, déjà
couvert par l'audit hebdomadaire `auditer_liens_internes.py`.

**Effet d'écrasement — infrastructure de mesure déjà présente mais inactive**.
Paysage identifié :
- `detecter_cannibalisation_gsc.py` (GitHub Actions, mensuel, actif) : vraies
  requêtes GSC en concurrence entre pages du site — signal tardif (nécessite
  plusieurs semaines de trafic réel par requête).
- `synchroniser_indexation()` + table `indexation_google` (`pipeline/pipeline.py`,
  `pipeline/server.py`) : interroge l'API URL Inspection de Search Console
  pour obtenir le `coverage_state` réel par URL (incluant les verdicts
  directement liés a l'ecrasement : "Duplicate, Google chose different
  canonical", "Crawled - currently not indexed", etc.) — le signal le plus
  direct et le plus precoce possible, disponible des que Google crawle la
  page, sans attendre du trafic de recherche. **Code present, jamais
  planifie** : declenchement uniquement manuel via un endpoint `server.py`
  (Cloud Run).
- `agent_orcaas_analyser_chevauchement` : compare l'etat d'indexation de
  pages voisines par prefixe d'URL. Marque "a l'abandon" depuis la decision
  d'octobre de ne plus investir sur ce Cloud Run (voir plus haut, "SEO
  technique delegue").

Contrainte identifiee avant toute automatisation : l'API URL Inspection a
un quota quotidien limite, incompatible avec une verification exhaustive a
l'echelle de "milliers de pages".

**Decision operateur (31/10)** : **aucune nouvelle automatisation pour
l'instant** — s'appuyer uniquement sur le suivi mensuel de cannibalisation
GSC deja actif (`detecter_cannibalisation_gsc.py`). Les options ecartees
pour l'instant, a reconsiderer si le besoin se precise : (a) nouveau
workflow GitHub Actions hebdomadaire limite aux articles recents (le plus
coherent avec la decision d'octobre de ne plus investir sur Cloud Run), ou
(b) reactiver/planifier l'outil existant sur Cloud Run. Point a noter si
l'option (a) est reprise un jour : le secret `SA_GTM_PRIVATE_KEY`
(credentials du compte de service Search Console) n'est aujourd'hui cable
que cote Cloud Run, pas dans les secrets GitHub Actions — a propager aux
deux endroits si besoin (meme regle que tout autre secret, voir plus haut).

## Bilan de sante du pipeline + echecs du 24-26/10 (31/10/2026)

Demande explicite de l'operateur ("est-ce que le systeme tourne comme il
faut, aucun probleme d'api ou correctif au niveau du code"), en deux
volets.

**Volet 1 — correction retroactive des articles selon les lois/valeurs
reglementaires** : `audit-mensuel.yml` (cron mensuel, 1er du mois 3h UTC)
→ `pipeline/auditer_articles_action.py` → `auditer_et_corriger_articles()`.
Audite les articles des sous-silos a `pertinence='directe'` (table
`mapping_indicateur_sous_silo`) contre les dernieres valeurs connues
(`indicateurs_reglementaires`), et **corrige automatiquement, sans
validation humaine**, tout article citant une valeur reglementaire
devenue obsolete. Dernier run : 1/10/2026, succes. **Cadence modifiee deux
fois le meme jour, voir section "Audit mensuel — appel a l'API Claude, et
volume" plus bas** : decalee au 5 du mois le 31/10/2026, puis passee le
1/11/2026 a 4 occurrences par mois (1, 8, 15, 22) suite a une nouvelle
demande operateur — le decalage au 5 n'a donc jamais ete utilise en
conditions reelles, remplace avant son premier run. Sans rapport avec le
chantier CTA/formulaire — c'est le seul mecanisme de correction
retroactive de contenu existant dans ce repo.

**Volet 2 — bilan de sante general** : tous les workflows recurrents sont
verts sur leurs derniers runs (`sync-clarity`, `sync-clarity-par-page`,
`sync-leads-app`, `sync-indicateurs`, `audit-liens-hebdomadaire`,
`audit-mensuel`) — SAUF `publication-quotidienne.yml`, en echec 3 jours
consecutifs (24, 25, 26/10), vert sans interruption depuis le 27/10.
`audit-cannibalisation-mensuel.yml` n'a encore jamais tourne — **normal,
pas un bug** : ajoute le 19/10 avec un cron mensuel, son premier
declenchement est prevu le 1/11/2026.

**Diagnostic des 3 echecs** : les logs blob du run GitHub Actions restent
illisibles depuis ce sandbox (limite documentee plus haut) — le point de
panne a ete reconstitue a partir de l'empreinte laissee dans
`historique_publications` (`image_id`, `run_id`) via
`scripts-maintenance/diagnostiquer_echecs_24_26_10.py`,
`diagnostiquer_origine_articles_26_10.py` et
`diagnostiquer_run_ids_24_27_10.py` (les trois lecture seule, pont GitHub
Actions). **Piege rencontre et corrige en cours de route** : le diagnostic
initial sur le 26/10 (10 articles publies ce jour-la avec `image_id`
renseignee) concluait a tort que l'echec etait survenu *apres*
`generer_featured_images()` — en realite, le `run_id` de ces 10 articles
(`solaire_transac_20261026_...`) ne correspond pas au format attendu d'un
run `publication-quotidienne.yml` (`YYYYMMDD_HHMM`, confirme via le 24/10
et le 27/10) : ce sont des articles d'un mecanisme Solaire distinct et
ponctuel, publies a 16h20-16h38 UTC, sans rapport avec le run quotidien du
jour (08h15 UTC, echoue) ni avec `sync-indicateurs.yml` (09h41 UTC) — ce
dernier avait en realite publie **0 article** ce jour-la, exactement
comme le 25/10. Toujours verifier le `run_id` avant d'attribuer des lignes
`historique_publications` a un workflow donne, ne jamais se fier au seul
horodatage/jour.

**Deux causes distinctes identifiees et corrigees** (meme commit) :

1. **24/10 (14/14 articles publies, 0/14 avec image)** : le run s'est
   arrete entre `rediger_et_publier()` (termine avec succes, 14 articles)
   et `generer_featured_images()` (jamais atteinte). Cause confirmee :
   `nettoyer_et_generer_schemas()` (schemas SVG injectes dans le contenu,
   appelee juste entre les deux dans `run_pipeline()`) n'avait **aucun
   try/except** a son site d'appel — alors que le MEME appel est deja
   protege dans `publier_actualites_reglementaires()` (Mode Actualite,
   voir plus haut) : incoherence entre les deux chemins de publication.
   La fonction elle-meme n'a aucune gestion d'erreur interne non plus (ni
   sur ses appels WordPress, ni sur l'extraction/generation des schemas) —
   une seule erreur sur un seul des 14 articles suffisait a faire perdre
   les images, Facebook/Instagram et la notification pour les 14, alors
   que les articles eux-memes etaient deja publies.
2. **25/10 et 26/10 (0 article publie par le run quotidien)** : echec
   survenu avant ou pendant `rediger_et_publier()`. Deux appels reseau non
   proteges dans sa boucle par-brief en sont la cause la plus probable
   (aucun des deux n'a de try/except, ni de verification de status avant
   `.json()`) : `get_ou_creer_categorie()` (appelee dans
   `publier_article()`, hors de son propre bloc try/except) et
   `recuperer_articles_meme_silo()` (repli maillage interne, utilise
   quand `recuperer_articles_meme_sous_silo()` ne trouve rien en
   BigQuery). La boucle par-brief elle-meme n'avait, de plus, aucun
   garde-fou global : une exception non prevue sur UN SEUL brief faisait
   perdre tous les briefs restants du run (jusqu'a 14).

**Corrige** (`pipeline/pipeline.py`) :
- `get_ou_creer_categorie()` : try/except complet (+ `timeout=15` sur les
  2 appels HTTP, + verification de `status_code` avant `.json()`),
  renvoie `None` sur toute erreur au lieu de lever.
- `publier_article()` : filtre les `None` de `categories_ids` avant
  l'envoi a l'API WordPress (categories_ids peut desormais contenir un
  `None` depuis le fix precedent) — un article publie sans categorie
  plutot qu'un plantage de tout le run.
- `recuperer_articles_meme_silo()` : try/except complet (+ `timeout=15`),
  renvoie `[]` sur toute erreur, exactement comme sa fonction sœur
  `recuperer_articles_meme_sous_silo()` l'a toujours fait.
- `rediger_et_publier()` : la boucle par-brief est desormais enveloppee
  dans un try/except (defense en profondeur, pas seulement les 2 points
  deja identifies) — un brief qui echoue, connu aujourd'hui ou par une
  cause future non prevue, ne fait plus perdre les briefs restants du
  run.
- `run_pipeline()` : `nettoyer_et_generer_schemas()` et
  `generer_featured_images()` sont desormais appelees sous try/except —
  memes garde-fous que leurs equivalents deja presents dans Mode
  Actualite. Une erreur dans les schemas/images (cosmetiques, optionnels)
  ne doit jamais empecher Facebook/Instagram et la notification de
  tourner pour des articles deja publies.

**Teste** : `python3 -m py_compile` (OK, seul le `SyntaxWarning`
preexistant non lie, ligne 2006) + test local (mock, aucun appel reseau
reel — `requests` stubbe pour lever systematiquement) confirmant que
`get_ou_creer_categorie()` et `recuperer_articles_meme_silo()` renvoient
bien `None`/`[]` sans lever. **Pas encore valide en conditions reelles** —
a confirmer que `publication-quotidienne.yml` continue de publier ses 14
articles/jour sans regression apres ce commit (le run est deja vert
depuis le 27/10 independamment de ce fix, donc rien d'urgent a
re-verifier avant le prochain run normal).

## Audit — le slug d'un article deja publie peut-il etre modifie ? (31/10/2026)

Question explicite de l'operateur suite au bilan de sante ci-dessus :
est-ce qu'un mecanisme quelconque (en particulier la correction
reglementaire automatique, mais plus largement tout l'ecosysteme) peut
toucher au `slug` d'un article **deja publie** — risque direct de 404 et
de perte du reference GSC/backlinks si une URL change sous le pied d'une
page existante.

**Audite, risque confirme nul, par lecture exhaustive du code** (pas par
test en conditions reelles — pas necessaire, la reponse est structurelle) :
toutes les occurrences de `slug` dans `pipeline/*.py`,
`scripts-maintenance/*.py`, `tracking-api/*.py`, `wordpress-mu-plugins/*.php`
et `apps-scripts/*.gs` ont ete recensees et classees.

- **`appliquer_correction_article()`** (correction reglementaire
  automatique, voir plus haut) : le payload envoye a l'API REST WordPress
  est strictement `json={"content": nouveau_contenu}` — aucune cle
  `slug`. L'API REST WordPress ne modifie que les champs presents dans la
  requete : l'absence de la cle suffit a garantir qu'elle ne peut
  structurellement pas toucher le slug.
- **`publier_article()`** : le seul endroit de tout le repo ou une cle
  `slug` est envoyee dans un payload d'ecriture WordPress pour un ARTICLE
  (en dehors des categories, sans rapport avec l'URL des articles). Mais
  cet envoi se fait uniquement lors d'un `POST` sur la collection
  `/wp-json/wp/v2/posts` (creation d'un NOUVEL article, sans ID dans
  l'URL) — jamais sur un `POST .../posts/{id}` visant un article
  existant. La logique de collision de slug (`verifier_article_wp_existe`
  + suffixe de date) ne fait que choisir le slug du NOUVEL article a
  creer ; elle ne renomme jamais l'existant (reutilise son post_id tel
  quel si meme titre, cree un second article avec un slug different sinon
  — voir plus haut, section "Audit 404").
- **Tous les autres scripts qui PATCHent du contenu existant**
  (`nettoyer_anciens_cta_statiques.py`, `fix_cta_liens_retroactif.py`,
  `patch_logo_entete.py`, etc.) : aucun ne touche `slug`, verifie par
  grep exhaustif — ils n'envoient que `content` ou d'autres champs
  explicitement vises.
- **mu-plugins WordPress** (`cme-cta-progressifs.php`,
  `cme-tracking-conversion.php`, `cme-header-tel-style.php`) : aucune
  occurrence du mot `slug` dans ces fichiers — ils injectent du contenu
  cote client (JS) ou journalisent des evenements, sans jamais toucher a
  l'objet post WordPress lui-meme.
- **Apps Script** (`cme-ga4-to-bq.gs`, `cme-gsc-to-bq.gs`) : le slug n'y
  est que LU (extrait d'une URL GA4/GSC pour classer par silo), jamais
  ecrit nulle part.

**Conclusion** : aucun mecanisme de l'ecosysteme ne peut renommer l'URL
d'un article deja publie. Complement direct a l'audit 404 du 31/10
(section "Audit 404 / effet d'ecrasement" plus haut) — un changement de
slug est la cause la plus classique de 404/perte de backlinks lors d'une
mise a jour de contenu, et ce risque precis est structurellement exclu
ici, pas seulement absent en pratique jusqu'ici.

## Audit mensuel — appel a l'API Claude, et volume (31/10/2026)

Question operateur : les correctifs du 1er du mois sollicitent-ils l'API
Claude ? Les deux workflows du 1er du mois n'ont pas le meme profil :

- **`audit-mensuel.yml`** (`auditer_et_corriger_articles()` →
  `auditer_article()`, voir plus haut) : **oui**, un vrai appel
  `api.anthropic.com/v1/messages` par article candidat (modele
  `claude-haiku-4-5-20251001`, `max_tokens=1500`), pour juger si l'article
  cite une valeur reglementaire perimee et generer le passage corrige.
  Compte verifie en lecture seule le 31/10
  (`scripts-maintenance/compter_candidats_audit_mensuel.py`, pont GitHub
  Actions, meme requete que la fonction reelle) : **441 articles
  candidats** actuellement (sous-silos a `pertinence='directe'` :
  `TRVE_part_variable_TTC` et `TRVE_part_fixe_TTC` 152 chacun,
  `PRVG_moyen_TTC` 75, `ampleur_pourcent_ecretement` 62) → ~441 appels
  Haiku attendus au run du 1/11/2026. Ce nombre est cumulatif et ne peut
  que croitre d'un mois a l'autre (aucun mecanisme ne retire un article de
  ces sous-silos une fois publie) — a garder en tete vu la montee en
  volume de publication anticipee par l'operateur.
- **`audit-cannibalisation-mensuel.yml`** (`detecter_cannibalisation_gsc.py`) :
  **non**, aucun appel a l'API Claude — purement SQL/seuils sur les
  donnees GSC (`01_raw.gsc_queries`), verifie par grep (zero occurrence de
  `anthropic`/`claude` dans ce fichier).

**Decale au 5 du mois (31/10/2026), puis passe a 4x/mois (1/11/2026)** :
`audit-mensuel.yml` a d'abord ete decale du 1er au 5 du mois
(`cron: '0 3 1 * *'` → `'0 3 5 * *'`), puis — demande operateur separee le
lendemain, avant que ce decalage n'ait eu le temps de tourner une seule
fois — passe de 1x/mois a **4x/mois, aux dates fixes 1, 8, 15 et 22**
(`'0 3 1,8,15,22 * *'`, toujours 3h UTC). Titre du workflow renomme
("Audit reglementaire articles (4x/mois)") pour refleter la nouvelle
cadence dans l'onglet Actions GitHub. `audit-cannibalisation-mensuel.yml`
n'est **pas** concerne par ce changement (reste au 1er du mois, 5h10 UTC,
SQL uniquement) — seul l'audit reglementaire (celui qui appelle l'API
Claude) a change de cadence ; son commentaire d'origine, qui affirmait les
deux audits alignes sur le meme jour, a ete corrige en consequence.

**Implication volume/cout directe** : `auditer_et_corriger_articles()`
re-audite l'integralite du pool de candidats a chaque run (aucun filtre
"deja verifie recemment" dans la requete SQL) — passer de 1x a 4x/mois
**quadruple** le nombre d'appels Claude mensuels, de ~441 (voir plus haut)
a environ **~1764/mois** au volume actuel, qui continuera de croitre avec
le nombre d'articles publies (meme logique cumulative que documentee
ci-dessus). Si les valeurs reglementaires sous-jacentes (`indicateurs_reglementaires`)
ne changent pas entre deux runs du meme mois, les runs intermediaires
re-confirment simplement "pas obsolete" pour les memes articles — cout
Haiku reel mais modeste par appel, a surveiller si le volume d'articles
monte fort dans les mois a venir. Avantage en contrepartie : une valeur
reglementaire qui change en cours de mois (ex. le 10) n'attend plus
jusqu'au mois suivant pour etre corrigee dans les articles, repere au plus
tard 5 jours apres (prochaine echeance fixe) au lieu de jusqu'a 30.

## Audit cannibalisation mensuel — premier run reel (01/11/2026)

Premier declenchement de `audit-cannibalisation-mensuel.yml` depuis sa
creation le 19/10 (cron du 1er du mois, 5h10 UTC — execute en realite a
11h46 UTC le 01/11, decalage probablement du a la file d'attente des
workflows programmes GitHub Actions, rien d'anormal). Run reussi
(`detecter_cannibalisation_gsc.py --jours=90 --impressions-min=30`),
resultat lu directement dans le log du run (exceptionnellement accessible
depuis ce sandbox pour ce run precis — le blob storage des logs de run
GitHub Actions reste globalement inaccessible, voir plus haut, section
sandbox) plutot que dans un fichier commite (conforme au design voulu,
lecture seule, rien n'est ecrit dans le repo par ce workflow).

**76 requetes GSC en concurrence interne** sur la fenetre de 90 jours :
**6 en concurrence forte** (action prioritaire), **70 en concurrence
faible** (a surveiller). Historise ici pour servir de base a une future
decision de correction/optimisation (fusion, differenciation ou
redirection 301) — **aucune action n'a ete prise sur ces pages**, la
donnee est juste capturee pour ne pas la perdre avant la prochaine passe
(mensuelle, prochain run prevu le 01/12/2026) :

| Requete | Pages en concurrence | Impressions cumulees | Detail |
|---|---|---|---|
| `prix du gaz bouteille 2026` | 6 | 140 | Silo Gaz/bouteilles — inclut 2 URL quasi-identiques (`...-1015` / `...-1015-2`), meme famille que les clusters de duplication editoriale deja identifies le 20/10 |
| `mon énérgie` (avec faute) | 2 | 54 | Page d'accueil vs `/comparateur-energie-electricite-gaz/` — concurrence sur le nom de marque lui-meme |
| `mon energie` | 2 | 39 | Meme paire que ci-dessus, variante sans faute |
| `quel fournisseur de gaz choisir` | 3 | 37 | Silo Gaz/comparatifs-fournisseurs — une des 3 pages positionnee en moyenne 90e (`meilleur-fournisseur-gaz-2024-comparatif`, probablement obsolete) |
| `prix bouteille de gaz carrefour 2026` | 4 | 35 | Meme cluster bouteilles que la 1ere ligne |
| `fonctionnement compteur electrique` | 5 | 30 | Silo Electricite/compteur — 5 pages quasi-identiques sur le meme sujet |

**Recoupement avec un diagnostic anterieur** : les clusters "bouteilles de
gaz 2026" et "fonctionnement compteur electrique" correspondent exactement
a des familles de quasi-doublons deja reperees le 20/10 par
`analyser_duplication_editoriale.py` (section "Duplication editoriale —
root cause et correctif" plus haut) — ces articles existaient donc deja
comme doublons editoriaux suspectes avant meme d'etre confirmes comme
cannibalisation GSC reelle (vraies requetes, vrai signal de confusion
Google) par ce premier run. Les deux paires "mon energie"/"mon énérgie"
sont un cas distinct, pas lie a la duplication editoriale : concurrence
entre la page d'accueil et une page produit sur le nom de marque, pas un
probleme de contenu redondant.

**Pas d'action automatique** — la decision (fusionner avec redirection
301, differencier l'angle, ou laisser tel quel pour les cas faibles) reste
explicitement editoriale, comme documente a la creation de ce script. Les
70 cas faibles ne sont pas enumeres ici (volume trop important pour ce
fichier) — consultables dans l'onglet Actions GitHub du run
`41303387741` si une revue complete est necessaire avant le prochain run
du 01/12.

## Entonnoir du mini-formulaire — fausse alerte corrigee (01/11/2026)

Suite a la demande explicite de l'operateur de creuser le bug "soumis=0"
signale le 29/10 (section plus haut, "Entonnoir du mini-formulaire par
silo") **en se mefiant explicitement d'une fausse alerte comme celle du
26/10** (run_id mal attribue) : diagnostic point-par-point via
`scripts-maintenance/diagnostiquer_bug_soumis_entonnoir.py`, qui
rapproche chaque lead reel inline (`leads_convertis`,
tool='contact-expert-inline') de ses evenements dans
`interactions_contenu` par `source_post_id` + fenetre de +/-10 minutes
(pas un agregat qui aurait pu masquer un rapprochement errone).

**Resultat : 3 leads inline reels depuis le 28/10**, pas 5 comme le
tableau trafic/conversion agrege (par silo, tous outils confondus,
`appel-telephone` inclus) le suggerait :
- 2 leads du **28/10 10:55-10:56 UTC** (post_id=5274, silo Electricite) :
  **AUCUNE ligne interactions_contenu, pas meme 'form_vu'**.
- 1 lead du **01/11 15:19 UTC** (post_id=3818, silo Aide energetique) :
  **les 4 etapes parfaitement tracees** (vu, etape 0, etape 1, termine),
  horodatages coherents avec la progression reelle du formulaire.

**Verification du sequencement**
(`scripts-maintenance/verifier_sequencement_deploiement_cartographie.py`) :
le **tout premier evenement jamais enregistre** dans
`interactions_contenu`, toutes sources confondues, date du **28/10
15:19:09 UTC** — soit environ **4h20 APRES** les 2 leads sans trace.
**Conclusion : pas un bug de tracking, un probleme de SEQUENCEMENT DE
DEPLOIEMENT** — meme famille exacte que l'incident "Lionel" du 22/10
(section plus haut) : ces 2 leads sont arrives avant que l'operateur
n'ait termine de deployer le code de cartographie des clics en cPanel
ce jour-la (la table + le code existaient depuis le 26/10, mais le
deploiement effectif du mu-plugin `cme-cta-progressifs.php` modifie, qui
necessite un upload manuel cPanel, n'a eu lieu que dans l'apres-midi du
28/10). Un evenement qui precede le deploiement du code qui le produit
ne peut structurellement pas exister — ce n'est pas une perte de donnee.

**Le soumis=0 observe pour Gaz/Electricite/Solaire/Renovation dans
l'entonnoir (29/10 et 01/11) s'explique entierement par ceci**, sans
aucun bug actif : Electricite n'a eu, sur toute la fenetre de test, QUE
ces 2 leads inline (tous deux anterieurs au tracking) — zero soumission
inline APRES le 28/10 15:19 a comparer ; Gaz/Solaire/Renovation n'ont eu
AUCUN lead inline du tout sur la fenetre (leurs conversions mesurees
venaient uniquement de `appel-telephone`, que l'entonnoir ne suit pas —
portee volontairement limitee au mini-formulaire). Le seul lead inline
survenu apres le go-live du tracking (01/11, Aide energetique) est
parfaitement trace de bout en bout.

**A nuancer** : un seul cas confirme "parfaitement trace" depuis le
go-live (echantillon tres faible, structurel vu le faible volume actuel
de soumissions inline) — suffisant pour infirmer un bug actif plutot que
pour garantir une fiabilite a 100% sur un volume plus eleve. A
reconfirmer simplement en laissant le volume s'accumuler, pas en
recreant un nouveau diagnostic. **Section "Point intermediaire" de
`objectif-100-leads-mois.md` (doc projet) corrigee en consequence** —
elle affirmait a tort que le bug persistait au 01/11.

## Cartographie des clics — ajout du TEMPS de lecture (01/11/2026)

Demande operateur, en complement du point precedent : capturer aussi le
**temps ecoule** depuis le chargement de la page (pas seulement la
POSITION en mots/scroll, deja captee depuis le 26/10), pour objectiver la
decision de placement du 1er formulaire (hypothese operateur : "apres
~15 secondes de lecture, soit ~150 mots"). La position seule ne dit rien
de la vitesse de lecture reelle des visiteurs — deux lecteurs peuvent
atteindre 150 mots a des vitesses tres differentes.

**Trois ajouts** :
1. **Nouvelle colonne `temps_ms`** (INT64, nullable) sur
   `interactions_contenu` — `scripts-maintenance/ajouter_colonne_temps_ms_interactions.py`
   (ALTER TABLE ADD COLUMN IF NOT EXISTS, idempotent, meme exception
   ECRITURE/DDL que `creer_table_interactions_contenu.py`). Lignes
   existantes : `temps_ms` reste NULL, aucune migration necessaire.
2. **`cme-tracking-conversion.php`** : `temps_ms` (millisecondes depuis
   le chargement de la page, `Date.now() - DEBUT`) ajoute a chaque
   evenement `clic_contenu` existant.
3. **`cme-cta-progressifs.php`** : `temps_ms` ajoute dans
   `journaliserInteraction()` (un seul point d'ajout, s'applique donc
   automatiquement aux 4 types d'evenements existants : `form_vu`,
   `form_etape` etapes 0/1/termine, `form_abandon`).
4. **Nouveau tracker `lecture_position`** (`cme-tracking-conversion.php`,
   meme IIFE que le tracker de clics existant, meme buffer/relais) :
   jalon tous les ~100 mots lus (pas un intervalle de temps fixe — borne
   le volume d'evenements a la LONGUEUR de l'article, pas a la duree de
   la visite ; un lecteur qui reste sur place sans avancer ne genere pas
   d'evenements supplementaires). Position de lecture approximee par le
   premier element de `.entry-content` dont le bas depasse ~20% de la
   hauteur de viewport (zone de lecture active), puis meme technique
   `motsAvant()` (Range DOM) que pour les clics, appliquee a cet element
   plutot qu'a l'element clique. Avec `temps_ms`, chaque jalon donne
   directement "temps reel mis pour atteindre N mots" — exactement la
   donnee demandee pour trancher le placement du 1er formulaire.

Valide : `php -l` sur les deux mu-plugins + extraction des 3 blocs
`<<<'JS'` (2 dans `cme-tracking-conversion.php`, 1 dans
`cme-cta-progressifs.php`) et `node --check` sur chacun — aucune erreur
de syntaxe.

**Pas encore deploye** : comme toute modification de ces deux fichiers,
non versionne automatiquement sur le serveur. Avant le prochain upload
cPanel : executer d'abord `ajouter_colonne_temps_ms_interactions.py` via
le pont GitHub Actions (la colonne doit exister avant que le relais
Cloud Run n'essaie d'y inserer une valeur, meme ordre de precaution que
pour la creation initiale de `interactions_contenu` le 26/10), puis
deployer les deux mu-plugins (`cloudshell download`, `.bak` horodate,
upload cPanel, purge des 2 caches LiteSpeed, verifier avec `?t=$RANDOM`).
Script de synthese (temps moyen/median pour atteindre chaque jalon de
100 mots, croise avec les clics par jalon) a ecrire une fois le volume
de donnees suffisant — meme sequence que pour `interactions_contenu`
elle-meme le 26/10 (attendre les donnees avant d'ecrire l'analyse).

**Mise a jour** : la colonne `temps_ms` a ete ajoutee avec succes via le
pont GitHub Actions (`ajouter_colonne_temps_ms_interactions.py`, run du
01/11 16:27 UTC) — schema confirme a 14 colonnes. Les deux mu-plugins
restent en attente de deploiement cPanel (voir section suivante, qui les
regroupe avec un second chantier dans le meme lot de deploiement).

## Mini-formulaire "avant d'appeler" (01/11/2026)

Demande explicite de l'operateur, dans la continuite directe du chantier
formulaire de contact progressif : *"est-ce qu'on peut créer un formulaire
avant d'appeler, le même : nom & prénom + numéro de téléphone avant
d'appeler, comme ça l'ajustement au niveau du déploiement se fait une
seule fois"*. Objectif explicite porte par la derniere clause : pas un
deuxieme formulaire construit a part, mais la REUTILISATION du meme
generateur deja en place (`creer()` dans `cme-cta-progressifs.php`), pour
qu'un futur ajustement (styles, champs, validation, RGPD...) n'ait besoin
d'etre code qu'UNE SEULE fois et profite aux deux formulaires.

**Trois precisions demandees explicitement a l'operateur avant
implementation** (question posee car ambigu et couteux a refaire une fois
deploye en prod) :
1. **Perimetre** : articles uniquement (`is_singular('post')`, meme
   perimetre que le formulaire de contact existant) — PAS le numero affiche
   en header/footer (widget WordPress natif sitewide, documente plus haut,
   section "Bouton telephone du header"), qui reste un lien `tel:` direct,
   totalement inchange.
2. **Declenchement de l'appel** : bouton "Appeler maintenant" explicite
   (pas de redirection automatique) — le visiteur garde la main sur le
   moment ou l'appel part reellement. Precision operateur ajoutee dans la
   meme reponse : le numero du header doit rester affiche tel quel, ET les
   leads captures via ce nouveau bouton doivent partir vers le MEME fichier
   Google Sheets que le formulaire de contact, avec l'URL de la page et le
   tracking habituel.
3. **Pas de contournement** : formulaire obligatoire pour commencer (pas de
   lien "appeler sans attendre") — revisable plus tard sur la base de
   donnees reelles si la friction s'avere trop forte.

**Implementation** (`wordpress-mu-plugins/cme-cta-progressifs.php`) :
- `creer(n)` devient `creer(n, variante)` (`'contact'` par defaut,
  `'appel'` pour le nouveau formulaire) — AUCUNE duplication de generateur :
  memes champs (`ETAPES`, inchange : nom/prenom puis telephone), memes
  styles (`injecterStyles()`, `FORMULAIRE_FOND1/2/ACCENT`), meme
  validation, meme navigation clavier/boutons, meme case RGPD obligatoire
  sur la derniere etape de saisie. Seules deux choses changent selon la
  variante :
  - le texte d'accroche et la phrase de reassurance (nouvelle constante
    `TEXTE_APPEL`, texte de reassurance adapte — "un conseiller vous repond
    immediatement au telephone" plutot que "vous recontacte sous 24h") ;
  - la DERNIERE etape : pour `'contact'`, l'ecran "✅ Merci, un expert vous
    recontacte rapidement" inchange ; pour `'appel'`, un ecran "📞 Appeler
    maintenant · 01 89 71 36 48" dont le bouton est un vrai lien
    `tel:+33189713648` (nouvelles constantes `TEL_NUMERO`/`TEL_AFFICHAGE`,
    meme numero que le header) — le lead est envoye (`envoyerLead()`) AU
    MOMENT ou cette etape s'affiche (donc avant le clic sur le bouton
    d'appel lui-meme), pas au clic sur le lien `tel:`.
- `envoyerLead()` prend desormais un 4e parametre `variante` : envoie
  `tool = 'appel-expert-inline'` (nouveau) au lieu de
  `'contact-expert-inline'` quand `variante === 'appel'` — permet de
  distinguer les deux types de conversion dans `leads_convertis` et dans
  les futures analyses. Evenement `dataLayer` distinct aussi
  (`generate_lead_appel_inline`).
- Tracking de progression (`journaliserInteraction`, table
  `interactions_contenu`) : le champ `cible` (jusqu'ici jamais rempli pour
  les evenements `form_vu`/`form_etape`/`form_abandon`) porte desormais la
  variante (`'contact'` ou `'appel'`) — aucune nouvelle colonne necessaire
  (colonne nullable deja existante, reutilisee), permet de separer les deux
  entonnoirs dans une future analyse sans migration de schema.
- **Frequence et position, volontairement DIFFERENTES du formulaire de
  contact** : une seule occurrence du formulaire "appel" par article (pas
  toutes les ~230 mots), ajoutee en toute fin de `.entry-content`
  (`zone.appendChild(...)`, traversee independante de la boucle
  periodique existante — aucun partage d'etat, aucun risque de regression
  sur le mecanisme de contact deja en prod et deja mesure). Choix assume,
  non demande explicitement par l'operateur mais documente ici : placer le
  nouveau CTA "appel" une seule fois, en fin d'article (moment ou
  l'intention d'appel est la plus forte, lecteur qui a lu l'ensemble du
  contenu), plutot que d'alterner les positions periodiques existantes
  entre les deux variantes — pour ne pas modifier le volume/la frequence du
  formulaire de contact actuellement mesure (chantier `temps_ms`/
  `lecture_position` en cours, voir section precedente). Garde-fou
  `MOTS_MIN_CTA_APPEL = 300` : pas de formulaire "appel" sur un article
  trop court (stub).

**Cote serveur** (`wordpress-mu-plugins/cme-tracking-conversion.php`,
`cme_relayer_log_lead()`) : le filtre qui decide quels leads sont relayes
vers Google Sheets (`CME_APPS_SCRIPT_LEADS_INLINE_URL`) accepte desormais
`tool IN ('contact-expert-inline', 'appel-expert-inline')` au lieu du seul
`'contact-expert-inline'` — demande operateur explicite ("le même fichier
sheets"), simple elargissement d'un `===` vers un `in_array()`, aucun
nouveau relais/onglet.

**Cote Google Sheets** (`apps-scripts/cme-formulaire-article-leads.gs`) :
colonne "Type" ajoutee en DERNIERE position de `HEADERS`/`ecrireRow`
(reprend `tool` tel quel) — pour que l'operateur puisse distinguer les deux
types de lead dans l'onglet partage ("Leads Formulaire Article") sans avoir
besoin de croiser avec BigQuery. Ajout en fin de ligne : compatible avec
les lignes deja ecrites, aucune migration necessaire.

**Pas d'action necessaire sur `tracking-api/server.py`** : `/api/log-lead`
republie le payload recu tel quel vers `leads_convertis`
(`tool`/`details`/etc. ne sont pas valides contre une liste figee de
valeurs connues cote serveur) — un nouveau `tool` n'a besoin d'aucun
changement de ce cote.

**Valide** : `php -l` sur les deux mu-plugins + extraction du bloc JS de
`cme-cta-progressifs.php` et des 2 blocs de `cme-tracking-conversion.php`
(`node --check` sur chacun, aucune erreur) + `node --check` sur
`cme-formulaire-article-leads.gs` (copie temporaire en `.js`, meme syntaxe).

**Pas encore deploye** — a regrouper dans le MEME lot de deploiement cPanel
que le chantier `temps_ms`/`lecture_position` (section precedente), les
deux portant sur les memes fichiers (`cme-cta-progressifs.php` et
`cme-tracking-conversion.php`) :
1. Deployer l'Apps Script mis a jour (`cme-formulaire-article-leads.gs`) —
   action operateur, pas d'acces script.google.com depuis ce sandbox (la
   nouvelle colonne "Type" n'a d'effet qu'au prochain redeploiement de ce
   script, pas automatique).
2. `cloudshell download` les deux mu-plugins modifies, `.bak` horodate en
   cPanel, upload dans `/wp-content/mu-plugins/`, purger les deux caches
   LiteSpeed, verifier avec `?t=$RANDOM` sur un article reel (le nouveau
   bloc "appel" doit apparaitre en toute fin de contenu, apres le dernier
   formulaire de contact periodique).
3. Faire un test reel (`?cta60=1` n'est pas necessaire, `MODE='actif'`
   deja) : remplir le nouveau formulaire "appel" jusqu'au bouton "Appeler
   maintenant", verifier la ligne correspondante dans `leads_convertis`
   (`tool='appel-expert-inline'`) et dans l'onglet Sheets (colonne "Type").

**Mise a jour (meme jour, revirement operateur)** : apres un premier test
en prod de ce qui precede, l'operateur a clarifie que ce n'est PAS ce
qu'il voulait en priorite -- il veut que **le bouton tel: du widget
header lui-meme** (visible sur toutes les pages du site, voir plus haut
section "Bouton telephone du header") declenche un formulaire avant
l'appel, pas (seulement) un bloc ajoute en fin d'article. Voir section
suivante.

## Popup "avant d'appeler" sur le bouton du header (01/11/2026)

Demande operateur explicite, en correction directe du point precedent :
*"je veux que en cliquant sur le bouton du header... pour appeler il faut
remplir un formulaire (nom + téléphone + conditions générales) et puis
appeler"*, et confirme que le mecanisme doit s'appliquer **au bouton
lui-meme, sur tout le site** (le widget header apparaissant sur toutes
les pages, pas seulement les articles) -- d'ou une implementation dans
`cme-tracking-conversion.php` (fichier sitewide) plutot que dans
`cme-cta-progressifs.php` (articles uniquement).

**Forme du formulaire, precisee explicitement par l'operateur** : PAS le
pas-a-pas type Typeform du mini-formulaire des articles -- un **popup a
un seul ecran**, les 2 champs (nom/prenom, telephone) affiches l'un en
dessous de l'autre en meme temps, plus la case RGPD, un bouton **"Appeler"**
(pas "Envoyer") qui capture le lead PUIS declenche l'appel reel. Donnees
historisees "au meme moment... cote BigQuery + Sheets" (demande operateur
explicite) -- memes destinations que les autres leads inline.

**Implementation** (`wordpress-mu-plugins/cme-tracking-conversion.php`,
IIFE du tracker sitewide, pas de garde `is_singular`) :
- Nouveau popup HTML/CSS/JS auto-genere au premier besoin
  (`creerPopupAppel()`/`ouvrirPopupAppel()`), overlay plein ecran,
  fermeture par `✕`, clic hors du popup, ou touche Echap -- fermer le
  popup n'est pas un contournement pour appeler directement (aucun lien
  tel: direct n'est propose dans le popup), juste annuler l'action.
- `surClicDocument()` (listener sitewide existant sur tout clic `a[href^="tel:"]`,
  jusqu'ici uniquement pour le tracking anonyme `appel-telephone`) verifie
  desormais en premier si le lien clique est a l'interieur de
  `.header-widget` (scope par ANCETRE, jamais par la classe `.btn-cta`
  seule -- meme piege que celui deja documente pour
  `cme-header-tel-style.php`, classe de theme partagee). Si oui :
  `evt.preventDefault()` + ouverture du popup, et le tracking generique
  `appel-telephone` est sciemment SAUTE pour ce clic precis (le popup
  journalisera un lead qualifie a la place). Tous les autres liens tel:
  du site (dont le bouton "Appeler maintenant" du nouveau bloc de fin
  d'article, qui n'est pas dans `.header-widget`) gardent le comportement
  direct existant, sans aucun changement.
- Validation identique en esprit au mini-formulaire des articles (nom
  >= 2 caracteres, telephone >= 8 chiffres, case RGPD obligatoire) --
  dupliquee ici en version compacte plutot que partagee entre fichiers,
  pour ne pas introduire de dependance d'ordre de chargement entre
  `cme-cta-progressifs.php` et `cme-tracking-conversion.php` (meme
  principe d'independance deja applique aux buffers de tracking des deux
  fichiers).
- Nouveau `tool = 'appel-header-formulaire'` (distinct de
  `appel-telephone`, `contact-expert-inline` et `appel-expert-inline`) --
  ajoute au filtre du relais Sheets (`cme_relayer_log_lead()`, meme onglet
  "Leads Formulaire Article" que les 2 autres formulaires inline, colonne
  "Type" deja prete a l'accueillir sans redeploiement de l'Apps Script).
  Evenement dataLayer distinct aussi (`generate_lead_appel_header`).
- Apres envoi du lead (`sendBeacon`/`fetch`, non bloquant), l'appel reel
  est declenche par `window.location.href = 'tel:+33189713648'` -- memes
  donnees, meme relais `/wp-json/cme/v1/log-lead` que les autres leads
  inline, aucun nouveau code backend necessaire (ni Cloud Run, ni
  `leads_convertis`, qui ne valide pas `tool` contre une liste figee).

**Coexistence assumee, pas demandee explicitement ni explicitement
refusee** : le bloc "avant d'appeler" ajoute en fin de contenu des
articles (section precedente, `cme-cta-progressifs.php`) n'a PAS ete
retire -- l'operateur n'a pas demande sa suppression lors de ce
revirement, seulement l'ajout du popup sur le bouton du header. Les deux
mecanismes coexistent pour l'instant (capturent des moments differents :
intention d'appel immediate n'importe ou sur le site, vs fin de lecture
d'un article) -- a retirer l'un des deux si l'operateur le demande une
fois vus en prod.

**Valide** : `php -l` + extraction des 2 blocs JS (`node --check` sur
chacun), aucune erreur.

**Pas encore deploye** : meme fichier que le chantier precedent
(`cme-tracking-conversion.php`), a regrouper dans le meme lot de
deploiement cPanel (`cloudshell download`, `.bak` horodate, upload, purge
des 2 caches LiteSpeed). Aucun redeploiement Apps Script necessaire cette
fois (colonne "Type" deja generique, pas de nouvelle colonne a ajouter).
Test reel attendu : cliquer sur le numero du header sur une page
quelconque du site (pas seulement un article) -> popup -> remplir ->
"Appeler" -> verifier `tool='appel-header-formulaire'` dans
`leads_convertis` et dans l'onglet Sheets.

**Deploye et confirme fonctionnel par l'operateur le 01/11** (popup
header + formulaire fin d'article). Les 2 leads de test crees pendant la
validation (tel. de test `0695410020`, meme article) ont ete nettoyes le
01/11 via `scripts-maintenance/nettoyer_leads_test_popup_header.py`
(dry-run puis `--apply`, pont GitHub Actions) -- 2 lignes supprimees dans
`leads_convertis`, sans toucher au lead reel du meme jour (Walter Auguste,
autre numero/article). Piege rencontre : le telephone de test est stocke
`0695410020` (zero initial) alors que l'onglet Sheets l'affichait
`695410020` (colonne interpretee comme un nombre, zero de tete supprime a
l'affichage) -- toujours verifier la vraie valeur stockee cote BigQuery
avant de filtrer une suppression sur un telephone copie depuis Sheets.
Nettoyage Sheets lui-meme fait manuellement par l'operateur (meme
precedent que l'incident "Lionel"/"QA-TEST" du 24/10 -- pas d'acces API
Sheets depuis ce sandbox).

## Audit cannibalisation GSC — premier run reel, decision de strategie (02/11/2026)

Suite au premier run reel de `audit-cannibalisation-mensuel.yml` le
01/11 (voir plus haut, section du meme nom) : 6 cas de "forte
concurrence" detailles un par un le 02/11 (URLs exactes recuperees via
`gh run view 41303387741 --log`, exceptionnellement accessible), croises
avec `analyser_duplication_editoriale.py` (20/10) pour distinguer doublon
accidentel vs angles reellement differents :

1. **Cluster "bouteilles de gaz, prix 2026"** (requetes "prix du gaz
   bouteille 2026" + "prix bouteille de gaz carrefour 2026", 6 pages, 0
   clic cumule) : confirme comme doublon de publication accidentel
   (cluster 18 de l'analyse du 20/10 -- meme article publie 2 fois a 71
   secondes d'intervalle le 15/10). Fusion par redirection 301
   quasi-sans-risque si elle devait avoir lieu (rien a perdre, 0 clic
   partout).
2. **"quel fournisseur de gaz choisir"** (3 pages) : 2 pages "2024"
   quasi invisibles (position ~90) vs 1 page qui performe tres bien
   (position 2.9, `gaz-naturel-vs-propane-fournisseur-0905`).
3. **"mon energie"/"mon energie" (requete de marque)** : PAS un doublon
   de contenu -- page d'accueil (mauvaise position, 32-46) vs page outil
   comparateur (meilleure position, ~20). Fusionner serait contre-productif
   (on ne fusionne pas une accueil avec une page outil) -- a laisser tel
   quel.
4. **"fonctionnement compteur electrique"** (5 pages) : PAS detecte comme
   doublon par l'analyse editoriale du 20/10 (titres distincts :
   communicant/lecture/generique/intelligent) -- possible angles reels
   plutot que doublon accidentel, a qualifier avant toute action.

**Decision operateur (02/11)** : **aucune fusion/redirection pour
l'instant**, sur aucun des 4 cas ci-dessus. Strategie retenue, differente
de la fusion proposee initialement : **ameliorer et differencier le
contenu de chaque page cannibalisee** plutot que consolider par
redirection -- une page qui ne peut pas se positionner en premiere
position doit jouer un role de **"page relais/proxy"** vers les pages du
site qui rankent deja sur ce mot-cle (maillage interne), plutot que
disparaitre derriere une 301. Mis en stand-by explicitement **en
attendant une nouvelle session de scraping cible sur ces mots-cles**, dont
le but sera d'identifier comment differencier/enrichir chaque page pour
qu'elle sorte de la cannibalisation sans perdre son URL propre. A ne pas
re-proposer une fusion/redirection sur ces 4 cas sans revalidation
explicite -- la decision a ete prise en toute connaissance des
propositions de fusion initiales.

**Point bloquant identifie en passant, non resolu** : aucun mecanisme de
creation de redirection 301 trouve dans ce repo (`patch_resolution_redirections.py`
ne fait que *suivre* des redirections deja existantes, pas en creer).
RankMath est installe sur le site (vu dans `pipeline/pipeline.py`,
sync indexation/RankMath) et propose generalement un module de
redirections, mais non confirme depuis ce sandbox (pas d'acces au site
live). Sans objet pour l'instant puisqu'aucune fusion n'est prevue, mais a
clarifier avec l'operateur si une fusion redevient d'actualite apres la
prochaine session de scraping.

## Trafic Chine signale dans Clarity — diagnostic (02/11/2026)

Demande operateur : sessions quotidiennes en provenance de Chine visibles
dans Microsoft Clarity, "sans parcours reel" (observation faite par
l'operateur dans le tableau de bord Clarity, replay de session -- pas
accessible depuis ce sandbox, voir plus haut "les vraies heatmaps...
existent uniquement dans le tableau de bord Clarity"). But : comprendre de
quoi il s'agit, pas encore d'action demandee.

**Tentative 1 — API GA4 Data directement (nouveau, pas de precedent dans
le repo)** : `scripts-maintenance/diagnostiquer_trafic_chine_ga4.py` --
`01_raw.ga4_pages` (table synchronisee habituelle) n'a pas de dimension
pays (seulement pagePath + date, voir `apps-scripts/cme-ga4-to-bq.gs`),
donc appel direct a `analyticsdata.googleapis.com` avec le meme compte de
service que le pipeline (`GOOGLE_APPLICATION_CREDENTIALS`, scope
`analytics.readonly`). **Echec en 403 PERMISSION_DENIED sur les 5
rapports** -- ce compte de service (`GCP_SA_KEY_CME`) n'a pas acces a la
propriete GA4 528487832 (contrairement au compte `cme-apps-script@...`
utilise par Apps Script, qui lui y a acces -- ce sont donc deux comptes
de service distincts, ou le meme compte avec des roles IAM differents
selon le produit Google). Si une mesure GA4 granulaire par pays est
necessaire a l'avenir, il faudra soit faire autoriser `GCP_SA_KEY_CME` en
Lecteur sur la propriete GA4 (Admin GA4 -> Gestion des acces), soit
ajouter la dimension pays a `cme-ga4-to-bq.gs` (action operateur,
script.google.com).

**Tentative 2 — donnees Clarity deja synchronisees (repli qui a
fonctionne)** : `scripts-maintenance/diagnostiquer_trafic_chine_clarity.py`
-- lecture de `04_pipeline_seo.clarity_insights_quotidien` (metrique
`Country`, 14 jours). **Confirme un vrai signal, mais de faible volume** :
environ 1 session Chine par jour (0 a 3 selon le jour, present 10 jours
sur 14), contre 50-180 sessions France/jour et des pics ponctuels
Allemagne (jusqu'a 80/jour, cause non investiguee ici, hors perimetre de
la demande). **Pas de panique justifiee par le volume seul** -- 1 session/
jour est un bruit de fond tres courant sur n'importe quel site public
(scanners/scrapers automatiques), pas le signe d'une attaque ciblee ou
d'une volumetrie anormale. Ce qui rend ce cas notable n'est pas le volume
mais la **regularite** (quasi quotidien, contrairement a des pays comme le
Maroc/la Belgique dont la presence s'explique par le lectorat francophone)
combinee a l'observation directe de l'operateur (sessions sans parcours
reel dans le replay Clarity) -- cohérent avec un scraper/scanner automatise
plutot qu'un vrai visiteur curieux, mais **non confirme avec certitude**
depuis ce sandbox : l'API Clarity exportee ne croise pas pays x engagement
(EngagementTime/ScrollDepth/RageClickCount sont des agregats globaux du
site, pas filtrables par pays), donc impossible de prouver "0 engagement
specifiquement pour la Chine" avec les donnees actuellement accessibles
par script -- seule l'observation visuelle de l'operateur dans Clarity
(hors de portee de ce sandbox) le confirme directement.

**Aucune protection/durcissement securite (plugin pare-feu, limitation de
requetes, desactivation de l'enumeration d'utilisateurs REST, etc.) trouve
dans ce repo** -- grep exhaustif sans resultat (`wordfence`, `sucuri`,
`xmlrpc`, `fail2ban`, etc.). Ca ne prouve pas l'absence cote wp-admin (pas
d'acces live depuis ce sandbox), seulement qu'aucun travail de ce type n'a
ete documente/verse dans le repo jusqu'ici.

**Aucune action prise** -- diagnostic uniquement, a la demande explicite
de l'operateur ("je veux juste savoir de quoi il s'agit"). Si une
mitigation est demandee a l'avenir (blocage geographique, regles de
pare-feu), rappeler que bloquer du trafic Chine n'a normalement aucun
impact SEO (Googlebot ne crawle pas depuis des plages IP chinoises), mais
que ce serait une action cote serveur/hebergement (cPanel ou plugin
securite), hors de portee d'execution directe depuis ce sandbox -- comme
pour les autres actions serveur de ce projet.

## Popup header — verification des clics depuis le deploiement (02/11/2026)

Demande operateur : verifier s'il y a eu des clics sur le numero du header
depuis la mise en ligne du popup obligatoire (confirme fonctionnel le
01/11, voir section precedente). `scripts-maintenance/verifier_clics_popup_header.py`
(lecture seule, pont GitHub Actions) : **0 lead reel** via
`tool='appel-header-formulaire'` depuis le 01/11 (hors le lead de test deja
nettoye). Pour contexte, 4 lignes `appel-telephone` (tracking generique
tel:, hors header) sur la meme periode.

**Limite de mesure a garder en tete pour interpreter ce chiffre** : le
popup ne journalise aucun evenement dans `interactions_contenu` (pas de
`popup_vu`/`popup_abandon`, contrairement au mini-formulaire des
articles qui a `form_vu`/`form_abandon`) -- impossible de distinguer
"personne n'a clique sur le bouton du header" de "des visiteurs ont
clique, vu le popup, et abandonne avant de le remplir". Ce 0 ne garantit
donc pas l'absence de friction, seulement l'absence de conversion
complete. A ajouter si l'operateur veut trancher entre ces deux
hypotheses : un evenement `popup_vu` (ouverture) et `popup_abandon`
(fermeture sans soumission) dans `creerPopupAppel()`/`ouvrirPopupAppel()`
(`cme-tracking-conversion.php`), meme table, meme pattern que le
mini-formulaire des articles.

## Audit 404 externe du 02/11/2026 — 7 URLs sans trace dans l'ecosysteme

Operateur fournit un export CSV d'un outil d'audit externe (colonnes
"Page URL with Http 400-499 errors" + "Page depth" -- probablement un
crawler SEO type Screaming Frog/Ahrefs/SEMrush, pas GSC) listant 7 URLs en
404, toutes de profondeur 3 (`/{silo}/{sous-silo}/{slug}/`, le schema de
permalien habituel) : 6 en silo Solaire, 1 en Electricite/Facture.

**Diagnostic exhaustif, resultat inattendu : AUCUNE trace nulle part**,
verifie par 4 scripts lecture seule distincts
(`diagnostiquer_404_audit_0211.py`, `..._suite.py`, `..._liens.py`, pont
GitHub Actions) :
- **404 confirme en live** sur les 7 URLs (requete HTTP directe depuis le
  runner GitHub Actions, acces reseau complet).
- **Aucune ligne** dans `historique_publications` (notre propre log de
  toute publication faite par ce pipeline, jamais purge par aucun script).
- **Aucun post WordPress**, meme en recherchant TOUS les statuts
  (draft/trash/pending/future/private) via l'API authentifiee par slug --
  ces articles n'existent pas, meme a la corbeille.
- **Aucune ligne, meme partielle (LIKE)**, dans `01_raw.gsc_queries` --
  Google n'a jamais vu ces URLs dans les requetes/clics/impressions
  synchronisees.
- **Absentes du sitemap XML live** (7 sous-sitemaps parcourus).
- **Absentes de `02_cleaned.wp_url_mapping`** (dernier snapshot complet
  des URLs publiees, rafraichi par `rafraichir_wp_url_mapping()`).
- **Aucun lien live** trouve ni sur les pages d'archive silo/sous-silo
  concernees (7 pages verifiees), ni sur 13 articles deja publies et
  thematiquement tres proches (meme sous-silo) -- rien sur le site
  n'a ete trouve pointant vers ces 7 URLs.

**Conclusion** : ces 7 URLs ne correspondent a aucun article jamais publie
par ce pipeline ni visible de Google -- l'hypothese la plus probable est
une **source externe au site** (backlink(s) pointant vers des URLs qui
n'ont jamais existe ou ont existe avant la periode couverte par nos
donnees synchronisees, ou decouverte par l'outil d'audit via son propre
historique/index plutot que par crawl du site actuel). **Non verifiable
depuis ce sandbox** : le rapport de backlinks de l'outil d'audit lui-meme,
ou le rapport GSC "Liens" (Search Console UI, hors API synchronisee ici).
A defaut d'une cause structurelle active sur le site, aucune correction de
code n'est necessaire -- seule une redirection 301 (cosmetique, pour
l'experience d'un visiteur qui suivrait ce lien externe perime) a du sens.

**Propositions de cibles de redirection 301** (meilleure page vivante par
proximite thematique + sous-silo, trouvee par recherche WordPress par
mot-cle) :

| URL 404 | Cible 301 proposee | Qualite du match |
|---|---|---|
| `.../systeme-solaire-combine/aides-systeme-solaire-combine-2026/` | `.../systeme-solaire-combine/prix-installation-systeme-solaire-combine-2026/` | Bon -- meme sous-silo, angle budget proche de "aides" |
| `.../batterie-panneaux-solaires/aides-batterie-solaire-2026/` | `.../batterie-panneaux-solaires/batterie-solaire-vs-panneau-seul-roi-2026/` | Bon -- meme sous-silo, meme suffixe -2026 |
| `.../facture-electricite/augmentation-electricite-causes/` | `.../facture-electricite/pic-consommation-electrique-facture-explose/` | Tres bon -- theme quasi identique (hausse facture) |
| `.../panneaux-solaires/maprimerenov-panneaux-solaires-2026/` | `.../panneaux-solaires/panneaux-solaires-400w-prix-rendement-roi-1031-2/` (ou a defaut l'archive `/solaire/panneaux-solaires/`) | Faible -- aucune page vivante ne traite specifiquement MaPrimeRénov pour le solaire, angle le plus proche = prix/ROI |
| `.../chauffe-eau-solaire/aides-chauffe-eau-solaire-2026/` | `.../chauffe-eau-solaire/chauffe-eau-solaire-vs-gaz-roi/` | Bon -- meme sous-silo, angle cout proche de "aides" |
| `.../chauffe-eau-solaire/prix-chauffe-eau-solaire-2026-cout-installation/` | `.../chauffe-eau-solaire/chauffe-eau-solaire-vs-electrique-cout-reel/` | Tres bon -- meme sous-silo, meme angle prix/cout |
| `.../panneaux-solaires/prix-panneaux-solaires-2026-tarifs/` | `.../panneaux-solaires/panneaux-solaires-400w-prix-rendement-roi-1031-2/` | Tres bon -- meme sous-silo, meme angle prix |

**Point bloquant deja identifie le 02/11** (section "Audit cannibalisation
GSC" plus haut) : aucun mecanisme de creation de redirection 301 trouve
dans ce repo -- a clarifier avec l'operateur (RankMath si son module
redirections est actif, plugin "Redirection", ou .htaccess manuel) avant
toute execution. Aucune action prise, proposition uniquement.

**CORRECTIF A LA CONCLUSION CI-DESSUS (meme jour, quelques heures plus
tard)** : l'operateur a explicitement demande de revérifier l'hypothese
"maillage interne genere par nos propres pipelines", jugee *a priori* peu
probable dans le diagnostic initial. **L'hypothese etait juste** -- le
diagnostic initial (`diagnostiquer_404_audit_0211_liens.py`) n'avait
verifie qu'un echantillon choisi a la main (7 pages d'archive + 13
articles "candidats" trouves par recherche de mots-cles), pas l'integralite
du corpus. `scripts-maintenance/verifier_maillage_interne_404_0211.py`
(lecture seule, pont GitHub Actions, scanne le contenu complet des **973**
articles publies, pas un echantillon) trouve **21 liens internes reels**
vers les 7 URLs 404, repartis sur **18 articles vivants distincts**
(correction d'un premier compte errone a 13, recalcule programmatiquement
le 02/11 a partir du log brut plutot qu'a la main) :

| URL 404 | Nb liens trouves | Articles sources (extrait) |
|---|---|---|
| aides-systeme-solaire-combine-2026 | 3 | cout-installation-systeme-solaire-combine, installation-systeme-solaire-combine-etapes-couts, systeme-solaire-combine-temps-retour-investissement |
| aides-batterie-solaire-2026 | 5 | batterie-solaire-prix-installation-roi, batterie-solaire-vs-groupe-electrogene-1028(-2), quelle-capacite-batterie-solaire-choisir-maison, prix-batterie-solaire-installation-cout |
| augmentation-electricite-causes | 1 | comprendre-facture-electricite-decryptage |
| maprimerenov-panneaux-solaires-2026 | 3 | panneaux-solaires-monocristallins-vs-polycristallins-1028, rentabilite-panneaux-solaires-temps-retour-investissement, combien-panneaux-solaires-maison-budget |
| aides-chauffe-eau-solaire-2026 | 5 | chauffe-eau-solaire-vs-electrique-prix-economies, installation-chauffe-eau-solaire-etapes-tarifs/-couts, chauffe-eau-solaire-vs-electrique-economique, chauffe-eau-solaire-rentabilite-economies-par-an |
| prix-chauffe-eau-solaire-2026-cout-installation | 1 | chauffe-eau-solaire-rentabilite-economies-par-an |
| prix-panneaux-solaires-2026-tarifs | 3 | panneaux-solaires-monocristallins-vs-polycristallins-1028-2, rentabilite-panneaux-solaires-temps-retour-investissement, combien-panneaux-solaires-maison-budget |

**Correction de la conclusion precedente** : ce ne sont donc PAS (ou pas
seulement) des backlinks externes perimes -- ce sont de VRAIS liens de
maillage interne, generes par ce pipeline a la publication d'autres
articles, qui pointent vers des slugs qui n'ont jamais existe dans
`historique_publications` ni dans aucun statut WordPress (voir diagnostic
initial). **Mecanisme exact confirme le meme jour par lecture de code**
(voir section suivante, "Root cause confirmee + correctif structurel") :
`rediger_article()` ne fait que DEMANDER au modele, par consigne de
PROMPT, de reprendre les URLs du maillage interne "EXACTEMENT" -- rien en
code ne verifiait que les `<a href>` reellement generes correspondaient a
une URL effectivement fournie. Les deux hypotheses envisagees initialement
(suppression/renommage manuel d'un post reellement existant) sont ecartees
comme explication principale : le vrai mecanisme est une invention du
modele (URL plausible pour le sujet, jamais fournie ni existante), pas la
disparition d'une page qui aurait existe.

**Action corrective recommandee, distincte des 301** : ces 21 liens, dans
18 articles **actuellement en ligne**, sont un probleme UX actif (pas
seulement un vieux backlink externe) -- un vrai visiteur qui clique "pour
aller plus loin" sur ces 18 pages tombe sur un 404 aujourd'hui. A corriger
en remplaçant chacun des 21 liens par le lien de redirection propose
correspondant (meme tableau que ci-dessus), via un script du meme type que
`fix_cta_liens_retroactif.py`/`nettoyer_anciens_cta_statiques.py`
(BeautifulSoup, dry-run par defaut) -- pas encore ecrit, propose a
l'operateur, en attente de son feu vert.

## Root cause confirmee + correctif structurel — liens internes morts (02/11/2026)

Demande operateur explicite ("une solution absolue... plus de production
de lien interne inexistant") suite a la correction ci-dessus (le maillage
interne, pas un backlink externe, est la vraie cause des 7 404 de
l'audit du jour).

**Root cause** : `rediger_article()` (`pipeline/pipeline.py`) passe au
modele une liste `MAILLAGE INTERNE` (titres+URLs reels, construite par
`recuperer_articles_meme_sous_silo()`/`recuperer_articles_meme_silo()`) et
lui demande, par consigne de PROMPT uniquement, de reprendre ces URLs
"EXACTEMENT" (`"NE JAMAIS modifier l'URL fournie"`) — **rien dans le code
ne verifie que les `<a href>` reellement presents dans le contenu genere
correspondent a une URL effectivement fournie**. Le modele peut (et a, de
facon confirmee) produire un lien vers une URL plausible pour le sujet —
meme convention de slug que les vraies pages du site — sans qu'elle n'ait
jamais ete fournie ni n'existe. Les 7 URLs 404 de l'audit en sont
l'illustration directe : aucune ne figure dans `historique_publications`
ni dans `LIENS_PILIERS_SOUS_SILO` (le mecanisme pilier, lui, code en dur
et donc fiable par construction) — seule l'hypothese "invention du modele
a partir du maillage fourni/du pattern du site" explique des URLs
plausibles mais jamais reellement publiees.

**Corrige, les deux chemins de publication** (`pipeline/pipeline.py`) :
nouvelle fonction `valider_et_nettoyer_liens_internes(contenu_html)` (+
helper `_url_interne_est_vivante()`, HEAD puis repli GET si 403/405, meme
convention que `auditer_liens_internes.py`) appelee juste avant
`publier_article()` dans **`rediger_et_publier()`** (run quotidien
principal, apres `inserer_lien_pilier()` — verifie donc aussi le lien
pilier code en dur, pas seulement ceux issus du modele) **et** dans
**`publier_actualites_reglementaires()`** (Mode Actualite, qui appelle
`rediger_article()` avec `articles_silo=None` mais reste exposee au risque
— pas de garantie que le modele n'invente rien sans liste fournie).
Parse avec BeautifulSoup (pas de regex sur HTML imbrique, meme principe
que documente plus haut pour `nettoyer_anciens_cta_statiques.py`), verifie
CHAQUE lien interne (domaine du site, absolu ou relatif) en LIVE contre le
site reel — **peu importe son origine** (maillage fourni, lien pilier,
initiative du modele) — et retire (unwrap, garde le texte de l'ancre) tout
lien qui ne repond pas 200. Volontairement limite aux liens internes (les
externes sont deja couverts par l'audit hebdomadaire). Fail-safe a deux
niveaux : un lien dont la verification echoue (timeout, exception) est
traite comme mort par prudence ; si la fonction echoue entierement
(erreur inattendue), elle renvoie le contenu inchange — ne bloque jamais
la publication, meme philosophie que les autres fonctions de maillage
(`recuperer_articles_meme_silo`, etc.).

**C'est une verification de la realite, pas une liste blanche** : elle ne
suppose rien sur la facon dont un lien mort pourrait apparaitre a l'avenir
(nouvelle fonction de maillage, evolution du prompt, etc.) — tout lien
interne qui ne repond pas 200 au moment de la publication est retire,
point. C'est ce qui en fait une garantie structurelle plutot qu'un patch
ponctuel sur le mecanisme identifie aujourd'hui.

**Teste en local** (mock des requetes HTTP, aucun appel reseau reel) :
lien vivant conserve, lien mort (absolu et relatif) retire avec le texte
de l'ancre preserve, lien externe jamais verifie ni touche, exception
reseau traitee comme mort, repli HEAD→GET sur 403 fonctionnel. `python3 -m
py_compile` OK (seul le `SyntaxWarning` preexistant non lie, ligne 2006).
**Pas encore valide en conditions reelles** — a confirmer au prochain run
de `publication-quotidienne.yml` que la ligne `🧹 X lien(s) interne(s)
mort(s) retire(s)` n'apparait plus (ou n'apparait que pour un vrai
hoquet reseau transitoire), signe que le modele ne produit plus de lien
vers une URL inexistante — ou, si elle apparait, que le nettoyage a bien
fonctionne au lieu de laisser un 404 partir en production.

**Limite assumee** : chaque lien interne ajoute un aller-retour HTTP vers
le site avant publication (quelques secondes, 1-5 liens par article en
pratique) — cout negligeable par rapport a l'appel au modele lui-meme, et
sans commune mesure avec le risque de publier un 404 en masse au volume
anticipe par l'operateur.

## 32 liens morts (pas 21) + redirections 301 : pas automatisable via RankMath (02/11/2026)

**Recomptage precis** : `fix_liens_morts_maillage_0211.py` (dry-run, BeautifulSoup,
compte chaque `<a href>` reellement present plutot qu'une seule fois par
article) trouve **32 liens morts** sur les 18 articles -- plusieurs
articles repetent le meme lien mort a 2-3 endroits du texte (le compte de
21 du diagnostic initial comptait les paires (article, URL 404) distinctes,
pas les occurrences). Script pret, teste en dry-run via le pont GitHub
Actions, en attente du feu vert operateur pour `--apply`.

**RankMath — API REST verifiee par lecture de sa source PUBLIQUE**
(wordpress.org, pas le site live) avant toute tentative reelle :
RankMath EST installe et actif (confirme via `/wp-json/`, namespace
`rankmath/v1`), mais sa seule route REST liee aux redirections
(`/rankmath/v1/updateRedirection`, POST) est **celle du metabox par
article** (`objectID`/`objectType` requis, `$metabox->save_advanced_meta()`)
-- elle attache un redirect a un objet WordPress EXISTANT, pas de source
arbitraire vers destination arbitraire. **Inutilisable pour nos 7 URLs**,
qui n'ont justement aucun post WordPress correspondant.

Le vrai gestionnaire de redirections (Admin → RankMath → Redirections →
Ajouter, source arbitraire → destination arbitraire) n'expose aucune route
REST ni action ajax dans `class-admin.php` -- protege par
`check_ajax_referer('redirection_list_action', 'security')`, un nonce lie
a une session admin cookie, **que l'authentification par Application
Password (utilisee par ce pipeline) ne peut pas fournir**. Confirme par
lecture directe du code source du plugin
(`inspecter_source_rankmath_redirections*.py`,
`inspecter_rankmath_redirections_admin_ajax.py`, pont GitHub Actions,
telechargement de la source publique wordpress.org -- aucun test en
aveugle sur le site live).

**Conclusion** : la creation des 7 redirections 301 n'est pas automatisable
depuis ce sandbox (ni par ce pipeline, ni par Claude Code) avec les moyens
d'authentification actuels. Reste une action manuelle operateur : 7 entrees
dans wp-admin → RankMath → Redirections → Ajouter (source = chemin relatif
de chacune des 7 URLs 404, destination = la cible proposee, meme table que
le diagnostic initial) -- quelques minutes, aucun developpement possible
pour reduire ca davantage sans un acces navigateur authentifie (hors de
portee de ce sandbox aujourd'hui).

## Chantier 404/maillage interne du 02/11/2026 — clos

**301** : les 7 redirections ont ete creees manuellement par l'operateur
dans RankMath (confirme par l'operateur le 02/11) -- aucune verification
cote code possible depuis ce sandbox (pas d'acces au site live), a
confirmer visuellement par l'operateur si besoin (`curl -I` sur chaque
URL 404, doit renvoyer 301 vers la cible plutot que 404).

**32 liens internes morts corriges** (`fix_liens_morts_maillage_0211.py --apply`,
pont GitHub Actions, canari `--limite=3` valide puis reste du lot) :
18/18 articles traites, 32/32 liens corriges, **0 erreur**. Verifie par
un dry-run final post-correction : `0 article(s) traite(s), 0 lien(s)
mort(s) detecte(s)` -- plus aucun des 7 slugs 404 n'est reference dans le
contenu stocke d'aucun article publie.

**Garde-fou structurel deploye dans le pipeline** (voir section
"Root cause confirmee + correctif structurel" plus haut, commit `b5dc8bd`) :
chaque futur lien interne genere par le modele est verifie en live avant
publication, quelle que soit son origine -- empeche une recidive du meme
mecanisme (invention de lien par le modele) pour les prochains articles.
**A confirmer au prochain run de `publication-quotidienne.yml`** que la
ligne `🧹 X lien(s) interne(s) mort(s) retire(s)` n'apparait plus (ou,
si un cas se presente, que le nettoyage fonctionne comme prevu plutot que
de laisser un 404 partir en production).

Chantier entierement clos : root cause identifiee et corrigee de maniere
structurelle, contenu existant assaini, redirections posees cote
operateur.

## Leads du vrai formulaire de contact — double comptage + regroupement Sheets (02/11/2026)

Demande operateur : "on verifie les leads enregistres sur le formulaire
'contactez-un-expert' et on regroupe le tout sur le meme fichier sheets,
la meme feuille d'inline formulaire et bouton headers."

**Verification** (`scripts-maintenance/verifier_leads_formulaire_contact_expert.py`,
lecture seule, pont GitHub Actions) sur `leads_convertis`,
`tool='contact-expert-formulaire'` (le vrai formulaire WPForms #472 sur
`/contactez-un-expert/`, tracking mis en place le 19/10, voir "Tracking
de conversion" plus haut) : **4 lignes sur 60 jours, toutes du jour meme**,
groupees en 2 paires a ~1 seconde d'intervalle — **0/4 avec un champ
prenom/nom/email/telephone/code_postal non vide**.

**Deux problemes distincts confirmes, pas un seul** :

1. **Double comptage reel** (bug) : chaque soumission reelle produisait 2
   lignes, pas 1. L'hypothese du docblock d'origine ("voie 1/2 ne se
   declenchent que pour une confirmation inline, pas une redirection")
   etait fausse — l'evenement jQuery `wpformsAjaxSubmitSuccess` (voie 1)
   se declenche en realite AUSSI pour un formulaire qui redirige vers
   `/demande-confirmee/` (avec un `formId` mal forme, `"[object Object]"`),
   juste AVANT que le navigateur n'effectue la redirection — la garde en
   memoire (`FORMULAIRE_DEJA_TRACKE`) ne pouvait pas l'empecher puisque
   voie 1 (page d'origine) et voie 3 (page de confirmation) sont deux
   chargements de page distincts, donc deux contextes JS distincts, la
   variable memoire etant reinitialisee entre les deux. **Corrige**
   (commit `98dca1c`) par une garde PARTAGEE en `sessionStorage` (survit a
   la navigation), deplacee dans `surSoumissionFormulaire()` — quelle que
   soit la voie qui se declenche en premier, la seconde est desormais
   ignoree. Au passage, simplifie la voie 3 (sa propre garde locale
   `cme_lead_confirme` devient redondante avec la garde partagee, retiree).
2. **Aucun champ capture** (limite structurelle, pas un bug) : contrairement
   aux 3 mini-formulaires inline (qui possedent leurs propres champs et les
   envoient directement), le tracking du vrai formulaire ne faisait que
   DETECTER qu'une soumission avait eu lieu — jamais lire les valeurs
   saisies dans les champs WPForms eux-memes.

**Decision operateur, suite a la clarification demandee** ("on capture ces
5 infos depuis le formulaire contactez un expert : Date & Heure, Prenom,
Telephone, Email, Code Postal") : capturer effectivement ces champs plutot
que se limiter a un compteur vide. **Corrige** (commit `424b765`),
nouvelle fonction `capturerChampsFormulaireContact(form)` :
- Lit les champs au moment du `submit` NATIF (capture phase, sur
  `document`, donc avant que WPForms n'intercepte en AJAX) — c'est le
  seul instant ou le DOM du formulaire est encore disponible pour les
  voies qui restent sur la page d'origine (1 et 2). La voie 3 (page de
  confirmation, apres redirection) n'y a plus acces et repart donc sans
  ces champs, exactement comme avant ce correctif — degradation sans
  casse, jamais pire qu'avant.
- Identification par **CLASSE de champ WPForms**
  (`wpforms-field-phone`/`-email`/`-name`), pas par nom/id d'input : chez
  WPForms, `name`/`id` sont generiques et positionnels
  (`wpforms[fields][N]`), sans rapport avec le type du champ — seule la
  classe du conteneur est un signal fiable, independant de la langue des
  libelles saisis par l'operateur dans le constructeur de formulaire.
  Le champ "Nom" peut etre configure en 1 input (Simple) ou plusieurs
  (First-Last) chez WPForms : les deux cas sont geres (concatenation).
- **Code postal : pas de classe WPForms dediee** (ce n'est pas un type de
  champ natif) — identifie **par elimination** : le premier champ texte
  simple restant une fois nom/tel/email trouves. **HYPOTHESE A CONFIRMER
  PAR UN TEST REEL post-deploiement** (ce sandbox n'a pas acces au DOM
  live du formulaire #472 pour la verifier avant coup) — si le formulaire
  reel contient un champ texte supplementaire inattendu, ou si le champ
  code postal utilise en realite un type "Nombre" plutot que "Texte", a
  ajuster une fois verifie sur une soumission de test reelle.
- Teste localement (DOM mocke en JS, 5 cas : champs simples, nom
  First-Last concatene, champ vide tolere, aucun champ texte restant,
  exception du DOM -> fail-safe sans crash) + `php -l` et `node --check`
  sur l'ensemble du fichier modifie.

**Regroupement Sheets** (meme commit `424b765`) : le filtre de
`cme_relayer_log_lead()` (`wordpress-mu-plugins/cme-tracking-conversion.php`)
inclut desormais `'contact-expert-formulaire'` en plus des 3 outils inline
deja presents (`contact-expert-inline`, `appel-expert-inline`,
`appel-header-formulaire`) — meme onglet "Leads Formulaire Article",
meme colonne generique en derniere position (aucun changement necessaire
cote `apps-scripts/cme-formulaire-article-leads.gs` pour le relais
lui-meme). Ce regroupement n'a de sens QUE depuis le correctif de capture
ci-dessus : avant, ces lignes seraient arrivees dans le Sheet avec
Prenom/Telephone/Email/Code Postal systematiquement vides, melees a des
lignes avec coordonnees reelles.

**Correction de libelle (02/11, suite, meme jour)** : l'operateur a
confirme l'entete REEL de l'onglet live — 9 colonnes dans l'ordre `Date &
Heure, Prenom, Telephone, Email, Code Postal, Silo, Position dans
l'article, URL de l'article, CTA` — la derniere colonne s'appelle **"CTA"**
sur la feuille live, pas "Type" comme le documentait ce fichier et comme
le disait la chaine `HEADERS` de `cme-formulaire-article-leads.gs` depuis
le 01/11. Corrige dans le `.gs` (`'Type'` -> `'CTA'`, + commentaire) pour
que la source retrouve la realite deployee — **sans impact live** :
`getSheet()` ne reecrit l'entete que si la cellule A1 est vide, donc un
redeploiement de ce fichier n'aurait de toute facon jamais ecrase l'entete
"CTA" deja en place. Confirme au passage, suite a la meme clarification
operateur : la page `/contactez-un-expert/` est bien la bonne cible visee
par tout ce chantier, et `Silo`/`Position dans l'article` resteront
legitimement vides pour les lignes `contact-expert-formulaire` (page
autonome, pas un article) — pas une anomalie a corriger.

**Deploiement — piege rencontre et resolu (02-03/11/2026)** : le premier
upload cPanel de ce fichier (commits `98dca1c`/`424b765`) n'a pas pris
effet malgre l'operateur confirmant avoir pousse/deploye — un test reel a
reproduit exactement l'ancien bug (double ligne, champs vides). Diagnostic
par chaine de verification : `curl ".../contactez-un-expert/?t=$RANDOM" |
grep -o "<marqueur unique du nouveau code>"` renvoyait vide, confirmant que
le SERVEUR servait toujours l'ancien fichier. Cause racine : le clone
Cloud Shell de l'operateur etait perime (anterieur au commit du jour) —
`cloudshell download` telechargeait donc fidelement... l'ancienne version.
**Resolu** en repartant d'un clone frais a chaque fois plutot que de
reutiliser un dossier existant :
```bash
rm -rf ~/cme-fresh && git clone https://github.com/cme-seo-pipeline/cme-seo-pipeline ~/cme-fresh
grep -c "<marqueur attendu>" ~/cme-fresh/wordpress-mu-plugins/cme-tracking-conversion.php   # doit matcher le nombre attendu avant de telecharger
cloudshell download ~/cme-fresh/wordpress-mu-plugins/cme-tracking-conversion.php
```
Repris en CLAUDE.md car generalisable a tout futur deploiement de ce
fichier (ou de `cme-cta-progressifs.php`) : si un `curl` de verification
post-deploiement ne montre pas le changement attendu, verifier d'abord
que le clone LOCAL de l'operateur est a jour avant de suspecter le cache
LiteSpeed ou un probleme d'upload — un clone perime produit exactement
les memes symptomes qu'un cache non purge.

**Deuxieme piege, distinct, trouve lors du test reel qui a suivi** : une
fois le bon fichier deploye, le test en navigation privee a montre que le
champ "Telephone" du formulaire live n'utilise PAS le type de champ
WPForms dedie (`wpforms-field-phone`) — c'est un champ texte simple, comme
le code postal. L'ancienne heuristique de `capturerChampsFormulaireContact()`
("par elimination, le 1er champ texte restant = code_postal") prenait donc
le telephone (place avant dans le formulaire) et ecrasait le vrai code
postal, jamais capture. **Corrige** (commit `5b0bcfd`) en classant les
champs texte restants par le CONTENU de leur valeur plutot que par leur
position : un telephone francais a 9-14 chiffres, un code postal en a
exactement 5 — aucune ambiguite pratique. Valide par un test unitaire
local (6 cas) puis en conditions reelles (navigation privee) : telephone
et code postal desormais chacun dans la bonne colonne.

**Validation complete en conditions reelles le 03/11** : l'operateur a
teste tous les formulaires de conversion (contact-expert-formulaire,
contact-expert-inline, appel-expert-inline, appel-header-formulaire) en
navigation privee apres ce second correctif — tous fonctionnels, champs
correctement captures et separes. Les 9 lignes de test generees pendant
cette session de validation (dont les 2 paires du bug de double comptage
pre-fix et la ligne du bug telephone/code_postal pre-fix) ont ete
supprimees de `leads_convertis` via
`scripts-maintenance/nettoyer_leads_test_0211_0302.py` (dry-run puis
`--apply`, cible par timestamp exact, pont GitHub Actions) — nettoyage du
Sheet correspondant fait manuellement par l'operateur (meme precedent que
les incidents "Lionel"/"QA-TEST popup header"). **Chantier entierement
clos.**

## Publication quotidienne — passage de 7j/7 a 5j/7 (11/11/2026)

Demande explicite de l'operateur : le run quotidien de publication ne
doit plus tourner que du lundi au vendredi, plus le week-end. Deux
emplacements distincts, corriges ensemble pour rester coherents :

1. **`.github/workflows/publication-quotidienne.yml`** : cron passe de
   `'0 3 * * *'` (tous les jours) a `'0 3 * * 1-5'` (lundi a vendredi,
   3h00 UTC inchange) — evite de consommer des minutes GitHub Actions
   pour un run qui ne publierait rien le week-end.
2. **`pipeline/pipeline.py`**, `CONFIG["JOURS_PUBLICATION"]` : deja un
   garde-fou existant (fonction `est_jour_publication()`, verifiee au
   tout debut de `run_pipeline()`) — passe de `[0, 1, 2, 3, 4, 5, 6]`
   (7j/7) a `[0, 1, 2, 3, 4]` (lundi-vendredi, convention Python
   `datetime.weekday()` : 0=lundi). Ce mecanisme existait deja avant ce
   changement (vu dans l'historique git,
   `scripts-maintenance/fix_planning_7j7.py`, qui avait fait exactement
   l'inverse a une date anterieure -- passer de Lundi-Vendredi a 7j/7) :
   ce correctif du 11/11 revient donc a une configuration deja connue du
   projet, pas une nouveaute.

**Double securite volontaire** : le cron empeche deja le run de se
declencher le week-end, et `JOURS_PUBLICATION` empecherait aussi la
publication meme si le workflow etait neanmoins declenche manuellement
un samedi/dimanche (`workflow_dispatch` sans `--force`) -- dans ce cas,
`run_pipeline()` affiche juste "⏸️ Pas un jour de publication" et
s'arrete proprement (`return` sans article publie, code de sortie 0, pas
un echec) ; `--force` (parametre `force` du workflow) reste disponible
pour publier malgre tout un jour non prevu si necessaire.

**Aucun autre impact de code** : le quota d'articles par jour ouvert
(`QUOTAS_SOUS_SILO`, 22/jour -- Solaire 5, Aide Energetique 9, Gaz 4,
Electricite 4) n'a pas ete modifie -- ce changement reduit uniquement le
nombre de jours de publication par semaine, pas le volume par run. Si le
volume mensuel total doit rester identique malgre la perte de 2
jours/semaine, une hausse des quotas serait une decision separate, non
demandee ici.

`python3 -m py_compile` valide sur `pipeline.py` apres modification
(seul le `SyntaxWarning` preexistant non lie, ligne 2040).

## Schemas SVG — titres qui depassent leur bloc (11/11/2026)

Signale par l'operateur : dans les images schema generees a l'interieur
des articles (CELLULE 11B, `pipeline/pipeline.py` --
`generer_flowchart_svg`/`generer_technique_svg`/`generer_comparatif_svg`),
les titres depassaient souvent leur petit bloc. Diagnostic demande
explicitement en lecture seule avant toute correction.

**Deux root causes distinctes, cumulatives** :
1. Troncature par **nombre de caracteres** (`texte[:28]`, `[:45]`, etc.)
   comme approximation de "ca rentre dans la boite" -- le nombre de
   caracteres n'est pas proportionnel a la largeur en pixels reellement
   rendue (une ligne de "i" tient bien plus de caracteres qu'une ligne
   de "M" dans la meme largeur).
2. Substitution de police silencieuse sur le runner GitHub Actions : le
   SVG declarait `font-family:Arial,sans-serif`, mais Arial n'est pas
   installee sur `ubuntu-latest` -- cairosvg retombe sur DejaVu Sans,
   mesurablement plus large qu'Arial/Liberation Sans. Confirme en
   rendant les 3 generateurs via le MEME appel que la prod
   (`upload_svg_wordpress()` : `cairosvg.svg2png(dpi=150,
   output_width=680)`) et en mesurant au pixel l'empan reel du texte vs
   la geometrie prevue par le code (`scripts-maintenance/diagnostiquer_overflow_schemas_svg.py`).

**Corrige** (`pipeline.py`, commit `df0c9ae` puis `1bdc241`) :
- Nouvelle fonction `ajuster_texte_svg(texte, taille_px, gras,
  largeur_max_px)` : mesure la largeur REELLE du texte via PIL
  (`ImageFont.truetype(...).getlength()`) avec le vrai fichier TTF
  Liberation Sans, et tronque caractere par caractere (ajoute "…") jusqu'a
  rentrer dans le budget -- remplace TOUTES les troncatures par nombre de
  caracteres dans les 3 generateurs. Marge de securite interne
  configurable (`SVG_MARGE_SECURITE_PX`, 18px apres ajustement, voir
  plus bas).
- `font-family` des 3 SVG passe a `SVG_POLICE_FAMILLE = "'Liberation
  Sans', Arial, sans-serif"` (Liberation Sans est metriquement compatible
  avec Arial, et un test dedie -- voir plus bas -- a confirme que
  cairosvg resout aussi bien "Arial" que "Liberation Sans" vers le meme
  rendu sur ce runner, les deux donnant 193px pour la meme chaine de
  test).
- Largeurs de texte disponibles calculees a partir de la **geometrie
  reelle** du schema (pas devinees) pour `generer_flowchart_svg` et
  `generer_comparatif_svg` ; pour `generer_technique_svg` (schema SANS
  boite reelle, texte flottant autour d'un cercle par design), nouveau
  dict ajustable `LARGEUR_LABEL_TECHNIQUE_PAR_NB = {1: 220, 2: 220, 3:
  170, 4: 140, 5: 130}` (budget de mise en page par nombre de
  composants affiches, pas un calcul geometrique puisqu'il n'y a pas de
  boite a mesurer).

**Piege rencontre et corrige en cours de route : `apt-get install
fonts-liberation` au runtime du workflow n'est PAS fiable**. Premiere
tentative (commit `df0c9ae`) : ajouter une etape `apt-get install
fonts-liberation` dans les 3 workflows qui rendent des schemas
(`maintenance-a-la-demande.yml`, `publication-quotidienne.yml`,
`sync-indicateurs.yml`). Deux executions de verification consecutives
(`diagnostiquer_overflow_schemas_svg.py` via le pont) ont montre des
chiffres de depassement **identiques au octet** a l'etat non corrige,
avec **zero police Liberation** dans `fc-list` -- meme apres avoir
ajoute `&& fc-cache -f` (commit `2141eb1`) en supposant une course de
cache. Un diagnostic dedie
(`scripts-maintenance/diagnostiquer_install_fonts_liberation.py`) a
confirme que l'installation PEUT reussir sur certains runs (vue
reussie une fois) -- **chaque `gh workflow run`/execution de workflow
provisionne une VM ephemere independante, sans aucun etat partage (cache
apt, DNS, miroirs) entre deux executions meme sur le meme commit** :
l'acces reseau aux miroirs apt est intermittent et non reproductible
d'un run a l'autre sur ce type de runner GitHub-hosted.

**Solution retenue** (commit `1bdc241`) : bundler directement les
fichiers TTF de Liberation Sans **dans le repo**
(`pipeline/assets/fonts/LiberationSans-{Regular,Bold}.ttf` + licence
SIL-OFL-1.1, qui autorise explicitement la redistribution) plutot que
de les installer a l'execution :
- `pipeline.py` : `SVG_POLICE_REGULIER_TTF`/`SVG_POLICE_GRAS_TTF`
  pointent vers ces fichiers bundles (chemin relatif a `pipeline.py`
  via `os.path.dirname(os.path.abspath(__file__))`), au lieu des
  chemins systeme `/usr/share/fonts/...`.
- Les 3 workflows : l'etape copie desormais ces fichiers depuis le repo
  (deja present via `actions/checkout`) vers `~/.local/share/fonts/`
  puis lance `fc-cache -f` localement -- **zero appel reseau**, donc
  deterministe a 100% a chaque run, contrairement a `apt-get`.

**Verification en conditions reelles (pont GitHub Actions), en
plusieurs passes** -- la premiere repasse du diagnostic corrige a
montre des depassements qui semblaient persister (jusqu'a 109px sur
certains champs), mais une investigation plus poussee a revele que
c'etaient des **faux positifs du script de diagnostic lui-meme**, pas
du code de production :
1. `scripts-maintenance/diagnostiquer_police_cairosvg.py` (nouveau,
   lecture seule) a confirme que cairosvg rend bien avec Liberation
   Sans une fois bundlee (193px rendu vs 189.5px mesure par PIL pour la
   meme chaine -- ecart negligeable, largement sous la marge de
   securite) -- la police n'etait donc plus en cause pour la suite.
2. `scripts-maintenance/diagnostiquer_troncature_svg.py` (nouveau,
   lecture seule) a confirme, en rendant isolement chaque texte
   REELLEMENT tronque par `ajuster_texte_svg()` dans les 3 vrais
   appels de generateurs, que la troncature elle-meme fonctionne
   correctement (5 cas sur 6 dans le budget, 1 edge-case a 8px --
   d'ou la marge de securite remontee de 10 a 18px, commit `10baa71`).
3. Le depassement encore mesure par
   `diagnostiquer_overflow_schemas_svg.py` provenait de **3 defauts du
   script de diagnostic lui-meme** (corriges, commits `8356425` et
   `46d1e99`) : (a) image ouverte en RGB au lieu de RGBA -- les zones
   transparentes du canevas (schemas qui ne remplissent pas tout le
   fond, le `background:#FAFAFA` en CSS sur la racine `<svg>` n'etant
   pas honore par cairosvg) etaient aplaties en noir et comptees comme
   "contenu" jusqu'au bord du canevas ; (b) fenetres de recherche par
   composant qui se chevauchaient entre composants voisins du schema
   technique (positions espacees de 210px, fenetres de ±140px) --
   le texte du composant d'a cote etait capte par erreur ; (c)
   l'entete de colonne du schema comparatif est un rect colore plein
   (pas une couleur de fond connue), donc "tout pixel non-fond" le
   detectait lui-meme sur toute sa largeur plutot que le texte qu'il
   contient, en plus d'une marge de recherche qui empietait sur la
   colonne voisine (colonnes contigues, sans espace entre elles).

**Resultat final, confirme sur le run `43067280700`** : les 3 schemas
(technique, flowchart, comparatif) rapportent **0px de depassement sur
tous les elements** par rapport a leur geometrie reelle. Chantier clos.

**Configuration ajustable si le rendu reste trop/pas assez serre**
(demande operateur explicite -- "comme d'habitude avec des endpoints") :
`SVG_MARGE_SECURITE_PX` (marge avant troncature, 18px), et
`LARGEUR_LABEL_TECHNIQUE_PAR_NB` (budget de label par nombre de
composants du schema technique), tous deux en haut de la section
CELLULE 11B de `pipeline.py`.

## SearchApi.io — quota mensuel epuise, correction du nombre reel de jours perdus (02-10/11/2026)

Demande operateur initiale : verifier l'etat du run du 12/11. Premier
`gh run list --limit 5` n'avait montre que **3 echecs** (08/11, 09/11,
10/11). **Recompte le meme jour, plus tard, a `--limit 15`** (demande
operateur sur l'impact d'une pause de publication a creuse ce point plus
loin) : en realite **8 jours consecutifs** (03/11 au 10/11 inclus,
0 article publie chacun) ont echoue avec la meme signature, trouvee par
lecture directe du log (`gh run view --log`, exceptionnellement
accessible pour ces runs) : `Erreur pipeline : SearchApi inutilisable
(HTTP 429) : You have used all of the searches for the month.` -- credit
mensuel SearchApi.io (scraping concurrents, avant la boucle de redaction)
tombe a 0, plantant tout le run des le premier appel (exit code 1, aucun
try/except a cette etape, contrairement aux garde-fous du 31/10 qui
couvrent la boucle par-brief mais pas le scraping qui la precede).

**Plus un 9e jour, cause DIFFERENTE** : le 02/11, le run a egalement
echoue (0 article), mais avec une erreur distincte, AVANT meme d'atteindre
le scraping SearchApi -- `❌ 5. Électricité : ❌ Erreur : 400 Client Error:
Bad Request for url: https://api.anthropic.com/v1/messages` suivi de
`❌ Aucun brief généré`. Cause exacte non investiguee (pas demande, run
isole, jamais revu depuis) -- a diagnostiquer si le meme signature
(échec à la génération de brief, 400 sur l'API Anthropic) reapparaissait.

**Au total : 9 jours calendaires sans AUCUN article publie, du 02/11 au
10/11 inclus** (confirme independamment par un ecart de 10 jours entre
deux dates distinctes de `historique_publications` : 01/11 -> 11/11) --
pas 3 jours comme documente dans une premiere passe de ce meme jour.
**Confirme par l'operateur** : credit SearchApi.io epuise, desormais
corrige (plan/credit renouvele) -- run du 11/11 sans la moindre erreur
SearchApi dans son log, run du 12/11 reparti normalement. **Aucun
correctif de code applique** -- pas demande, cause externe (facturation
SearchApi.io) pour les 8 jours SearchApi ; cause de l'echec isole du
02/11 non diagnostiquee, pas un bug confirme du pipeline. A garder en
tete si le run quotidien replante en debut de mois suivant avec la meme
signature SearchApi : verifier le quota SearchApi.io avant de chercher un
bug cote code.

**Impact reel sur le trafic organique, mesure (voir section suivante,
meme jour)** : malgre 9 jours calendaires sans nouvelle publication, le
trafic SITE ENTIER (GSC + GA4) pendant et apres cette fenetre n'a montre
aucun effondrement -- cause par ce que le flux organique vient a plus de
99% des >1000 articles deja publies et deja indexes, pas des publications
de la semaine en cours.

## Page pilier attestation-de-contrat-delectricite — perte de trafic, diagnostic 360 (12/11/2026)

Demande operateur : comprendre pourquoi
`https://www.comprendre-mon-energie.fr/electricite/contrat-electricite/attestation-de-contrat-delectricite/`
(page PILIER du sous-silo "Contrat Électricité", reference dans
`LIENS_PILIERS_SOUS_SILO`, `pipeline.py` -- chaque nouvel article du
sous-silo lui insere un lien en tout debut de contenu via
`inserer_lien_pilier()`) a perdu du trafic. Diagnostic en lecture seule
via le pont GitHub Actions
(`scripts-maintenance/diagnostic_360_attestation_contrat_electricite.py`
puis `..._suite_url_exacte.py`, pour re-interroger GSC/GA4 par URL EXACTE
apres une premiere ambiguite de LIKE) : historique_publications, statut
technique live, tendances GSC/GA4 mensuelles et hebdomadaires,
cannibalisation sur les requetes historiques, indexation Google connue,
scan complet du maillage interne reel.

**Root cause confirmee : DEUX URLs live pour le MEME post_id (2218),
canonicalisees l'une vers l'autre, et le trafic organique + le maillage
interne ont divergé depuis juin/juillet 2026** :
- **URL longue** (`/electricite/contrat-electricite/attestation-de-contrat-delectricite/`,
  permalien categorise normal du site, celle que pointent les 50 articles
  "Contrat Électricité" vivants qui la lient + le constant pilier) :
  **0 ligne GSC depuis le debut de l'historique synchronise** -- Google ne
  l'a jamais indexee independamment. Son propre `<link rel="canonical">`
  live pointe vers l'URL courte (confirme par requete directe HTML depuis
  le runner), donc Google la traite en "Alternate page with proper
  canonical tag" (confirme dans `04_pipeline_seo.indexation_google`,
  post_id=2218) et ne la fait jamais apparaitre dans les resultats de
  recherche.
- **URL courte** (`/attestation-de-contrat-delectricite/`, sans prefixe de
  categorie) : c'est elle que Google indexe reellement ("Submitted and
  indexed", meme post_id) et qui porte **100% des impressions/clics GSC**
  en continu jusqu'au 09/11/2026 -- mais elle ne recoit plus AUCUNE
  session GA4 depuis juin 2026 (sessions GA4 : avril=1, mai=25, juin=11,
  puis 0 tous les mois suivants), alors que l'URL longue en recoit depuis
  (juin=6, juillet=22, ..., novembre=19) -- la bascule du trafic REEL
  (visites, maillage interne) vers l'URL longue s'est faite a ce moment-la,
  sans que le canonical ne suive.

**Consequence directe, c'est la perte de trafic constatee** : depuis cette
bascule, l'URL que Google classe reellement (la courte) ne recoit plus
aucun lien interne ni aucune visite -- elle "coasse" sur son autorite
residuelle sans plus etre renforcee -- tandis que l'URL activement lieee
par les 50 articles + le mecanisme pilier (la longue) n'apparaitra jamais
dans Google tant que son canonical pointe ailleurs. Chute nette observee
sur l'URL courte (donc sur TOUT le trafic organique reel de cette page) :
impressions GSC 1748 en juillet 2026 -> 208-413/mois depuis (-75% a -88%),
clics organiques quasi nuls (0-4/mois) sur toute la periode malgre une
position moyenne qui s'ameliore legerement (13.3 -> 11.1) -- coherent avec
une page privee de renforcement (ni lien interne frais, ni signal
d'engagement) plutot qu'une perte de classement actif. **Cannibalisation
interne ecartee** : aucune autre page du site n'approche son classement
sur ses 8 requetes historiques principales (le seul concurrent partiel,
`/electricite/facture-electricite/justificatif-de-domicile/`, reste
positionne 50+ sur les memes requetes).

**Hors de portee de ce sandbox** : confirmer cote wp-admin/RankMath
pourquoi les deux URLs repondent 200 sans redirection 301 automatique
entre elles (WordPress redirige normalement une URL non-canonique vers la
permalien courante via `redirect_canonical()` -- absence de redirection
ici suggere une configuration RankMath/cache qui le desactive pour ce
post, pas verifiable sans acces au site live) et pourquoi le canonical de
l'URL longue (la vraie, la lieee) pointe vers l'URL courte (l'ancienne)
plutot que l'inverse.

**Action recommandee, pas encore faite (decision operateur)** : dans
wp-admin/RankMath pour ce post (id 2218), (a) corriger le canonical pour
qu'il se pointe lui-meme sur l'URL longue (celle deja lieee par tout le
maillage interne et coherente avec le permalien `{silo}/{sous-silo}/{slug}/`
utilise partout ailleurs sur le site), et (b) ajouter une redirection 301
de l'URL courte vers l'URL longue pour consolider l'autorite/l'historique
Google sur l'URL qui sera desormais la seule active. Aucune action prise
depuis ce sandbox -- diagnostic uniquement, meme limite deja documentee
pour les redirections 301 (section "32 liens morts... pas automatisable
via RankMath" plus haut : pas d'acces API/ajax authentifie depuis ce
pipeline pour creer une redirection).

**Note (12/11/2026)** : l'operateur indique que le correctif cote
RankMath (canonical) est deja fait depuis le 11 juin -- non reverifie
depuis ce sandbox apres cette indication (le dernier check live direct,
fait juste avant cette remarque, montrait encore le canonical de l'URL
longue pointant vers l'URL courte). A reverifier avec un nouveau
`curl -s ".../attestation-de-contrat-delectricite/" | grep canonical`
si ce dossier redevient d'actualite, plutot que de supposer l'un ou
l'autre etat.

## Schemas SVG — bug distinct trouve en verifiant le correctif du 11/11 sur la prod (12/11/2026)

Demande operateur : le correctif des titres de schemas qui depassaient
leur bloc (section "Schemas SVG — titres qui depassent leur bloc"
plus haut, 11/11) a-t-il ete confirme en conditions reelles ?

**Le correctif du 11/11 est confirme applique sur de vrais articles
publies le 12/11** : `scripts-maintenance/verifier_schemas_svg_production_1211.py`
(lecture seule, pont GitHub Actions) a recupere 3 vrais schemas (un de
chaque type : technique, flowchart, comparatif) parmi les 21 articles
publies le jour meme, en lisant le contenu BRUT stocke via l'API REST
(`?context=edit`) plutot que la page live -- **piege rencontre** : la
page live reste souvent servie depuis le cache LiteSpeed d'AVANT
l'injection des schemas (qui a lieu apres la publication initiale), donc
un premier essai scrapant la page publique n'a rien trouve a tort (0 image)
malgre des injections confirmees reussies dans le log de
`publication-quotidienne.yml` -- toujours lire le contenu stocke
(`context=edit`) pour ce genre de verification, jamais la page rendue.
**Second piege** : le nom de fichier des schemas (`{silo}_{index}_{type}.png`,
voir `nettoyer_et_generer_schemas()`) ne contient ni `post_id` ni slug
d'article -- avec plusieurs articles du meme silo publies le meme jour,
WordPress renomme les collisions avec un suffixe `-N` (`..._comparatif-1.png`,
`..._flowchart-8.png`...) qu'un filtre par nom de fichier exact doit
tolerer. Les 3 images recuperees et inspectees visuellement (base64 dans
le log texte, decode cote sandbox) : titres corrects sur les 3 types.

**Correction a cette premiere lecture (voir section suivante, meme
jour)** : l'operateur a repere, sur l'image "technique" envoyee suite a
cette verification, que la ligne de description continuait bel et bien
a depasser son cercle -- le "aucun depassement" ci-dessus etait une
lecture visuelle rapide, pas une mesure au pixel ; une fois mesure
precisement, l'ecart etait reel (3-6px). Toujours mesurer au pixel
avant d'affirmer qu'un rendu est correct, plutot que se fier a une
inspection visuelle a l'oeil sur une image envoyee en apercu.

**Bug DISTINCT trouve en creusant pourquoi certains des 21 articles
n'avaient aucun schema** : le run du 12/11 a plante au 8e article
("Chèque énergie : tableau comparatif...", H2 "Points clés à retenir",
type comparatif) avec `integer division or modulo by zero` --
`generer_comparatif_svg()` (`pipeline.py`) divise `(680-160) // nb_items`
sans garde, et le LLM avait renvoye un JSON valide mais `"items": []`.
Comme `nettoyer_et_generer_schemas()` n'a qu'un seul try/except GLOBAL
autour de toute la boucle (meme garde-fou que celui pose le 31/10 pour
`rediger_et_publier()`), ce seul plantage a fait perdre les schemas des
**13 articles restants** du jour (articles 9 a 21), pas seulement celui
qui a plante -- exactement le meme risque de "panne en cascade" deja
identifie et corrige ailleurs dans le pipeline.

**Corrige** (meme session, commit `415405d`), deux garde-fous
complementaires (meme philosophie que le correctif structurel des liens
morts du 02/11 -- ne pas supposer comment le cas degenere pourrait se
reproduire a l'avenir) :
- `generer_comparatif_svg()` : le diviseur ne peut plus etre nul
  (`max(nb_items, 1)`) -- la fonction elle-meme ne plante plus jamais sur
  des items vides, quel que soit l'appelant futur.
- `nettoyer_et_generer_schemas()` : si `items` est vide, le H2 est ignore
  (`continue`) plutot que de publier un tableau comparatif degenere sans
  colonnes.

Teste en local (mock BigQuery/requests/bs4/cairosvg, aucun appel reseau) :
le cas qui plantait (`items=[]`) renvoie desormais un SVG valide ; cas
normal non regresse. `python3 -m py_compile` OK. **Pas encore valide en
conditions reelles** -- a confirmer au prochain run de
`publication-quotidienne.yml` que la ligne `⚠️ Erreur schemas SVG :` (ou
le plus specifique `⚠️ Comparatif sans items, schema ignore`) n'apparait
plus comme cause d'interruption globale, et que les articles suivant un
cas degenere recoivent bien leurs schemas normalement.

## Schema technique SVG — cercles qui ne contenaient pas le texte, malgre le correctif du 11/11 (12/11/2026)

Suite directe de la section precedente : l'operateur a repere sur
l'image "technique" envoyee ("Installer une bouteille de gaz") que la
ligne de description sortait toujours de son cercle, malgre le
correctif du 11/11 (troncature par largeur reelle + police bundlee).

**Mesure au pixel sur l'image reelle en prod** (fenetre de scan serree
autour de chaque cercle pour eviter la contamination par les composants
voisins, heuristique `min(r,g,b)<200 ou saturation>60` pour distinguer
texte/trait du fond tres pale a 8% d'opacite) : depassement reel de 3 a
6px de chaque cote sur la ligne "desc" uniquement (pas "nom", pas
l'icone) -- confirme que le signalement de l'operateur etait fonde.

**Root cause, distincte du bug du 11/11** : `generer_technique_svg()`
n'a structurellement pas de boite reelle pour ce type de schema (texte
flottant CENTRE sur chaque icone, sans `<rect>` pour le contenir). Le
budget de largeur par composant (`LARGEUR_LABEL_TECHNIQUE_PAR_NB`,
jusqu'a 220px pour nb<=2, variable selon le nombre de composants) avait
ete dimensionne pour eviter que le texte d'un composant ne chevauche
celui du composant VOISIN (d'ou un budget plus genereux quand les
composants sont plus espaces) -- pas pour rester a l'INTERIEUR du
cercle qui l'entoure visuellement. Deux contraintes differentes, et
c'est la seconde qui compte pour l'oeil.

**Demande operateur explicite sur la direction du correctif** ("Réduire
et agrandir le cercle, on cherche un équilibre et surtout une solution
durable") : les deux leviers combines plutot qu'un seul **(commit
`a792110`)** :
- Rayon des cercles : 52/44 -> 58/50 (nouvelles constantes
  `SVG_RAYON_CERCLE_TECHNIQUE`/`_INTERIEUR`). Verifie au prealable
  qu'aucune paire de positions (toutes valeurs de `nb`) ne se
  chevaucherait : distance minimale entre deux centres = 130px (cas
  nb=5), donc tout rayon <= 65 restait sans risque -- 58 choisi pour une
  marge confortable (14px).
- Budget de texte : `LARGEUR_LABEL_TECHNIQUE_PAR_NB` uniformise a 120px
  pour tout `nb` (au lieu de 130-220 selon `nb`) -- vise une largeur
  reellement rendue au maximum de 102px (120 - 18px de marge interne
  deja soustraite par `ajuster_texte_svg()`), soit 14px sous le nouveau
  diametre (116px).

**Validation en deux temps**, cairosvg etant indisponible dans ce
sandbox (acces pypi.org bloque malgre sa presence dans la liste
`noProxy` -- `NameResolutionError`, cause exacte non investiguee plus
avant) :
1. **Arithmetique locale** (sans rendu, meme fonctions de mesure que
   `pipeline.py` -- `_mesurer_largeur_texte_svg`/`ajuster_texte_svg`,
   meme police TTF embarquee) sur 5 descriptions realistes, en ajoutant
   par precaution le pire ecart PIL-vs-cairosvg deja mesure en prod le
   11/11 (jusqu'a 8px, voir `SVG_MARGE_SECURITE_PX`) : AVANT (rayon 52,
   budget nb=5=130), les 5 depassent le diametre de 12.5 a 16.7px dans
   le pire des cas -- coherent avec les 3-6px REELS mesures sur l'image
   (le pire-cas theorique majore volontairement l'ecart reel). APRES
   (rayon 58, budget uniforme 120), les memes textes restent tous DANS
   le cercle, marge minimale +6px meme dans le pire des cas.
2. **Rendu cairosvg REEL via le pont GitHub Actions**
   (`scripts-maintenance/verifier_fix_cercles_technique_1211.py`,
   lecture seule) : rend `generer_technique_svg()` (code committe) avec
   5 composants representatifs (memes textes que l'etape 1), mesure au
   pixel le depassement UNIQUEMENT sur les bandes horizontales ou le
   texte "nom"/"desc" est reellement dessine, en comparant a la courbe
   reelle de l'anneau du cercle (rayon + moitie du stroke-width, pas un
   rayon plat). **Piege rencontre et corrige en cours de route** : une
   premiere version du script scannait toute la hauteur du cercle contre
   un rayon PLAT -- l'anneau du cercle lui-meme (stroke-width=2.5, dont
   le bord EXTERIEUR reel est a rayon+1.25px) etait alors compte a tort
   comme un "depassement de texte" sur quasi toute la hauteur du cercle
   (signature reconnaissable : exces quasi UNIFORME de 1-2px sur 20+
   lignes consecutives, alors qu'un vrai depassement de texte aurait des
   bords irreguliers et localises aux seules lignes de texte) -- corrige
   (commit `f6b6a67`) en comparant a la courbe reelle de l'anneau plutot
   qu'a un rayon constant.
   **Resultat final (run `43237900523`, log
   `20261112-143103-...`)** : ligne "desc" -- celle a l'origine du
   signalement operateur -- **0px de depassement sur les 5 composants**.
   Ligne "nom" : ~1px residuel sur les 5 composants, mais ce point
   precis se situe a plus de 20px de l'extremite reelle du texte "nom"
   (`"Bouteille de gaz"` mesure ~76px de large, soit ~38px de chaque
   cote du centre -- le pixel detecte est a la frontiere du cercle, pas
   dans cette zone) : c'est l'anti-aliasing du trait du cercle
   lui-meme (tout trait rendu a un bord adouci sur ~1px), pas du texte --
   imperceptible a l'oeil et present sur n'importe quel cercle trace de
   cette maniere, ancien rayon inclus (jamais mesure aussi finement
   avant ce chantier).

**Conclusion** : le defaut reellement signale par l'operateur (texte
"desc" hors du cercle) est corrige et confirme par un rendu reel du
code production, pas seulement par un calcul theorique. Chantier clos.

## Nouveau sous-silo "Aide isolation" (12/11/2026)

Demande operateur : ajouter la production sur un nouveau sous-silo,
**"Aide isolation"** (silo "3. Aide Énergétique"), a **+2 articles/jour**,
en gardant le volume total quotidien inchange -- finance par **-1 sur
"Chèque énergie"** et **-1 sur "Bouteilles"** (Gaz). Categorie WordPress
**deja creee manuellement par l'operateur** avant ce changement (confirme
par l'operateur, URL
`https://www.comprendre-mon-energie.fr/aide-energetique/aide-isolation/`,
parente "Aide Énergétique") -- aucune creation de categorie necessaire
cote pipeline.

**Deux questions posees a l'operateur avant d'appliquer le changement**
(cout d'une erreur en prod trop eleve pour deviner) :
1. La categorie WordPress existe-t-elle deja ? -- **Confirmee**, creee
   manuellement, meme URL que ci-dessus.
2. Quel angle editorial pour ce nouveau sous-silo -- le meme angle
   transactionnel que "Aide pompe à chaleur"/Solaire (prix/devis, ROI,
   budget, comparatif, lecteur pret a convertir), ou l'angle
   informationnel standard des autres sous-silos Aide Énergétique
   (MaPrimeRénov'/Chèque énergie/Aides chauffe-eau thermodynamique) ?
   -- **Reponse operateur : "Absolument le même angle"** (= angle
   transactionnel, comme Aide pompe à chaleur).

**Nouveau quota `QUOTAS_SOUS_SILO`** (`pipeline/pipeline.py`,
`selectionner_silos_a_traiter()`), total **toujours 22/jour** :

| Silo | Sous-silo | Avant | Après |
|---|---|---|---|
| 1. Gaz | Bouteilles | 3 | **2** |
| 1. Gaz | Facture Gaz | 1 | 1 |
| 5. Électricité | Contrat Électricité | 2 | 2 |
| 5. Électricité | Facture Électricité | 2 | 2 |
| 3. Aide Énergétique | MaPrimeRénov' | 2 | 2 |
| 3. Aide Énergétique | Chèque énergie | 2 | **1** |
| 3. Aide Énergétique | Aides chauffe-eau thermodynamique | 2 | 2 |
| 3. Aide Énergétique | Aide pompe à chaleur | 3 | 3 |
| 3. Aide Énergétique | **Aide isolation** | — | **2 (nouveau)** |
| 4. Solaire | Kit solaire / Panneaux solaires / Batterie panneaux solaires / Système solaire combiné / Chauffe-eau solaire | 1 chacun | 1 chacun (inchange) |

**Implementation** (commit `6310e5b`) :
- `QUOTAS_SOUS_SILO` : ligne "Bouteilles" 3→2, ligne "Chèque énergie"
  2→1, nouvelle ligne `("3. Aide Énergétique", "Aide isolation", 2)`.
  Meme mecanisme de selection dynamique que tous les autres sous-silos du
  quota (GSC en priorite pour le mot-cle, fallback anciennete, aucune
  liste de sujets figee) -- rien de specifique a coder pour la selection
  elle-meme.
- `generer_tous_briefs()` : le branchement qui force
  `ANGLE_TRANSACTIONNEL_GENERIQUE` (jusqu'ici `silo == "4. Solaire"` OU
  sous-silo commencant par "Aide pompe à chaleur") etendu pour couvrir
  aussi `str(sous_silo_name).startswith("Aide isolation")` -- meme
  `.startswith()` (pas egalite stricte) que l'existant, necessaire car un
  sous-silo a quota > 1 arrive ici avec le suffixe anti-collision
  (`" (2)"`) ajoute par `selectionner_silos_a_traiter()`. Le reste du silo
  Aide Énergétique (MaPrimeRénov'/Chèque énergie/Aides chauffe-eau
  thermodynamique) reste explicitement sur l'angle informationnel
  habituel -- inchange.
- Docstring de `selectionner_silos_a_traiter()` mise a jour (meme
  convention que les evolutions precedentes de `QUOTAS_SOUS_SILO`,
  "Aide pompe à chaleur" du 04/11 notamment).

**Validation** : `python3 -m py_compile pipeline/pipeline.py` OK (seul le
`SyntaxWarning` preexistant non lie, ligne ~2081) + verification
programmatique que le total reste exactement 22 et que les 3 lignes
modifiees ont les valeurs attendues. **Pas encore valide en conditions
reelles** -- prend effet automatiquement au prochain run de
`publication-quotidienne.yml` (modification pure de `pipeline/pipeline.py`,
pas de fichier mu-plugin PHP : aucune etape de deploiement manuel cPanel
necessaire ici, a la difference des chantiers CTA/tracking). A confirmer
apres ce run que 2 articles "Aide isolation" sont bien publies avec
l'angle transactionnel attendu, et que le volume des 3 sous-silos
touches (Bouteilles, Chèque énergie, Aide isolation) correspond au
nouveau quota.

## Personnalisation des messages CTA (12/11/2026) — chantier en deux niveaux

Demande operateur : les mini-formulaires inline des articles portent deja
une promesse qui pousse au remplissage, mais elle est **generique par
silo** (4 messages pour ~1000 articles) -- objectif : un message plus
"frappant", avec une promesse de prise en charge specifique au sujet reel
de chaque article, pour ameliorer le taux de conversion. Propose et
valide avec l'operateur en deux niveaux distincts avant de coder quoi que
ce soit (cout d'une mauvaise implementation trop eleve pour deviner) :

- **Niveau 1 — par SOUS-SILO** : rapide, zero nouvelle donnee backend (le
  sous-silo est deja dans le 2e segment de l'URL). **Decision operateur :
  applique immediatement.**
- **Niveau 2 — par ARTICLE** : promesse unique par article (le mot-cle/
  angle reel), necessite une nouvelle brique (champ pipeline + stockage +
  lecture PHP + repli). **Decision operateur : prevu comme chantier
  separe, mise en prod dans quelques semaines**, avec generation **sur
  les nouveaux articles ET retroactif sur l'historique deja publie**
  ("il y a du trafic dessus").

### Niveau 1 — fait, deploye cote code (commit `577acc4`)

`wordpress-mu-plugins/cme-cta-progressifs.php` : avant ce commit, le choix
du message (`PAR_PREFIXE`, GAZ/ELEC/AIDES/SOLAIRE) ne lisait que le 1er
segment de l'URL (le silo). Nouvelle table `PAR_SOUS_SILO` (cle
`'{prefixe-silo}/{slug-sous-silo}'` → texte d'accroche), consultee en
priorite ; si le sous-silo n'y figure pas, repli silencieux sur le
message de silo existant -- aucun risque de regression, un sous-silo
absent se comporte exactement comme avant ce commit.

**Slugs VERIFIES, pas devinees** : `scripts-maintenance/lister_categories_wp.py`
(nouveau, lecture seule, pont GitHub Actions -- liste les 44 categories
WordPress reelles via `/wp-json/wp/v2/categories`) a confirme les slugs
exacts de tous les sous-silos avant d'ecrire la table JS. Necessaire car
certaines categories "Aide Énergétique" ont ete creees **manuellement**
en wp-admin (`Aide pompe à chaleur`, `Aide isolation`) -- rien ne
garantissait que leur slug WordPress reel soit identique a une simple
sanitisation du nom (accents, apostrophes). Resultat : les slugs
correspondent exactement a `to_slug()` (`pipeline.py`) sur les 44 cas
verifies -- aucune divergence trouvee, mais verifie plutot que suppose.

**Couverture volontairement plus large que le quota quotidien** : la
table couvre les **~34 sous-silos ayant deja des articles publies**
(`count > 0` dans la liste des categories), pas seulement les 14
sous-silos de `QUOTAS_SOUS_SILO` -- ca inclut aussi le silo distinct
"Rénovation Énergétique" (isolation/pompe-a-chaleur/chaudiere/poele/
chauffe-eau-thermodynamique/audit-energetique/bilan-energetique/
renovation-globale) et plusieurs sous-silos Gaz/Électricité/Aide
Énergétique qui ne sont plus dans le quota actif mais qui ont du trafic
reel sur leurs articles deja publies (ex. `facture-electricite` 90
articles, `bouteilles` 108, `maprimerenov` 72).

**Validation** : `php -l` + extraction et `node --check` du bloc JS, les
deux OK. **Pas encore deploye en prod** -- meme contrainte que d'habitude
pour ce fichier : `cloudshell download`, `.bak` horodate en cPanel,
upload dans `/wp-content/mu-plugins/`, purge des 2 caches LiteSpeed,
verifier avec `?t=$RANDOM` sur un article d'un sous-silo couvert (le
nouveau message doit remplacer le message de silo generique).

### Niveau 2 — chantier planifie, PAS encore implemente

A faire quand l'operateur donne le feu vert pour le demarrer (annonce :
"dans quelques semaines") :
1. **Pipeline** (`pipeline/pipeline.py`) : un champ de plus dans le brief
   genere par le LLM (comme `titre_seo`), une promesse courte adaptee au
   `mot_cle_principal`/angle reel de l'article (pas le sous-silo).
2. **Stockage** : post meta WordPress au moment de `publier_article()`
   (necessite d'enregistrer le meta avec `show_in_rest` pour pouvoir
   l'ecrire via l'API REST, ou un champ ACF/natif existant a verifier).
3. **Lecture cote mu-plugin** : meme technique que `CME_POST_ID` (deja
   interpole cote PHP via `get_the_ID()`) -- `get_post_meta(get_the_ID(),
   '_cme_cta_promesse', true)` expose dans un petit `<script>` interpole,
   lu par le JS avec repli sur le message de sous-silo (niveau 1) puis de
   silo si absent -- jamais de regression, degradation progressive a 3
   niveaux.
4. **Retroactif sur l'historique** (decision operateur confirmee : oui,
   "il y a du trafic dessus") : script par lot du meme type que les
   autres chantiers retroactifs de ce projet (dry-run par defaut,
   `--apply`, pont GitHub Actions, canari `--limite=N` avant le lot
   complet) -- genere la promesse via LLM a partir du `mot_cle_principal`/
   `titre_seo` deja en base dans `historique_publications`, pas besoin de
   relire le contenu complet de chaque article. Ordre de grandeur
   similaire aux autres lots IA du projet (~1000 appels Haiku, cout
   modeste, meme famille que l'audit reglementaire mensuel).
5. **Deploiement** : comme toujours pour ce fichier -- cPanel manuel,
   `.bak` horodate, purge des 2 caches LiteSpeed. Prevoir eventuellement
   un canari `MODE='apercu'` + `?cta60=1` avant le passage en `'actif'`
   (meme precaution que pour le tout premier deploiement du formulaire
   progressif en octobre), puisque c'est une nouvelle source de donnee
   affichee directement aux visiteurs.

## Quota quotidien uniformise a 1 article/sous-silo (13/11/2026)

Demande operateur : passer chaque sous-silo du quota a 1 article/jour.
Etat des lieux en lecture seule avant application (pattern habituel de ce
projet) : le quota actuel (`QUOTAS_SOUS_SILO`, `pipeline.py`) ne couvre que
14 sous-silos sur les 37 ayant du contenu deja publie (recoupement avec le
relevé reel des categories WordPress du 12/11, voir section
"Personnalisation des messages CTA" plus haut) -- 23 sous-silos avec du
contenu existant restent hors quota, dont **tout le silo Rénovation
Énergétique** (quota actuel nul). Question posee explicitement a
l'operateur avant d'appliquer, vu l'ecart de volume et le cout API
(Anthropic + SearchApi) que represente chacun des deux perimetres
possibles : (a) les 14 sous-silos deja actifs, chacun ramene/monte a 1 →
14/jour, ou (b) les 37 sous-silos avec du contenu existant, chacun a 1 →
37/jour, ce qui aurait reactive Rénovation Énergétique. **Reponse
operateur : perimetre (a) uniquement** -- les 14 sous-silos deja actifs,
aucune extension, aucune reactivation de silo.

**Applique** (`QUOTAS_SOUS_SILO`, `pipeline.py`) : les 7 sous-silos qui
etaient a quota > 1 ramenes a 1 (Bouteilles 2→1, Contrat Électricité 2→1,
Facture Électricité 2→1, MaPrimeRénov' 2→1, Aides chauffe-eau
thermodynamique 2→1, Aide pompe à chaleur 3→1, Aide isolation 2→1) ; les 7
sous-silos deja a 1 inchanges (Facture Gaz, Chèque énergie, et les 5
sous-silos Solaire). **Total quotidien vise : 14 articles/jour (etait
22)** -- baisse de volume, pas une hausse, malgre la formulation "1 par
sous-silo" qui aurait pu laisser croire a une extension.

Aucun autre changement de code necessaire : le mecanisme de selection
dynamique (GSC en priorite, fallback anciennete) et le suffixe
anti-collision (`" (N)"`) restent les memes -- ce dernier ne s'activera
simplement plus jamais en pratique tant qu'aucun sous-silo n'a de quota >
1 (plus de risque de doublon intra-run par construction, pas seulement par
le filtre anti-doublon existant).

`python3 -m py_compile pipeline/pipeline.py` valide (seul le
`SyntaxWarning` preexistant non lie, ligne ~2072) + verification
programmatique que le nouveau total est exactement 14 sur 14 sous-silos.
**Pas encore valide en conditions reelles** -- prend effet automatiquement
au prochain run de `publication-quotidienne.yml` (modification pure de
`pipeline/pipeline.py`, aucun fichier mu-plugin PHP, aucun deploiement
cPanel necessaire). A confirmer apres ce run que 14 articles sont bien
publies (1 par sous-silo), sans regression sur la selection dynamique ni
sur l'angle transactionnel (`Aide pompe à chaleur`/`Aide isolation`/
Solaire, inchange).
