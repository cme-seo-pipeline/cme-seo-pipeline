FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''    import subprocess
    import io
    import paramiko

    try:
        cle = subprocess.check_output(
            ["gcloud", "secrets", "versions", "access", "latest",
             "--secret=O2SWITCH_SSH_PRIVATE_KEY"],
            text=True
        )
        passphrase = subprocess.check_output(
            ["gcloud", "secrets", "versions", "access", "latest",
             "--secret=O2SWITCH_SSH_PASSPHRASE"],
            text=True
        ).strip()
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)'''

nouveau = '''    import io
    import paramiko

    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        if not cle or not passphrase:
            raise Exception("O2SWITCH_SSH_PRIVATE_KEY ou O2SWITCH_SSH_PASSPHRASE absent des variables d'environnement")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)'''

if "os.environ.get(\"O2SWITCH_SSH_PRIVATE_KEY\"" in contenu:
    print("⏭️  PATCH (secrets o2switch via env) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (secrets o2switch via env) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (secrets o2switch via env) : corrige")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
