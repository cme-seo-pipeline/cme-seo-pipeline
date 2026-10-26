"""
CME — Ajout rétroactif de l'image à la une (carte titre verte + icône
sous-silo) aux 10 articles Solaire transactionnels publiés le 26/10/2026
par publier_articles_transactionnels_solaire.py.

Contexte : ce lot de publication appelait volontairement UNIQUEMENT
generer_brief_silo / rediger_article / inserer_lien_pilier / publier_article
(voir le commentaire "Volontairement HORS PERIMETRE" en tête de ce script),
donc ces 10 articles sont restés sans image à la une. Décision opérateur du
26/10/2026 (chantier "image principale Solaire") : carte titre verte
(couleurs CTA_TOOLS["4. Solaire"], déjà définies -- #052e16/#16a34a --
jamais utilisées en pratique jusqu'ici faute d'appel) + icône vectorielle
fixe par sous-silo (voir dessiner_icone_sous_silo() dans pipeline/pipeline.py,
ajoutée le même jour, et le rendu matplotlib pur existant generer_carte_titre()
-- AUCUNE génération par IA, ce mécanisme n'a jamais été branché dans ce
pipeline malgré la présence de generer_image_dalle()). Portée tranchée par
l'opérateur : ces 10 articles + tout futur article Solaire (déjà couvert
sans rien de plus à faire : generer_featured_images() est systématiquement
appelée pour tous les silos à la fin de run_pipeline(), et résout déjà les
couleurs via CTA_TOOLS["4. Solaire"] -- seule l'icône est nouvelle). Les 32
autres articles Solaire déjà publiés avant ce chantier restent HORS PERIMETRE
ici (pas de rétroactif demandé au-delà de ces 10).

Reutilise integralement generer_featured_images() (aucune réimplémentation) :
construit le DataFrame qu'elle attend à partir de historique_publications
(BigQuery) pour ces 10 post_id uniquement, puis l'appelle telle quelle --
y compris son contrôle d'unicité par empreinte sha256 (une carte strictement
identique à une carte déjà publiée ne serait pas republiée ; sans effet ici
car chaque titre d'article est différent, donc chaque empreinte aussi, même
avec une icône/fond identiques au sein d'un même sous-silo -- c'est exactement
le comportement "image constante pour le sous-silo, titre variable par
article" demandé).

USAGE :
  python3 ajouter_images_articles_solaire_transactionnels.py            # dry-run (défaut) : affiche ce qui serait fait, rien n'est publié
  python3 ajouter_images_articles_solaire_transactionnels.py --apply    # génère et pose réellement les 10 images

Nécessite WP_APP_PASSWORD (si --apply) et GOOGLE_APPLICATION_CREDENTIALS
dans l'environnement. ANTHROPIC_API_KEY / OPENAI non nécessaires (rendu
matplotlib pur, aucun appel IA).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import (
        CONFIG, WP_CONFIG, OPENAI_CONFIG, init_bigquery,
        generer_featured_images, PROJECT_ID, DATASET_ID,
    )
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

import pandas as pd

# Les 10 post_id publiés le 26/10/2026 par publier_articles_transactionnels_solaire.py
# (voir le bilan final de ce run -- 2 par sous-silo x 5 sous-silos Solaire).
POST_IDS = [12352, 12353, 12354, 12355, 12356, 12357, 12358, 12359, 12360, 12361]


def main():
    apply_mode = "--apply" in sys.argv

    print(f"{'='*70}")
    print(f"Mode : {'PUBLICATION RÉELLE (--apply)' if apply_mode else 'DRY-RUN (lecture seule, rien n’est publié)'}")
    print(f"{'='*70}")

    client_bq = init_bigquery()

    ids_sql = ", ".join(str(i) for i in POST_IDS)
    df = client_bq.query(f"""
        SELECT post_id AS Post_ID, silo AS Silo, titre AS Titre,
               mot_cle AS Mot_cle, sous_silo_strategique AS sous_silo,
               image_id, url_wp
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE post_id IN ({ids_sql})
        ORDER BY post_id
    """).to_dataframe()

    if df.empty:
        sys.exit("❌ Aucun des 10 post_id attendus n'a été trouvé dans historique_publications.")

    manquants = set(POST_IDS) - set(df['Post_ID'].tolist())
    if manquants:
        print(f"⚠️ {len(manquants)} post_id introuvable(s) dans historique_publications (ignorés) : {sorted(manquants)}")

    deja_illustres = df[df['image_id'].notna() & (df['image_id'] != '')]
    if not deja_illustres.empty:
        print(f"\n⚠️ {len(deja_illustres)} article(s) ont déjà un image_id enregistré "
              f"(retraités quand même -- le contrôle d'unicité de generer_featured_images() s'applique normalement) :")
        for _, r in deja_illustres.iterrows():
            print(f"   - post_id={r['Post_ID']} : image_id={r['image_id']}")

    print(f"\n{len(df)}/{len(POST_IDS)} article(s) trouvés :")
    for _, r in df.iterrows():
        print(f"  - post_id={r['Post_ID']} | {r['sous_silo']} | {r['Titre']}")
        print(f"      {r['url_wp']}")

    if not apply_mode:
        print("\n🔍 [DRY-RUN] Rien n'est publié. Relancer avec --apply pour générer et poser réellement les 10 images.")
        return

    df_publications = df.copy()
    # H1 non re-scrapé (pas besoin de recharger le HTML complet de chaque
    # article) : generer_featured_images() retombe sur la colonne Titre
    # quand Contenu_HTML ne contient pas de <h1>, ce qui est le cas attendu
    # ici (Titre = titre_seo stocké en base = H1 réel de rediger_article()).
    df_publications['Contenu_HTML'] = ''

    generer_featured_images(df_publications, client_bq, CONFIG, OPENAI_CONFIG, WP_CONFIG)


if __name__ == "__main__":
    main()
