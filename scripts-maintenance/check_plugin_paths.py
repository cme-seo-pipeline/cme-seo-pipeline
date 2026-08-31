import io, paramiko

def get_secret(nom):
    import subprocess
    return subprocess.check_output(
        ["gcloud", "secrets", "versions", "access", "latest", f"--secret={nom}"],
        text=True
    )

cle = get_secret("O2SWITCH_SSH_PRIVATE_KEY")
passphrase = get_secret("O2SWITCH_SSH_PASSPHRASE").strip()
pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname="109.234.167.170", port=22, username="jolu5920", pkey=pkey, timeout=15)

WP = "/home/jolu5920/public_html/comprendre-mon-energie.com"
cmd = f'wp --path="{WP}" plugin list --format=csv --fields=name,status'
stdin, stdout, stderr = client.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
client.close()
