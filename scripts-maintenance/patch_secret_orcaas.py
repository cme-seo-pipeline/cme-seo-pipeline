FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/', methods=['GET'])"

nouveau_bloc = '''CHEMINS_PUBLICS = {'/', '/orcaas', '/orcaas-dashboard', '/orcaas-chat'}
ORCAAS_ACTION_SECRET = os.environ.get("ORCAAS_ACTION_SECRET", "")


@app.before_request
def verifier_secret_action():
    """Protege tous les endpoints d'action (sync, audit, deploiement WP,
    agent ORCAAS ecriture) par un secret partage -- necessaire car le
    service est desormais public (plus de proxy Cloud Shell requis pour
    les pages /orcaas). Les pages publiques (chat, dashboard, healthcheck)
    restent librement accessibles."""
    if request.path in CHEMINS_PUBLICS:
        return None
    if request.method == 'OPTIONS':
        return None
    secret_recu = request.headers.get('X-Orcaas-Secret', '')
    if not ORCAAS_ACTION_SECRET or secret_recu != ORCAAS_ACTION_SECRET:
        return jsonify({"erreur": "Non autorise -- en-tete X-Orcaas-Secret requis"}), 401
    return None


'''

if "verifier_secret_action" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouveau_bloc + ancre, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
