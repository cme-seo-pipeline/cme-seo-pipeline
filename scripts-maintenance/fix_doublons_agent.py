import subprocess, requests, json, io
import paramiko

def get_secret(nom):
    return subprocess.check_output(
        ["gcloud", "secrets", "versions", "access", "latest", f"--secret={nom}"], text=True
    )

ANTHROPIC_KEY = get_secret("ANTHROPIC_API_KEY").strip()
cle_ssh = get_secret("O2SWITCH_SSH_PRIVATE_KEY")
passphrase = get_secret("O2SWITCH_SSH_PASSPHRASE").strip()
pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle_ssh), password=passphrase)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname="109.234.167.170", port=22, username="jolu5920", pkey=pkey, timeout=15)
WP_PATH = "/home/jolu5920/public_html/comprendre-mon-energie.com"

# Pour chaque paire : (post_id a corriger, titre du jumeau a eviter, mot-cle)
a_corriger = [
    (7334, "Aides chaudière fioul : cumulez MaPrimeRénov' + CEE", "aides chaudière fioul cumul"),
    (7270, "Eco-PTZ vs MaPrimeRénov' : lequel choisir ?", "Eco-PTZ vs MaPrimeRénov'"),
]

for post_id, titre_jumeau, mot_cle in a_corriger:
    prompt = (
        "Tu es un expert SEO technique ET commercial pour un site francais sur l'energie.\n"
        f"Mot-cle cible : {mot_cle}\n"
        f"IMPORTANT : une AUTRE page du site a deja ce titre exact : \"{titre_jumeau}\"\n"
        "Genere un NOUVEAU titre SEO (50-60 caracteres) DIFFERENT de celui-ci, "
        "et une NOUVELLE meta description (140-160 caracteres), pour la MEME thematique "
        "mais un angle distinct (ex: liste de criteres, question differente, "
        "focus sur un aspect specifique). Approche commerciale/transactionnelle, "
        "jamais de donnee inventee.\n"
        'Reponds UNIQUEMENT en JSON strict : {"titre": "...", "meta": "..."}'
    )
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 300, "messages": [{"role": "user", "content": prompt}]}
    )
    resp.raise_for_status()
    texte = resp.json()['content'][0]['text']
    texte_json = texte[texte.find('{'):texte.rfind('}')+1]
    correction = json.loads(texte_json)
    nouveau_titre = correction['titre']
    nouvelle_meta = correction['meta']

    titre_echap = nouveau_titre.replace('"', '\\"')
    meta_echap = nouvelle_meta.replace('"', '\\"')
    cmd = (f'wp --path="{WP_PATH}" post meta update {post_id} rank_math_title "{titre_echap}" && '
           f'wp --path="{WP_PATH}" post meta update {post_id} rank_math_description "{meta_echap}"')
    stdin, stdout, stderr = ssh.exec_command(cmd)
    sortie = stdout.read().decode()
    erreur = stderr.read().decode()
    print(f"post_id {post_id} -> {nouveau_titre}")
    print(f"  sortie: {sortie.strip()}")
    if erreur:
        print(f"  erreur: {erreur.strip()}")

ssh.close()
