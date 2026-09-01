FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/orcaas', methods=['GET'])"

nouvelle_route = r'''@app.route('/orcaas-dashboard', methods=['GET'])
def orcaas_dashboard_page():
    """AGENT ORCAAS : dashboard visuel (stack Dashboard/Data Analytics),
    genere par ORCAAS lui-meme -- pas un outil externe."""
    import json as json_module
    from pipeline import agent_orcaas_donnees_dashboard, init_bigquery

    try:
        client_bq = init_bigquery()
        donnees = agent_orcaas_donnees_dashboard(client_bq)
    except Exception as e:
        donnees = {"top_pages": [], "briefs_par_probleme": [], "evaluations_par_verdict": [], "erreur": str(e)}

    donnees_json = json_module.dumps(donnees, ensure_ascii=False)

    html = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ORCAAS - Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 0; }
  header { background: #1e3a5f; padding: 16px 24px; display: flex; align-items: center; gap: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.3); }
  header h1 { margin: 0; font-size: 20px; }
  header .badge { background: #2563eb; padding: 4px 10px; border-radius: 12px; font-size: 12px; }
  header a { margin-left: auto; color: #93c5fd; text-decoration: none; font-size: 14px; }
  main { padding: 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 24px; max-width: 1400px; margin: 0 auto; }
  .carte { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; }
  .carte h2 { margin: 0 0 16px 0; font-size: 15px; color: #93c5fd; font-weight: 600; }
  .vide { color: #64748b; font-size: 14px; text-align: center; padding: 40px 0; }
</style>
</head>
<body>
<header>
  <h1>ORCAAS</h1>
  <span class="badge">Dashboard</span>
  <a href="/orcaas">&larr; Retour au chat</a>
</header>
<main>
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
</main>
<script>
const DONNEES = __DONNEES_JSON__;
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
</script>
</body>
</html>"""

    html = html.replace("__DONNEES_JSON__", donnees_json)
    return html


'''

if "orcaas_dashboard_page" in contenu:
    print("SKIP : deja present")
elif ancre not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
