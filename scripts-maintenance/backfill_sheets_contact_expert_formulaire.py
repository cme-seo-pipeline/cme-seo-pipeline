"""
CME — Backfill, dans l'onglet Google Sheets "Leads Formulaire Article",
de l'historique des leads tool='contact-expert-formulaire' (le vrai
formulaire WPForms /contactez-un-expert/) -- jamais relayes vers ce Sheet
avant le 02/11/2026 (le filtre de cme_relayer_log_lead() ne les incluait
pas). Demande operateur (02/11) : "on enregistre les leads capture depuis
06/10/2026 sur notre fichier sheets qui regroupe maintenant".

PERIMETRE VOLONTAIREMENT LIMITE a ce seul tool. Les 3 autres
('contact-expert-inline', 'appel-expert-inline', 'appel-header-formulaire')
sont relayes en continu vers ce Sheet depuis leur creation respective --
rejouer leur historique dupliquerait chaque lead deja present, sans aucun
moyen de nettoyer ensuite (pas d'acces API Sheets depuis ce sandbox). Voir
CLAUDE.md pour le detail du raisonnement.

DEDUPLICATION DU BUG DE DOUBLE COMPTAGE (corrige le 02/11, voir CLAUDE.md
"Leads du vrai formulaire de contact") : chaque soumission reelle avant ce
correctif produisait 2 lignes dans leads_convertis (voie 1 + voie 3, a
quelques secondes d'intervalle). Regrouper celles-ci en UNE seule ligne
avant de les envoyer au Sheet, sous peine de doubler artificiellement le
nombre de leads affiches. Regroupement par fenetre temporelle (lignes a
moins de FENETRE_DEDUP_SECONDES l'une de l'autre = meme soumission
reelle) -- represente chaque groupe par sa 1ere ligne (timestamp le plus
proche de l'instant reel de soumission), sauf pour source_page : prefere
la page d'origine du formulaire (/contactez-un-expert/) a la page de
confirmation (/demande-confirmee/) quand les deux sont presentes dans le
groupe, plus informative pour un suivi commercial.

Rejoue chaque lead deduplique en appelant le MEME endpoint Apps Script que
le relais WordPress en production (meme format de payload que
cme_relayer_log_lead() -> cme-formulaire-article-leads.gs), avec le VRAI
timestamp d'origine (necessite le correctif du 02/11 sur ecrireSheet(),
qui respecte desormais d.timestamp -- a redeployer cote operateur avant
--apply, sinon les lignes seront datees du moment du backfill et non de
la soumission reelle).

OPERATION A USAGE UNIQUE -- ne pas relancer --apply une seconde fois
apres un run reussi (aucune dedup possible cote Sheet, chaque appel
ajoute une ligne sans verifier si elle existe deja).

USAGE :
  python3 backfill_sheets_contact_expert_formulaire.py [--depuis=2026-10-06]                 (dry-run)
  python3 backfill_sheets_contact_expert_formulaire.py --apply --confirmation=BACKFILL-UNIQUE
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

try:
    from google.cloud import bigquery
except ImportError:
    sys.exit("❌ google-cloud-bigquery manquant")

PROJECT_ID = "seo-data-hub-cme"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxpzUna-KBj6kpASyufpeAz0rF2C-lXFHSAjpUGiHnrqpTujYsLnUZi9aJlQrHciSThxA/exec"
FENETRE_DEDUP_SECONDES = 5


def dedupliquer(rows):
    """Regroupe les lignes a moins de FENETRE_DEDUP_SECONDES les unes des
    autres (meme soumission reelle, doublee par le bug voie1+voie3).
    Retourne une liste de leads deduplique (timestamp du 1er de chaque
    groupe, source_page preferant la page d'origine du formulaire)."""
    if not rows:
        return []
    groupes = []
    groupe_courant = [rows[0]]
    for row in rows[1:]:
        dernier = groupe_courant[-1]
        if (row["timestamp"] - dernier["timestamp"]) <= timedelta(seconds=FENETRE_DEDUP_SECONDES):
            groupe_courant.append(row)
        else:
            groupes.append(groupe_courant)
            groupe_courant = [row]
    groupes.append(groupe_courant)

    leads = []
    for groupe in groupes:
        representant = groupe[0]
        page_origine = next(
            (r for r in groupe if "demande-confirmee" not in (r["source_page"] or "")),
            None,
        )
        leads.append({
            "timestamp": representant["timestamp"],
            "source_page": (page_origine or representant)["source_page"] or "",
            "nb_lignes_brutes": len(groupe),
        })
    return leads


def main():
    depuis = "2026-10-06"
    apply_mode = False
    confirmation = ""
    for arg in sys.argv[1:]:
        if arg.startswith("--depuis="):
            depuis = arg.split("=", 1)[1]
        elif arg == "--apply":
            apply_mode = True
        elif arg.startswith("--confirmation="):
            confirmation = arg.split("=", 1)[1]

    if apply_mode and confirmation != "BACKFILL-UNIQUE":
        sys.exit("❌ --apply necessite --confirmation=BACKFILL-UNIQUE (operation a usage unique, garde-fou volontaire).")

    client = bigquery.Client(project=PROJECT_ID)
    print(f"📥 leads_convertis, tool='contact-expert-formulaire', depuis {depuis}...\n")
    df = client.query(f"""
        SELECT timestamp, source_page
        FROM `{PROJECT_ID}.04_pipeline_seo.leads_convertis`
        WHERE tool = 'contact-expert-formulaire'
          AND DATE(timestamp) >= '{depuis}'
        ORDER BY timestamp
    """).to_dataframe()

    if df.empty:
        print("⚠️ Aucune ligne trouvee -- rien a backfiller.")
        return

    rows = [{"timestamp": ts.to_pydatetime(), "source_page": sp} for ts, sp in zip(df["timestamp"], df["source_page"])]
    leads = dedupliquer(rows)

    print(f"✅ {len(rows)} ligne(s) brute(s) en base -> {len(leads)} lead(s) reel(s) apres deduplication (fenetre {FENETRE_DEDUP_SECONDES}s).\n")
    print("=" * 100)
    print(f"{'#':>2}  {'Timestamp (reel)':<30}  {'Lignes brutes':<14}  Source page")
    print("=" * 100)
    for i, lead in enumerate(leads, 1):
        print(f"{i:>2}  {lead['timestamp'].isoformat():<30}  {lead['nb_lignes_brutes']:<14}  {lead['source_page']}")

    if not apply_mode:
        print(f"\n(dry-run -- relancer avec --apply --confirmation=BACKFILL-UNIQUE pour envoyer ces {len(leads)} lead(s) au Sheet)")
        return

    print(f"\n🚀 Envoi de {len(leads)} lead(s) vers l'Apps Script (meme endpoint que le relais production)...")
    for i, lead in enumerate(leads, 1):
        payload = {
            "tool": "contact-expert-formulaire",
            "prenom": "",
            "telephone": "",
            "email": "",
            "code_postal": "",
            "details": "{}",
            "source_page": lead["source_page"],
            "timestamp": lead["timestamp"].isoformat(),
        }
        url = APPS_SCRIPT_URL + "?payload=" + urllib.parse.quote(json.dumps(payload, ensure_ascii=False))
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                corps = resp.read().decode("utf-8", errors="replace")
                print(f"  [{i}/{len(leads)}] {lead['timestamp'].isoformat()} -> HTTP {resp.status} : {corps[:200]}")
        except Exception as e:
            print(f"  [{i}/{len(leads)}] {lead['timestamp'].isoformat()} -> ❌ ERREUR : {e}")
        time.sleep(1)  # espace les appels, pas de raison de solliciter Apps Script en rafale pour 2-3 lignes

    print("\n✅ Backfill termine. Verifier manuellement l'onglet 'Leads Formulaire Article' (pas d'acces API Sheets depuis ce sandbox).")


if __name__ == "__main__":
    main()
