FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/wp-shell', methods=['GET'])"

nouvelle_route = '''@app.route('/wp-deploy', methods=['POST'])
def wp_deploy():
    """
    Ecrit un fichier directement sur le serveur o2switch via SFTP (meme
    canal SSH que wp-shell, IP fixe Cloud Run). Attend un JSON :
    {"chemin_distant": "...", "contenu": "..."}
    Temporaire, chantier G.1 (deploiement direct des plugins patches).
    """
    import io
    import paramiko

    data = request.get_json(silent=True) or {}
    chemin_distant = data.get('chemin_distant', '')
    contenu_fichier = data.get('contenu', '')

    if not chemin_distant or not contenu_fichier:
        return jsonify({"status": "erreur", "detail": "chemin_distant et contenu requis"}), 400

    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname="109.234.167.170", port=22, username="jolu5920",
                        pkey=pkey, timeout=15)

        sftp = client.open_sftp()
        with sftp.open(chemin_distant, 'w') as f:
            f.write(contenu_fichier)
        sftp.close()
        client.close()

        return jsonify({"status": "ok", "chemin": chemin_distant,
                         "taille": len(contenu_fichier)}), 200
    except Exception as e:
        return jsonify({"status": "erreur", "detail": str(e)}), 500


'''

if "wp_deploy" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
