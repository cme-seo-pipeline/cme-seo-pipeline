FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/auditer-site-technique', methods=['POST'])"

nouvelle_route = r'''@app.route('/orcaas-chat', methods=['POST'])
def orcaas_chat_endpoint():
    """AGENT ORCAAS : repond a une question en s'appuyant sur le contexte reel du projet."""
    from pipeline import agent_orcaas_chat, init_bigquery

    data = request.get_json(silent=True) or {}
    question = data.get('message', '').strip()
    if not question:
        return jsonify({"erreur": "message requis"}), 400

    try:
        client_bq = init_bigquery()
        reponse = agent_orcaas_chat(question, client_bq)
        return jsonify({"reponse": reponse}), 200
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


ORCAAS_CHAT_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ORCAAS</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 0; height: 100vh; display: flex; flex-direction: column; }
  header { background: #1e3a5f; padding: 16px 24px; display: flex; align-items: center; gap: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.3); }
  header h1 { margin: 0; font-size: 20px; }
  header .badge { background: #2563eb; padding: 4px 10px; border-radius: 12px; font-size: 12px; }
  #chat { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
  .msg { max-width: 70%; padding: 12px 16px; border-radius: 12px; line-height: 1.5; white-space: pre-wrap; }
  .msg.user { align-self: flex-end; background: #2563eb; color: white; }
  .msg.orcaas { align-self: flex-start; background: #1e293b; border: 1px solid #334155; }
  .msg.loading { align-self: flex-start; background: #1e293b; border: 1px solid #334155; opacity: .6; }
  #input-zone { padding: 16px 24px; display: flex; gap: 12px; border-top: 1px solid #334155; }
  #question { flex: 1; padding: 12px 16px; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: #e2e8f0; font-size: 15px; }
  #question:focus { outline: none; border-color: #2563eb; }
  #send { padding: 12px 24px; border-radius: 8px; border: none; background: #2563eb; color: white; font-weight: 600; cursor: pointer; }
  #send:hover { background: #1d4ed8; }
  #send:disabled { opacity: .5; cursor: not-allowed; }
</style>
</head>
<body>
<header>
  <h1>ORCAAS</h1>
  <span class="badge">SEO Specialiste IA</span>
</header>
<div id="chat">
  <div class="msg orcaas">Bonjour, je suis ORCAAS. Posez-moi une question sur l'etat du site, mes dernieres actions, ou les resultats obtenus.</div>
</div>
<div id="input-zone">
  <input type="text" id="question" placeholder="Posez votre question..." autocomplete="off" />
  <button id="send">Envoyer</button>
</div>
<script>
const chat = document.getElementById('chat');
const question = document.getElementById('question');
const send = document.getElementById('send');

function ajouterMessage(texte, classe) {
  const div = document.createElement('div');
  div.className = 'msg ' + classe;
  div.textContent = texte;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

async function envoyer() {
  const q = question.value.trim();
  if (!q) return;
  ajouterMessage(q, 'user');
  question.value = '';
  send.disabled = true;
  const loading = ajouterMessage('ORCAAS reflechit...', 'loading');
  try {
    const res = await fetch('/orcaas-chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: q})
    });
    const data = await res.json();
    loading.remove();
    ajouterMessage(data.reponse || data.erreur || 'Erreur inconnue', 'orcaas');
  } catch (e) {
    loading.remove();
    ajouterMessage('Erreur de connexion : ' + e.message, 'orcaas');
  }
  send.disabled = false;
  question.focus();
}

send.addEventListener('click', envoyer);
question.addEventListener('keypress', function(e) {
  if (e.key === 'Enter') envoyer();
});
</script>
</body>
</html>"""


@app.route('/orcaas', methods=['GET'])
def orcaas_chat_page():
    """Page visuelle de conversation avec ORCAAS."""
    return ORCAAS_CHAT_HTML


'''

if "orcaas_chat_page" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
