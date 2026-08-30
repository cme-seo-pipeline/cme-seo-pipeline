"""
CME — Souverainete Shell : acces SSH / WP-CLI a l'hebergement o2switch.

Contexte : WordPress n'exposait jusqu'ici que sa REST API (contenu
uniquement). Ce mecanisme donne un acces complet au serveur (fichiers de
plugin, WP-CLI), valide de bout en bout le 30/08/2026.

Prerequis :
- Cle SSH generee et autorisee dans cPanel (Acces SSH > Gerer les cles)
- IP source autorisee dans cPanel (Outils > Autorisation SSH) — ATTENTION :
  ce mecanisme bloque le port 22 par defaut et necessite une IP fixe
  autorisee. Cloud Run n'a PAS d'IP sortante fixe par defaut : ce script
  fonctionne depuis Cloud Shell (IP relativement stable) mais PAS encore
  depuis une automatisation Cloud Run sans configuration reseau
  supplementaire (Cloud NAT + IP statique reservee) — chantier a part.
- Secrets stockes : O2SWITCH_SSH_PRIVATE_KEY, O2SWITCH_SSH_PASSPHRASE

Site cible confirme : /home/jolu5920/public_html/comprendre-mon-energie.com
(le chemin contient ".com" mais le site reel repond sur .fr — verifie via
`wp option get siteurl`, ne jamais supposer le mapping domaine/dossier).

Autre site sur le meme compte (NE PAS CONFONDRE) :
/home/jolu5920/public_html/ -> mon-electricite.fr
"""
import subprocess
import io
import paramiko

WP_PATH = "/home/jolu5920/public_html/comprendre-mon-energie.com"
SSH_HOST = "109.234.167.170"
SSH_PORT = 22
SSH_USER = "jolu5920"


def get_secret(nom):
    return subprocess.check_output(
        ["gcloud", "secrets", "versions", "access", "latest", f"--secret={nom}"],
        text=True
    )


def connecter():
    cle = get_secret("O2SWITCH_SSH_PRIVATE_KEY")
    passphrase = get_secret("O2SWITCH_SSH_PASSPHRASE").strip()
    pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=SSH_HOST, port=SSH_PORT, username=SSH_USER, pkey=pkey, timeout=15)
    return client


def wp_cli(commande):
    """Execute une commande WP-CLI sur le site comprendre-mon-energie.fr."""
    client = connecter()
    stdin, stdout, stderr = client.exec_command(f'wp --path="{WP_PATH}" {commande}')
    resultat = stdout.read().decode().strip()
    erreur = stderr.read().decode().strip()
    client.close()
    if erreur:
        raise Exception(f"Erreur WP-CLI : {erreur}")
    return resultat


if __name__ == "__main__":
    print(wp_cli("core version"))
