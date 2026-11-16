"""
CME — Rappel de fraicheur des prix d'offres de marche (concurrents) du
comparateur-energie (demande operateur, 16/11/2026 : "on essaye de créer un
système qui nous rappelle de faire le changement, puisqu'on a une
restriction d'automatisation").

Contexte : les offres de marche (ELEC/GAZ, ~18 fournisseurs) du
comparateur-energie n'ont aucune source live fiable -- contrairement aux
deux offres de reference (EDF TRVE, Prix Repere gaz CRE) desormais branchees
sur indicateurs_reglementaires (voir tracking-api/server.py, /api/tarif-edf
et /api/tarif-gaz-repere). Elles doivent donc etre revues et mises a jour
MANUELLEMENT par l'operateur, a un rythme trimestriel -- rien a scraper/
automatiser ici, juste un rappel qui echoue visiblement si ca prend trop de
retard.

Mecanisme : lit la constante PHP CME_CMP_PRIX_MARCHE_DERNIERE_VERIF
(wordpress-plugins/comparateur-energie/comparateur-energie.php), qui doit
etre mise a jour par l'operateur (ou Claude Code a sa demande) a CHAQUE
revue manuelle des prix de marche, que des prix aient change ou non -- c'est
cette date, pas l'historique git du fichier (qui bouge pour des raisons
sans rapport, UI/UX, icones...), qui fait foi.

Lecture seule. Sort en erreur (exit 1) si le seuil trimestriel (configurable
via --seuil-jours) est depasse -- c'est volontaire : ce script est fait pour
etre lance par un workflow GitHub Actions recurrent et faire echouer le run
(visible dans l'onglet Actions, meme logique que les audits SEO technique
existants de ce projet) quand une revue manuelle est due.
"""
import re
import sys
from datetime import datetime, timezone

PHP_FILE = "wordpress-plugins/comparateur-energie/comparateur-energie.php"
SEUIL_JOURS_DEFAULT = 100  # ~1 trimestre + marge

def _arg_int(flag, default):
    for i, a in enumerate(sys.argv):
        if a == flag and i + 1 < len(sys.argv):
            return int(sys.argv[i + 1])
    return default

def main():
    seuil_jours = _arg_int("--seuil-jours", SEUIL_JOURS_DEFAULT)

    try:
        contenu = open(PHP_FILE, encoding="utf-8").read()
    except FileNotFoundError:
        sys.exit(f"❌ Fichier introuvable : {PHP_FILE}")

    m = re.search(r"CME_CMP_PRIX_MARCHE_DERNIERE_VERIF'\s*,\s*'(\d{4}-\d{2}-\d{2})'", contenu)
    if not m:
        sys.exit(
            "❌ Constante CME_CMP_PRIX_MARCHE_DERNIERE_VERIF introuvable dans "
            f"{PHP_FILE} -- le marqueur de fraicheur a peut-etre ete renomme ou "
            "supprime par erreur. A corriger avant de pouvoir verifier la fraicheur."
        )

    date_derniere_verif = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    aujourd_hui = datetime.now(timezone.utc)
    jours_ecoules = (aujourd_hui - date_derniere_verif).days

    print(f"Derniere verification manuelle des prix de marche : {m.group(1)} ({jours_ecoules} jour(s))")
    print(f"Seuil d'alerte (trimestriel) : {seuil_jours} jour(s)")

    if jours_ecoules >= seuil_jours:
        sys.exit(
            f"\n🔔 RAPPEL : les prix des offres de marche (ELEC/GAZ, comparateur-energie) "
            f"n'ont pas ete revus depuis {jours_ecoules} jours (seuil : {seuil_jours}).\n"
            "Action attendue (manuelle, aucune API fiable n'existe pour automatiser) :\n"
            "  1. Revisiter les ~18 offres de marche (tableaux ELEC/GAZ, "
            f"{PHP_FILE}) : prix au kWh, abonnement, conditions, et confirmer "
            "qu'aucun fournisseur n'a quitte/rejoint le marche (cf. retrait de "
            "Vattenfall le 16/11/2026, repris par Alterna).\n"
            "  2. Mettre a jour CME_CMP_PRIX_MARCHE_DERNIERE_VERIF a la date du jour, "
            "meme si aucun prix n'a change -- c'est elle qui reinitialise ce rappel.\n"
            "  3. Redeployer le plugin en cPanel (meme contrainte que d'habitude, "
            "fichier non versionne automatiquement sur le serveur)."
        )

    print("✅ Fraicheur dans les clous, rien a signaler.")

if __name__ == "__main__":
    main()
