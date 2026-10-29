"""
CME — Diagnostic ponctuel (lecture seule, aucune ligne inseree en base) :
pourquoi interactions_contenu est vide (0 ligne) alors que le mecanisme a
ete documente comme "deploye et valide" le 26/10/2026. Verifie les 3
maillons de la chaine, dans l'ordre, sans rien ecrire :

  1. Le code JS live sur le site contient-il bien les nouveaux trackers
     (journaliserInteraction/prefixeSilo) -- confirme ou infirme que le
     mu-plugin cPanel a vraiment ete mis a jour depuis le 26/10 (rappel :
     ce fichier n'est PAS versionne automatiquement sur le serveur, cf.
     CLAUDE.md -- upload cPanel manuel requis apres chaque modification).
  2. Le relais WordPress /wp-json/cme/v1/log-interaction repond-il (existe
     -- cote PHP, versionne par le MEME fichier que le point 1).
  3. L'endpoint Cloud Run /api/log-interaction repond-il (existe cote
     service deploye -- rappel : pas de CI/CD Cloud Run dans ce repo,
     gcloud run deploy est une action operateur manuelle).

CORRECTIF du 29/10/2026 : les maillons 2 et 3 testaient l'existence de la
route avec un GET, en supposant qu'un code autre que 404 confirmerait sa
presence (comportement Flask : 405 sur mismatch de methode). Mais
WordPress renvoie 404 "rest_no_route" pour N'IMPORTE QUEL mismatch de
methode (pas 405) -- un GET sur une route POST-only y est indistinguable
d'une route reellement absente. Cela avait produit une fausse alerte sur
/log-interaction ET, plus grave, sur /log-lead (route de production
critique, en realite fonctionnelle) -- voir
diagnostiquer_regression_log_lead.py. Les deux maillons testent desormais
en POST, avec un corps JSON vide ({}), que les deux endpoints (verifie par
lecture de code : cme_relayer_log_interaction() cote PHP, log_interaction()
cote Flask) traitent comme "0 evenement" sans ecrire la moindre ligne en
base -- donc toujours lecture seule au sens propre (pas d'INSERT declenche).

USAGE :
  python3 diagnostiquer_chaine_interactions_contenu.py
"""
import sys

import requests

WP_URL = "https://www.comprendre-mon-energie.fr"
CLOUD_RUN_URL = "https://cme-tracking-api-217943559750.europe-west1.run.app"


def main():
    print("="*70)
    print("MAILLON 1 — Code JS live sur un article (mu-plugin cPanel a jour ?)")
    print("="*70)
    try:
        # Un article recent connu pour avoir le mini-formulaire + le tracker clics
        r = requests.get(f"{WP_URL}/solaire/kit-solaire/kit-solaire-vs-panneau-solaire-seul-comparatif/", timeout=20)
        html = r.text
        for fonction in ["journaliserInteraction", "prefixeSilo", "viderInteractions", "CME_POST_ID"]:
            present = fonction in html
            print(f"  {'✅' if present else '❌'} '{fonction}' {'trouve' if present else 'ABSENT'} dans le HTML live")
    except Exception as e:
        print(f"  ⚠️ Erreur de lecture de la page : {e}")

    print(f"\n{'='*70}")
    print("MAILLON 2 — Relais WordPress /wp-json/cme/v1/log-interaction")
    print(f"{'='*70}")
    try:
        # POST avec corps JSON vide : traite comme "0 evenement" par le
        # relais (cme_relayer_log_interaction() republie tel quel, et
        # l'endpoint Cloud Run en aval renvoie inserted=0 sans ecrire --
        # voir le commentaire de tete). Un 404 ici reste un vrai "route
        # absente" (WordPress le renvoie aussi sur methode invalide, mais
        # POST est justement la bonne methode) ; un 200 confirme la presence.
        r = requests.post(f"{WP_URL}/wp-json/cme/v1/log-interaction", json={}, timeout=20)
        print(f"  POST {{}} -> HTTP {r.status_code}")
        if r.status_code == 404:
            print("  ❌ Route absente -- le mu-plugin cPanel ne contient probablement pas ce relais")
        elif r.status_code == 200:
            print("  ✅ Route presente et fonctionnelle")
        else:
            print("  ⚠️ Route presente mais reponse inattendue")
        print(f"  Corps (200 premiers caracteres) : {r.text[:200]}")
    except Exception as e:
        print(f"  ⚠️ Erreur : {e}")

    print(f"\n{'='*70}")
    print("MAILLON 3 — Endpoint Cloud Run /api/log-interaction")
    print(f"{'='*70}")
    try:
        # Meme logique : POST corps vide, traite comme 0 evenement par
        # log_interaction() (verifie par lecture de code, aucune ligne
        # inseree dans interactions_contenu).
        r = requests.post(f"{CLOUD_RUN_URL}/api/log-interaction", json={}, timeout=20)
        print(f"  POST {{}} -> HTTP {r.status_code}")
        if r.status_code == 404:
            print("  ❌ Route absente sur le service Cloud Run deploye -- /api/log-interaction")
            print("     n'a probablement jamais ete redeploye (gcloud run deploy, action operateur)")
        elif r.status_code == 200:
            print("  ✅ Route presente et fonctionnelle")
        else:
            print("  ⚠️ Route presente mais reponse inattendue")
        print(f"  Corps (200 premiers caracteres) : {r.text[:200]}")
    except Exception as e:
        print(f"  ⚠️ Erreur : {e}")

    print(f"\n{'='*70}")
    print("MAILLON 3bis — Comparaison avec une route Cloud Run connue fonctionnelle")
    print(f"{'='*70}")
    try:
        # log-lead EXIGE des champs pour etre utile, mais un corps vide est
        # accepte sans erreur par son propre contrat (voir CLAUDE.md,
        # incident du 28/10) -- insere neanmoins une ligne vide en prod,
        # donc on se contente ici d'une requete OPTIONS (jamais 404 si la
        # route existe, et aucune ecriture declenchee) plutot que POST.
        r = requests.options(f"{CLOUD_RUN_URL}/api/log-lead", timeout=20)
        print(f"  OPTIONS {CLOUD_RUN_URL}/api/log-lead -> HTTP {r.status_code} (reference, route confirmee en prod)")
    except Exception as e:
        print(f"  ⚠️ Erreur : {e}")


if __name__ == "__main__":
    main()
