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
| `audit-mensuel.yml` | cron mensuel (1er du mois, 3h UTC) + `workflow_dispatch` | Audit factuel des valeurs réglementaires citées dans les articles (`auditer_articles_action.py`) — **sans rapport avec les CTA** |
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
