"""
CME — Ecrit la description de la categorie WordPress "Aide isolation"
(id=69, parent "Aide Energetique" id=61), actuellement vide (0 car.,
cf. verifier_description_categories_aide.py, 13/11/2026).

Demande operateur du 13/11/2026 : "je veux maintenant une description
pour le sous silo aide-isolation". Texte redige pour suivre exactement
la convention deja en place sur les categories voisines du meme silo
(notamment "Aide pompe à chaleur", qui partage le meme angle editorial
transactionnel -- cf. CLAUDE.md, "Aide pompe à chaleur" / "Nouveau
sous-silo Aide isolation", confirmation operateur "Absolument le même
angle") : memes aides nommees (MaPrimeRénov', CEE, eco-PTZ, TVA reduite,
aides locales/Anah), meme structure (aides -> montants/conditions ->
demarches -> pieges a eviter), longueur comparable (~420 car., vs 413
pour pompe a chaleur).

ECRITURE -- dry-run par defaut (affiche la description actuelle et
celle qui serait ecrite, n'ecrit rien), --apply pour ecrire reellement
via l'API REST WordPress (categories, meme authentification Application
Password que le reste du pipeline).

USAGE :
  python3 definir_description_categorie_aide_isolation.py           # dry-run
  python3 definir_description_categorie_aide_isolation.py --apply    # ecrit
"""
import os
import sys

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
WP_USERNAME = os.environ.get("WP_USERNAME", "Ouss")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
if not WP_APP_PASSWORD:
    sys.exit("❌ WP_APP_PASSWORD manquant dans l'environnement (ne jamais le coder en dur ici)")

AUTH = (WP_USERNAME, WP_APP_PASSWORD)
CATEGORY_ID = 69  # aide-isolation

NOUVELLE_DESCRIPTION = (
    "Toutes les aides financières disponibles pour l’isolation de votre "
    "logement : MaPrimeRénov’, primes CEE (Coup de pouce isolation), "
    "éco-prêt à taux zéro, TVA réduite à 5,5 %, et aides locales ou de "
    "l’Anah. Retrouvez les montants selon vos revenus, les conditions "
    "d’éligibilité, les démarches pas à pas et les pièges à éviter pour "
    "financer vos travaux d’isolation des combles, murs, toiture ou "
    "plancher au meilleur coût."
)


def main():
    apply = "--apply" in sys.argv

    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories/{CATEGORY_ID}",
        params={"context": "edit"},
        auth=AUTH,
        timeout=15,
    )
    if r.status_code != 200:
        sys.exit(f"❌ HTTP {r.status_code} lecture categorie : {r.text[:300]}")
    cat = r.json()
    actuelle = (cat.get("description") or "").strip()

    print(f"Categorie : {cat['slug']} (id={cat['id']})")
    print(f"Description actuelle ({len(actuelle)} car.) : {actuelle!r}")
    print(f"Nouvelle description ({len(NOUVELLE_DESCRIPTION)} car.) :")
    print(f"  {NOUVELLE_DESCRIPTION!r}")

    if not apply:
        print("\n🔎 DRY-RUN -- aucune ecriture. Relancer avec --apply pour ecrire.")
        return

    r2 = requests.post(
        f"{WP_URL}/wp-json/wp/v2/categories/{CATEGORY_ID}",
        auth=AUTH,
        json={"description": NOUVELLE_DESCRIPTION},
        timeout=15,
    )
    if r2.status_code not in (200, 201):
        sys.exit(f"❌ HTTP {r2.status_code} ecriture : {r2.text[:300]}")
    confirmee = (r2.json().get("description") or "").strip()
    if confirmee == NOUVELLE_DESCRIPTION:
        print("\n✅ Description ecrite et confirmee par relecture de la reponse API.")
    else:
        print(f"\n⚠️  Ecriture envoyee mais la description relue differe : {confirmee!r}")


if __name__ == "__main__":
    main()
