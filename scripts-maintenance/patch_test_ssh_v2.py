FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/test-ip-sortante', methods=['GET'])"

nouvelle_route = '''@app.route('/test-ssh-o2switch', methods=['GET'])
def test_ssh_o2switch():
    """
    VALIDATION CHANTIER RESEAU : confirme qu'une connexion SSH reelle vers
    o2switch fonctionne DEPUIS Cloud Run (pas seulement depuis Cloud Shell),
    via le connecteur VPC + Cloud NAT + IP fixe. Endpoint temporaire de
    diagnostic (pas destine a rester en production).
    """
    import subprocess
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
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname="109.234.167.170", port=22, username="jolu5920",
                        pkey=pkey, timeout=15)

        wp_path = "/home/jolu5920/public_html/comprendre-mon-energie.com"
        stdin, stdout, stderr = client.exec_command(f'wp --path="{wp_path}" core version')
        resultat = stdout.read().decode().strip()
        erreur = stderr.read().decode().strip()
        client.close()

        return jsonify({"status": "ok", "wp_version": resultat, "erreur": erreur or None}), 200
    except Exception as e:
        return jsonify({"status": "erreur", "detail": str(e)}), 500


'''

if "test_ssh_o2switch" in contenu:
    print("⏭️  PATCH (test SSH o2switch) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (test SSH o2switch) : ancre non trouvee")
else:
    # IMPORTANT : on insere AVANT l'ancre (pas apres), pour ne jamais
    # scinder la fonction existante en deux.
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("✅ PATCH (test SSH o2switch) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
