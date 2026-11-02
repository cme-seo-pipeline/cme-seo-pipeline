"""
CME — Verification des leads du VRAI formulaire de contact WPForms
(/contactez-un-expert/, formulaire #472), avant de les regrouper dans le
meme onglet Google Sheets que les 3 mini-formulaires inline
(contact-expert-inline / appel-expert-inline / appel-header-formulaire).

Demande operateur (02/11/2026) : "on verifie les leads enregistres sur le
formulaire 'contactez-un-expert' et on regroupe le tout sur le meme
fichier sheets, la meme feuille d'inline formulaire et bouton headers."

Ce script repond a la partie VERIFICATION, en lecture seule :
- volume et fenetre de dates des lignes tool='contact-expert-formulaire'
  dans leads_convertis (confirme que le tracking (voies 1/2/3 JS, voir
  cme-tracking-conversion.php) capture reellement des soumissions) ;
- completude des champs (prenom/nom/email/telephone/code_postal), pour
  savoir AVANT de modifier le filtre du relais Sheets si ces lignes
  apportent une information exploitable (nom/telephone a rappeler) ou
  seulement un compteur de conversion horodate.

Pourquoi cette 2e question est cruciale ici (contrairement aux 3 outils
inline) : le payload JS envoye pour ce tool (voir surSoumissionFormulaire()
dans cme-tracking-conversion.php) est `{tool, details: {form_id}}` --
AUCUN champ prenom/telephone/email n'est lu depuis le formulaire WPForms
lui-meme avant envoi. server.py (/api/log-lead) par defaut ces champs a
une chaine vide s'ils sont absents du payload. Ce script confirme (ou
infirme) cette lecture de code sur les donnees reelles.

LECTURE SEULE -- aucune ecriture.
Necessite GOOGLE_APPLICATION_CREDENTIALS.

USAGE :
  python3 verifier_leads_formulaire_contact_expert.py [--jours=30]
"""
import sys

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"


def main():
    jours = 30
    for arg in sys.argv[1:]:
        if arg.startswith("--jours="):
            jours = int(arg.split("=", 1)[1])

    client = bigquery.Client(project=PROJECT_ID)

    print(f"📥 Lignes tool='contact-expert-formulaire' (leads_convertis, {jours} derniers jours)...\n")
    df = client.query(f"""
        SELECT timestamp, prenom, nom, email, telephone, code_postal,
               source_page, source_post_id, details, user_agent
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE tool = 'contact-expert-formulaire'
          AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {jours} DAY)
        ORDER BY timestamp
    """).to_dataframe()

    if df.empty:
        print(f"⚠️ Aucune ligne 'contact-expert-formulaire' sur les {jours} derniers jours.")
        print("   -> soit aucune soumission reelle, soit le tracking (voies 1/2/3 JS) ne capture rien.")
        # Verifie aussi sans fenetre de temps, au cas ou les seules lignes
        # existantes seraient plus anciennes que la fenetre demandee.
        df_total = client.query(f"""
            SELECT COUNT(*) AS n, MIN(timestamp) AS premiere, MAX(timestamp) AS derniere
            FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
            WHERE tool = 'contact-expert-formulaire'
        """).to_dataframe()
        n = int(df_total.iloc[0]["n"])
        if n:
            print(f"\nℹ️ {n} ligne(s) au total (toutes dates), de {df_total.iloc[0]['premiere']} a {df_total.iloc[0]['derniere']}.")
            print("   -> hors de la fenetre demandee, relancer avec --jours plus grand.")
        else:
            print("\nℹ️ 0 ligne au total, toutes dates confondues.")
        return

    print(f"✅ {len(df)} ligne(s) trouvee(s).\n")

    # Completude des champs potentiellement utiles pour un suivi commercial.
    print("=" * 100)
    print("COMPLETUDE DES CHAMPS (nb de lignes NON vides / total)")
    print("=" * 100)
    for champ in ["prenom", "nom", "email", "telephone", "code_postal"]:
        non_vides = int((df[champ].astype(str).str.strip() != "").sum())
        print(f"  {champ:15s} : {non_vides}/{len(df)} non vide(s)")

    print("\n" + "=" * 100)
    print(f"ECHANTILLON (les {min(5, len(df))} plus recentes lignes)")
    print("=" * 100)
    for _, row in df.tail(5).iterrows():
        print(f"\n  {row['timestamp']}")
        print(f"    prenom={row['prenom']!r}  telephone={row['telephone']!r}  email={row['email']!r}  code_postal={row['code_postal']!r}")
        print(f"    source_page={row['source_page']!r}")
        print(f"    details={row['details']!r}")

    print("\n" + "=" * 100)
    print("FENETRE DE DATES")
    print("=" * 100)
    print(f"  Premiere : {df['timestamp'].min()}")
    print(f"  Derniere : {df['timestamp'].max()}")
    print(f"  Total    : {len(df)} ligne(s) sur {jours} jours")


if __name__ == "__main__":
    main()
