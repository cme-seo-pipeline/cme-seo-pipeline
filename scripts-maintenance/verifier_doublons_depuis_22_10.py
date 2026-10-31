"""
CME — Audit rigoureux (lecture seule) de la garde anti-duplication des
mots-cles, demande par l'operateur le 31/10/2026 ("vu le volume qu'on va
avoir les prochains mois, il faut etre rigoureux sur ce point").

Contexte : 3 root causes de duplication editoriale ont ete trouvees et
corrigees en octobre 2026 (voir CLAUDE.md, sections "Duplication
editoriale" et "suite") :
  #1 (20/10) : publier_actualites_reglementaires() publiait un article par
      indicateur reglementaire change, sans dedoublonnage -- corrige par
      un garde en memoire intra-run + verifier_doublons().
  #2 (20/10) : selectionner_silos_a_traiter() pouvait reselectionner le
      meme mot-cle run apres run -- corrige par un filtre SQL NOT IN sur
      l'historique recent.
  #3+#4 (22/10) : verifier_et_differencier_sujet() recevait un sous-silo
      SUFFIXE (' (2)', ' (3)'...) pour les sous-silos a quota > 1 et
      filtrait dessus tel quel -- ne trouvait donc JAMAIS aucune ligne
      pour l'occurrence >= 2, exactement le cas le plus a risque. Corrige
      en debasant le sous-silo avant la requete, + un bug d'echappement
      SQL trouve au passage (backslash vs doublement de guillemet).

verifier_doublons_post_fix.py (20/10) avait deja valide les causes #1/#2.
CLAUDE.md note explicitement que le correctif #3/#4 (22/10) n'avait PAS
encore ete valide en conditions reelles au moment de son commit. Ce script
etend cette validation sur toute la fenetre ecoulee depuis (22/10 -> ce
jour), avec un focus specifique sur les sous-silos a quota > 1 (le cas que
le bug #3/#4 cassait precisement).

LECTURE SEULE -- aucune ecriture.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    from pipeline import init_bigquery, PROJECT_ID, DATASET_ID
except Exception as e:
    sys.exit(f"❌ Import de pipeline/pipeline.py impossible : {e}")

FENETRE_DEBUT = "2026-10-22T00:00:00Z"  # date du correctif #3/#4

SOUS_SILOS_QUOTA_SUP_1 = [
    "Bouteilles", "Facture Électricité", "Contrat Électricité",
    "MaPrimeRénov'", "Chèque énergie", "Aides chauffe-eau thermodynamique",
    "Kit solaire", "Panneaux solaires", "Batterie panneaux solaires",
    "Système solaire combiné", "Chauffe-eau solaire",
]


def main():
    client_bq = init_bigquery()

    print("=" * 80)
    print(f"1. Mots-cles EXACTEMENT identiques republies pour le meme sous-silo")
    print(f"   (base, suffixe retire) depuis {FENETRE_DEBUT}, fenetre de 90j glissante")
    print("   -- signature directe des 3 root causes corrigees en octobre")
    print("=" * 80)
    df1 = client_bq.query(f"""
        SELECT
            h1.date_publication AS date_nouvelle, h1.post_id AS post_id_nouveau,
            SPLIT(h1.sous_silo_strategique, ' (')[OFFSET(0)] AS sous_silo_base,
            h1.mot_cle AS mot_cle,
            h2.date_publication AS date_precedente, h2.post_id AS post_id_precedent,
            TIMESTAMP_DIFF(h1.date_publication, h2.date_publication, MINUTE) AS ecart_minutes
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications` h1
        JOIN `{PROJECT_ID}.{DATASET_ID}.historique_publications` h2
          ON LOWER(h1.mot_cle) = LOWER(h2.mot_cle)
          AND SPLIT(h1.sous_silo_strategique, ' (')[OFFSET(0)]
            = SPLIT(h2.sous_silo_strategique, ' (')[OFFSET(0)]
          AND h2.date_publication < h1.date_publication
          AND h2.date_publication >= TIMESTAMP_SUB(h1.date_publication, INTERVAL 90 DAY)
        WHERE h1.date_publication >= '{FENETRE_DEBUT}'
          AND h1.mot_cle IS NOT NULL AND h1.mot_cle != ''
        ORDER BY h1.date_publication DESC
    """).to_dataframe()
    if df1.empty:
        print("   ✅ Aucun mot-cle exactement republie depuis le correctif du 22/10.")
    else:
        print(f"   ⚠️ {len(df1)} cas trouves :")
        print(df1.to_string(index=False))

    print("\n" + "=" * 80)
    print("2. Meme jour, meme sous-silo (base), DEUX articles partageant au moins")
    print("   3 mots de plus de 3 lettres dans leur mot-cle -- signature precise")
    print("   du bug #3/#4 ('jumeaux' publies a quelques minutes d'ecart DANS LE")
    print("   MEME RUN, occurrence >=2 d'un sous-silo a quota > 1)")
    print("=" * 80)
    df2 = client_bq.query(f"""
        WITH base AS (
          SELECT post_id, date_publication,
                 SPLIT(sous_silo_strategique, ' (')[OFFSET(0)] AS sous_silo_base,
                 mot_cle,
                 SPLIT(LOWER(mot_cle), ' ') AS mots
          FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
          WHERE date_publication >= '{FENETRE_DEBUT}'
            AND mot_cle IS NOT NULL AND mot_cle != ''
        ),
        paires AS (
          SELECT
              a.date_publication AS date_a, a.post_id AS post_id_a, a.mot_cle AS mot_cle_a,
              b.date_publication AS date_b, b.post_id AS post_id_b, b.mot_cle AS mot_cle_b,
              a.sous_silo_base,
              (SELECT COUNT(*) FROM UNNEST(a.mots) m WHERE LENGTH(m) > 3 AND m IN UNNEST(b.mots)) AS mots_communs
          FROM base a
          JOIN base b
            ON a.sous_silo_base = b.sous_silo_base
            AND a.post_id < b.post_id
            AND DATE(a.date_publication) = DATE(b.date_publication)
        )
        SELECT * EXCEPT(mots_communs) FROM paires WHERE mots_communs >= 3
        ORDER BY date_a DESC
    """).to_dataframe()
    if df2.empty:
        print("   ✅ Aucune paire 'jumelle' (meme jour, meme sous-silo, mots-cles tres proches).")
    else:
        print(f"   ⚠️ {len(df2)} paire(s) suspecte(s) -- a relire manuellement (faux positifs possibles) :")
        print(df2.to_string(index=False))

    print("\n" + "=" * 80)
    print("2bis. Diagnostic de la fenetre de comparaison de verifier_et_differencier_sujet()")
    print("      (LIMIT 15 ORDER BY date DESC) : pour chaque sous-silo a quota > 1,")
    print("      jusqu'a quand remonte le 15e article le plus recent AU MOMENT de")
    print("      chaque publication depuis le 22/10 -- si < 90 jours, un doublon")
    print("      plus ancien que cette fenetre echappe totalement a la verification,")
    print("      meme si verifier_doublons()/le filtre SQL amont le voyaient.")
    print("=" * 80)
    sous_silos_sql2 = "', '".join(s.replace("'", "\\'") for s in SOUS_SILOS_QUOTA_SUP_1)
    df2bis = client_bq.query(f"""
        WITH candidats AS (
          SELECT post_id, date_publication,
                 SPLIT(sous_silo_strategique, ' (')[OFFSET(0)] AS sous_silo_base
          FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
          WHERE date_publication >= '{FENETRE_DEBUT}'
            AND SPLIT(sous_silo_strategique, ' (')[OFFSET(0)] IN ('{sous_silos_sql2}')
        ),
        historique AS (
          SELECT post_id, date_publication,
                 SPLIT(sous_silo_strategique, ' (')[OFFSET(0)] AS sous_silo_base
          FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
          WHERE SPLIT(sous_silo_strategique, ' (')[OFFSET(0)] IN ('{sous_silos_sql2}')
        )
        SELECT
            c.post_id, c.date_publication, c.sous_silo_base,
            (SELECT MIN(h.date_publication) FROM (
                SELECT h2.date_publication FROM historique h2
                WHERE h2.sous_silo_base = c.sous_silo_base
                  AND h2.date_publication < c.date_publication
                ORDER BY h2.date_publication DESC LIMIT 15
             ) h) AS portee_15e_article,
            TIMESTAMP_DIFF(c.date_publication,
                (SELECT MIN(h.date_publication) FROM (
                    SELECT h2.date_publication FROM historique h2
                    WHERE h2.sous_silo_base = c.sous_silo_base
                      AND h2.date_publication < c.date_publication
                    ORDER BY h2.date_publication DESC LIMIT 15
                 ) h), DAY) AS portee_en_jours
        FROM candidats c
        ORDER BY c.sous_silo_base, c.date_publication
    """).to_dataframe()
    if df2bis.empty:
        print("   (aucune donnee)")
    else:
        resume = df2bis.groupby("sous_silo_base")["portee_en_jours"].agg(["min", "max", "mean", "count"])
        print(resume.to_string())
        print("\n   → 'min'/'max'/'mean' = nombre de jours couverts par les 15 articles")
        print("     les plus recents vus par verifier_et_differencier_sujet() au moment")
        print("     de chaque publication. A comparer a la fenetre anti-doublon de 90j.")

    print("\n" + "=" * 80)
    print("3. Detail complet de tous les articles publies depuis le 22/10 sur les")
    print("   sous-silos a QUOTA > 1 (le cas precis que le bug #3/#4 cassait) --")
    print("   pour relecture manuelle titre par titre, au-dela de ce qu'un script")
    print("   de correspondance exacte/approchee peut detecter")
    print("=" * 80)
    sous_silos_sql = "', '".join(s.replace("'", "\\'") for s in SOUS_SILOS_QUOTA_SUP_1)
    df3 = client_bq.query(f"""
        SELECT
            DATE(date_publication) AS jour, date_publication,
            SPLIT(sous_silo_strategique, ' (')[OFFSET(0)] AS sous_silo_base,
            sous_silo_strategique, titre, mot_cle, post_id
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE date_publication >= '{FENETRE_DEBUT}'
          AND SPLIT(sous_silo_strategique, ' (')[OFFSET(0)] IN ('{sous_silos_sql}')
        ORDER BY sous_silo_base, date_publication
    """).to_dataframe()
    if df3.empty:
        print("   ⚠️ Aucun article trouve sur ces sous-silos depuis le 22/10 (inattendu).")
    else:
        print(f"   {len(df3)} article(s) -- groupes par sous-silo :")
        for sous_silo_base, grp in df3.groupby("sous_silo_base"):
            print(f"\n   --- {sous_silo_base} ({len(grp)} articles) ---")
            for _, r in grp.iterrows():
                print(f"     {r['date_publication']} | {r['titre'][:70]!r} | mot-cle: {r['mot_cle']!r}")

    print("\n" + "=" * 80)
    print("4. Volume publie par jour depuis le 22/10 (contexte -- confirme que le")
    print("   pipeline continue de tourner au volume attendu)")
    print("=" * 80)
    df4 = client_bq.query(f"""
        SELECT DATE(date_publication) AS jour, COUNT(*) AS nb_articles
        FROM `{PROJECT_ID}.{DATASET_ID}.historique_publications`
        WHERE date_publication >= '{FENETRE_DEBUT}'
        GROUP BY jour ORDER BY jour
    """).to_dataframe()
    print(df4.to_string(index=False) if not df4.empty else "   (0 publication depuis le 22/10 -- a investiguer)")


if __name__ == "__main__":
    main()
