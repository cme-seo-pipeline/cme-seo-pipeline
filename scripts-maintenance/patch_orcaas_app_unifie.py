FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    lignes = f.readlines()

LIGNE_DEBUT = 644
LIGNE_FIN = 838

bloc_actuel = "".join(lignes[LIGNE_DEBUT-1:LIGNE_FIN])
if "orcaas_chat_page" not in bloc_actuel or "ORCAAS_CHAT_HTML" not in bloc_actuel:
    print("ERREUR : le bloc a ces lignes ne correspond pas a ce qui est attendu, arret sans modification")
else:
    nouveau_bloc = r'''ORCAAS_APP_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ORCAAS</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 0; height: 100vh; display: flex; flex-direction: column; }
  header { background: #1e3a5f; padding: 16px 24px; display: flex; align-items: center; gap: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.3); }
  header h1 { margin: 0; font-size: 20px; }
  header .badge { background: #2563eb; padding: 4px 10px; border-radius: 12px; font-size: 12px; }
  nav { display: flex; gap: 4px; margin-left: 24px; }
  nav button { background: transparent; border: none; color: #94a3b8; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; }
  nav button.actif { background: #2563eb; color: white; }

  #vue-chat { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
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

  #vue-dashboard { flex: 1; overflow-y: auto; padding: 24px; display: none; }
  #vue-dashboard.actif { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 24px; max-width: 1400px; margin: 0 auto; }
  .carte { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; }
  .carte h2 { margin: 0 0 16px 0; font-size: 15px; color: #93c5fd; font-weight: 600; }
  .vide { color: #64748b; font-size: 14px; text-align: center; padding: 40px 0; }
</style>
</head>
<body>
<header>
  <h1>ORCAAS</h1>
  <span class="badge">SEO Specialiste IA</span>
  <nav>
    <button id="onglet-chat" class="actif" onclick="afficherOnglet('chat')">Chat</button>
    <button id="onglet-dashboard" onclick="afficherOnglet('dashboard')">Dashboard</button>
  </nav>
</header>

<div id="vue-chat">
  <div id="chat">
    <div class="msg orcaas">Bonjour, je suis ORCAAS. Posez-moi une question sur l'etat du site, mes dernieres actions, ou les resultats obtenus.</div>
  </div>
  <div id="input-zone">
    <input type="text" id="question" placeholder="Posez votre question..." autocomplete="off" />
    <button id="send">Envoyer</button>
  </div>
</div>

<div id="vue-dashboard">
  <div class="carte">
    <h2>Top pages par impressions (GSC, 30 derniers jours)</h2>
    <canvas id="chartPages"></canvas>
  </div>
  <div class="carte">
    <h2>Corrections ORCAAS par type de probleme</h2>
    <canvas id="chartBriefs"></canvas>
  </div>
  <div class="carte">
    <h2>Evaluations d'impact par verdict</h2>
    <canvas id="chartEvals"></canvas>
  </div>
</div>

<script>
function afficherOnglet(nom) {
  document.getElementById('onglet-chat').classList.toggle('actif', nom === 'chat');
  document.getElementById('onglet-dashboard').classList.toggle('actif', nom === 'dashboard');
  document.getElementById('vue-chat').style.display = nom === 'chat' ? 'flex' : 'none';
  document.getElementById('vue-dashboard').classList.toggle('actif', nom === 'dashboard');
  if (nom === 'dashboard' && !window.dashboardCharge) {
    chargerDashboard();
  }
}

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

async function chargerDashboard() {
  window.dashboardCharge = true;
  try {
    const res = await fetch('/orcaas-dashboard-data');
    const donnees = await res.json();
    dessinerGraphiques(donnees);
  } catch (e) {
    document.getElementById('vue-dashboard').innerHTML = '<div class="vide">Erreur de chargement : ' + e.message + '</div>';
  }
}

function dessinerGraphiques(DONNEES) {
  Chart.defaults.color = '#94a3b8';
  Chart.defaults.borderColor = '#334155';

  if (DONNEES.top_pages && DONNEES.top_pages.length > 0) {
    new Chart(document.getElementById('chartPages'), {
      type: 'bar',
      data: {
        labels: DONNEES.top_pages.map(p => p.url.length > 30 ? p.url.slice(0,30)+'...' : p.url),
        datasets: [
          { label: 'Impressions', data: DONNEES.top_pages.map(p => p.impressions), backgroundColor: '#2563eb' },
          { label: 'Clics', data: DONNEES.top_pages.map(p => p.clics), backgroundColor: '#f59e0b' }
        ]
      },
      options: { indexAxis: 'y', responsive: true, plugins: { legend: { position: 'top' } } }
    });
  } else {
    document.getElementById('chartPages').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.briefs_par_probleme && DONNEES.briefs_par_probleme.length > 0) {
    new Chart(document.getElementById('chartBriefs'), {
      type: 'doughnut',
      data: {
        labels: DONNEES.briefs_par_probleme.map(b => b.probleme),
        datasets: [{ data: DONNEES.briefs_par_probleme.map(b => b.nb), backgroundColor: ['#2563eb','#f59e0b','#16a34a','#dc2626','#7e22ce'] }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
  } else {
    document.getElementById('chartBriefs').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.evaluations_par_verdict && DONNEES.evaluations_par_verdict.length > 0) {
    new Chart(document.getElementById('chartEvals'), {
      type: 'doughnut',
      data: {
        labels: DONNEES.evaluations_par_verdict.map(v => v.verdict),
        datasets: [{ data: DONNEES.evaluations_par_verdict.map(v => v.nb), backgroundColor: ['#64748b','#16a34a','#dc2626','#2563eb'] }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
  } else {
    document.getElementById('chartEvals').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }
}
</script>
</body>
</html>"""


@app.route('/orcaas-dashboard-data', methods=['GET'])
def orcaas_dashboard_data_endpoint():
    """Donnees JSON du dashboard (page publique, appelee en arriere-plan par /orcaas)."""
    from pipeline import agent_orcaas_donnees_dashboard, init_bigquery
    try:
        client_bq = init_bigquery()
        donnees = agent_orcaas_donnees_dashboard(client_bq)
        return jsonify(donnees), 200
    except Exception as e:
        return jsonify({"top_pages": [], "briefs_par_probleme": [], "evaluations_par_verdict": [], "erreur": str(e)}), 500


@app.route('/orcaas', methods=['GET'])
def orcaas_chat_page():
    """Application unique ORCAAS : onglets Chat + Dashboard."""
    return ORCAAS_APP_HTML
'''
    lignes[LIGNE_DEBUT-1:LIGNE_FIN] = [nouveau_bloc]
    with open(FICHIER, "w", encoding="utf-8") as f:
        f.writelines(lignes)
    print("OK : bloc remplace (structure a onglets)")
