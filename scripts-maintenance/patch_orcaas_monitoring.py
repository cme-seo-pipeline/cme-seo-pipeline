FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "def rafraichir_indicateurs_reglementaires(client_bq):"

nouvelle_fonction = '''def agent_orcaas_monitoring_pipeline(client_bq, date_cible=None):
    """AGENT ORCAAS -- Stack Monitoring du pipeline (nouvelle, ajoutee le
    02/09/2026 suite a un incident reel : deux executions concurrentes du
    pipeline principal ont produit 7 paires d'articles sur le meme sujet,
    avec des titres legerement differents -- une comparaison de texte simple
    ne les aurait pas detectees. Utilise Claude pour juger la similarite
    semantique entre articles publies le meme jour dans le meme silo.
    Controle total : supprime automatiquement le plus recent de chaque
    paire confirmee (WordPress + BigQuery), genere un brief par
    intervention."""
    print("AGENT ORCAAS -- Monitoring du pipeline...")

    if not date_cible:
        date_cible = datetime.now().date().isoformat()

    try:
        df = client_bq.query(f"""
            SELECT post_id, silo, titre, date_publication
            FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications`
            WHERE DATE(date_publication) = '{date_cible}'
            ORDER BY silo, date_publication
        """).to_dataframe()
    except Exception as e:
        print(f"  Erreur lecture historique_publications : {e}")
        return {"paires_analysees": 0, "doublons_supprimes": 0}

    if len(df) < 2:
        print("  Moins de 2 articles ce jour, rien a analyser")
        return {"paires_analysees": 0, "doublons_supprimes": 0}

    import io
    import paramiko
    try:
        cle = os.environ.get("O2SWITCH_SSH_PRIVATE_KEY", "")
        passphrase = os.environ.get("O2SWITCH_SSH_PASSPHRASE", "")
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cle), password=passphrase)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname="109.234.167.170", port=22, username="jolu5920", pkey=pkey, timeout=15)
    except Exception as e:
        print(f"  Erreur connexion SSH : {e}")
        return {"paires_analysees": 0, "doublons_supprimes": 0}

    wp_path = "/home/jolu5920/public_html/comprendre-mon-energie.com"
    briefs = []
    supprimes = 0
    deja_traites = set()

    for silo in df['silo'].unique():
        sous_df = df[df['silo'] == silo].reset_index(drop=True)
        for i in range(len(sous_df)):
            id_a = int(sous_df.iloc[i]['post_id'])
            if id_a in deja_traites:
                continue
            for j in range(i + 1, len(sous_df)):
                id_b = int(sous_df.iloc[j]['post_id'])
                if id_b in deja_traites:
                    continue
                titre_a = sous_df.iloc[i]['titre']
                titre_b = sous_df.iloc[j]['titre']

                prompt = (
                    "Ces deux titres d'articles, publies le meme jour dans le meme silo "
                    "thematique, traitent-ils du MEME sujet exact (un vrai doublon de "
                    "contenu, pas juste une thematique proche) ?\\n"
                    f"Titre A : {titre_a}\\n"
                    f"Titre B : {titre_b}\\n"
                    'Reponds UNIQUEMENT en JSON strict, rien d\\'autre : {"meme_sujet": true}'
                    ' ou {"meme_sujet": false}'
                )
                meme_sujet = False
                try:
                    resp = requests.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": CONFIG['ANTHROPIC_API_KEY'], "anthropic-version": "2023-06-01", "content-type": "application/json"},
                        json={"model": CONFIG['MODEL'], "max_tokens": 50, "messages": [{"role": "user", "content": prompt}]},
                        timeout=20
                    )
                    resp.raise_for_status()
                    texte = resp.json()['content'][0]['text']
                    texte_json = texte[texte.find('{'):texte.rfind('}') + 1]
                    jugement = json.loads(texte_json)
                    meme_sujet = bool(jugement.get('meme_sujet', False))
                except Exception:
                    meme_sujet = False

                if not meme_sujet:
                    continue

                deja_traites.add(id_b)
                statut = "echec"
                erreur = None
                try:
                    cmd = f'wp --path="{wp_path}" post delete {id_b} --force'
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    sortie = stdout.read().decode()
                    if "Success" in sortie:
                        client_bq.query(
                            f"DELETE FROM `{PROJECT_ID}.04_pipeline_seo.historique_publications` WHERE post_id = {id_b}"
                        ).result()
                        statut = "corrige"
                        supprimes += 1
                    else:
                        erreur = sortie[:200]
                except Exception as e:
                    erreur = str(e)[:200]

                briefs.append({
                    "brief_id": f"{id_b}_{int(datetime.now().timestamp())}",
                    "date_execution": datetime.now().isoformat(),
                    "stack": "monitoring_pipeline", "post_id": id_b, "url": "",
                    "probleme_detecte": f"doublon_sujet (conserve {id_a} : {titre_a[:60]})",
                    "valeur_avant": titre_b, "valeur_apres": "Article supprime (WordPress + BigQuery)",
                    "statut": statut, "erreur": erreur,
                })
                break

    ssh.close()

    if briefs:
        try:
            client_bq.insert_rows_json(f"{PROJECT_ID}.04_pipeline_seo.agent_orcaas_briefs", briefs)
        except Exception as e:
            print(f"  Erreur ecriture briefs : {e}")

    print(f"  {len(briefs)} paire(s) confirmee(s), {supprimes} suppression(s) reussie(s)")
    return {"paires_analysees": len(briefs), "doublons_supprimes": supprimes}


def rafraichir_indicateurs_reglementaires(client_bq):'''

if "def agent_orcaas_monitoring_pipeline" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_fonction, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
