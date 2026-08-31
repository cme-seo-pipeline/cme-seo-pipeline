FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/test-ssh-o2switch', methods=['GET'])"

nouvelle_route = '''@app.route('/wp-shell', methods=['GET'])
def wp_shell():
    """
    Endpoint generique de diagnostic/commande WP-CLI via SSH (Cloud Run,
    IP fixe). Parametre 'cmd' = commande WP-CLI a executer (sans le 'wp'
    initial ni --path, ajoutes automatiquement). Temporaire, pour le
    chantier G.1 (deploiement des plugins).
    """
    import io
    import paramiko

    commande = request.args.get('cmd', 'plugin list --format=csv --fields=name,status')

    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname="109.234.167.170", port=22, username="jolu5920",
                        pkey=pkey, timeout=15)

        wp_path = "/home/jolu5920/public_html/comprendre-mon-energie.com"
        stdin, stdout, stderr = client.exec_command(f'wp --path="{wp_path}" {commande}')
        resultat = stdout.read().decode()
        erreur = stderr.read().decode()
        client.close()

        return jsonify({"status": "ok", "resultat": resultat, "erreur": erreur or None}), 200
    except Exception as e:
        return jsonify({"status": "erreur", "detail": str(e)}), 500


'''

if "wp_shell" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
