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

Aucun de ces workflows n'exécute automatiquement les scripts de
`scripts-maintenance/` — ce sont des scripts à lancer manuellement.

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

## Divergence connue, non résolue

`pipeline.py` à la racine du repo (~85 Ko, legacy, **non exécuté** par les
GitHub Actions — le pipeline actif est `pipeline/pipeline.py`) contient
potentiellement les mêmes `CTA_TOOLS`/`generer_cta_html()` mais n'a pas été
vérifié pour cohérence avec les changements CTA d'octobre 2026. Faible
priorité (fichier inutilisé par l'automatisation), mais à nettoyer ou
supprimer un jour pour éviter toute confusion future.
