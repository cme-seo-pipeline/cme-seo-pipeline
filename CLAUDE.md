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
uniquement `wordpress-mu-plugins/cme-cta-progressifs.php` — les **boutons
CTA progressifs insérés dans le corps du texte** (toutes les ~230 mots,
fonction `demarrer()`) restent inchangés, ce n'est pas une bannière.

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

## Divergence connue, non résolue

`pipeline.py` à la racine du repo (~85 Ko, legacy, **non exécuté** par les
GitHub Actions — le pipeline actif est `pipeline/pipeline.py`) contient
potentiellement les mêmes `CTA_TOOLS`/`generer_cta_html()` mais n'a pas été
vérifié pour cohérence avec les changements CTA d'octobre 2026. Faible
priorité (fichier inutilisé par l'automatisation), mais à nettoyer ou
supprimer un jour pour éviter toute confusion future.

`/wp-json/cme/v1/log-lead-debug` (endpoint de diagnostic ajouté dans
`cme-tracking-conversion.php` pendant l'incident IAM du 19/10, voir
ci-dessus) est resté en place après résolution — il n'expose qu'un
statut HTTP générique (aucune donnée personnelle), risque faible, mais à
retirer à la prochaine modification de ce fichier pour ne pas laisser un
endpoint public inutile.
