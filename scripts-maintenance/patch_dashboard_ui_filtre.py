FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# Partie 1 : CSS pour la barre de filtre
ancien_css = "  .vide { color: #64748b; font-size: 14px; text-align: center; padding: 40px 0; }"
nouveau_css = """  .vide { color: #64748b; font-size: 14px; text-align: center; padding: 40px 0; }
  #barre-filtre { grid-column: 1 / -1; display: flex; align-items: center; gap: 12px; background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 14px 20px; }
  #barre-filtre label { font-size: 13px; color: #94a3b8; display: flex; align-items: center; gap: 6px; }
  #barre-filtre input[type=date] { background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 6px 10px; border-radius: 6px; font-size: 13px; }
  #barre-filtre button { background: #2563eb; border: none; color: white; padding: 8px 18px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; }
  #barre-filtre button:hover { background: #1d4ed8; }
  #periode-affichee { font-size: 13px; color: #64748b; margin-left: auto; }"""

if "#barre-filtre" in contenu:
    print("SKIP (partie 1) : deja present")
elif ancien_css not in contenu:
    print("ERREUR (partie 1) : ancre CSS non trouvee")
else:
    contenu = contenu.replace(ancien_css, nouveau_css, 1)
    print("OK (partie 1/3) : CSS ajoute")

# Partie 2 : barre de filtre HTML
ancien_html = '''<div id="vue-dashboard">
  <div class="carte">
    <h2>Top pages par impressions (GSC, 30 derniers jours)</h2>'''

nouveau_html = '''<div id="vue-dashboard">
  <div id="barre-filtre">
    <label>Du <input type="date" id="date-debut"></label>
    <label>au <input type="date" id="date-fin"></label>
    <button id="appliquer-filtre" onclick="rechargerAvecFiltre()">Appliquer</button>
    <span id="periode-affichee"></span>
  </div>
  <div class="carte">
    <h2>Top pages par impressions (GSC, periode selectionnee)</h2>'''

if 'id="barre-filtre"' in contenu:
    print("SKIP (partie 2) : deja present")
elif ancien_html not in contenu:
    print("ERREUR (partie 2) : ancre HTML non trouvee")
else:
    contenu = contenu.replace(ancien_html, nouveau_html, 1)
    print("OK (partie 2/3) : barre de filtre HTML ajoutee")

# Partie 3 : logique JS
ancien_js = '''async function chargerDashboard() {
  window.dashboardCharge = true;
  try {
    const res = await fetch('/orcaas-dashboard-data');
    const donnees = await res.json();
    dessinerGraphiques(donnees);
  } catch (e) {
    document.getElementById('vue-dashboard').innerHTML = '<div class="vide">Erreur de chargement : ' + e.message + '</div>';
  }
}'''

nouveau_js = '''function datesParDefaut() {
  const auj = new Date();
  const il30j = new Date(auj);
  il30j.setDate(il30j.getDate() - 30);
  return { debut: il30j.toISOString().slice(0,10), fin: auj.toISOString().slice(0,10) };
}

async function chargerDashboard(dateDebut, dateFin) {
  window.dashboardCharge = true;
  const defaut = datesParDefaut();
  const db = dateDebut || defaut.debut;
  const df = dateFin || defaut.fin;
  document.getElementById('date-debut').value = db;
  document.getElementById('date-fin').value = df;
  try {
    const res = await fetch('/orcaas-dashboard-data?date_debut=' + db + '&date_fin=' + df);
    const donnees = await res.json();
    document.getElementById('periode-affichee').textContent = 'Periode : ' + (donnees.date_debut || db) + ' au ' + (donnees.date_fin || df);
    dessinerGraphiques(donnees);
  } catch (e) {
    document.getElementById('vue-dashboard').innerHTML = '<div class="vide">Erreur de chargement : ' + e.message + '</div>';
  }
}

function rechargerAvecFiltre() {
  const db = document.getElementById('date-debut').value;
  const df = document.getElementById('date-fin').value;
  chargerDashboard(db, df);
}'''

if "function rechargerAvecFiltre" in contenu:
    print("SKIP (partie 3) : deja present")
elif ancien_js not in contenu:
    print("ERREUR (partie 3) : ancre JS non trouvee")
else:
    contenu = contenu.replace(ancien_js, nouveau_js, 1)
    print("OK (partie 3/3) : logique JS remplacee")

# Partie 4 : fonction utilitaire pour eviter "Canvas is already in use"
# quand le dashboard est recharge plusieurs fois (filtre par date)
ancien_fn_dessiner = "function dessinerGraphiques(DONNEES) {\n  Chart.defaults.color = '#94a3b8';\n  Chart.defaults.borderColor = '#334155';\n"
nouveau_fn_dessiner = """function assurerCanvas(id) {
  var el = document.getElementById(id);
  var chartExistant = Chart.getChart(id);
  if (chartExistant) { chartExistant.destroy(); }
  if (!el || el.tagName !== 'CANVAS') {
    var c = document.createElement('canvas');
    c.id = id;
    if (el) { el.replaceWith(c); } 
    el = c;
  }
  return el;
}

function dessinerGraphiques(DONNEES) {
  Chart.defaults.color = '#94a3b8';
  Chart.defaults.borderColor = '#334155';
"""

if "function assurerCanvas" in contenu:
    print("SKIP (partie 4) : deja present")
elif ancien_fn_dessiner not in contenu:
    print("ERREUR (partie 4) : ancre fonction dessinerGraphiques non trouvee")
else:
    contenu = contenu.replace(ancien_fn_dessiner, nouveau_fn_dessiner, 1)
    # Remplacer chaque document.getElementById('chartX') par assurerCanvas('chartX')
    # UNIQUEMENT dans les appels "new Chart(document.getElementById(...)"
    import re
    contenu_avant = contenu
    contenu = re.sub(
        r"new Chart\(document\.getElementById\('(chart\w+)'\)",
        r"new Chart(assurerCanvas('\1')",
        contenu
    )
    nb_remplacements = len(re.findall(r"new Chart\(assurerCanvas\(", contenu))
    print(f"OK (partie 4/4) : fonction assurerCanvas ajoutee, {nb_remplacements} appels Chart mis a jour")

    # Partie 5 : les messages "vide" doivent garder le meme id, sinon
    # assurerCanvas ne peut plus les retrouver/remplacer au chargement suivant
    contenu, nb_vides = re.subn(
        r"document\.getElementById\('(chart\w+)'\)\.outerHTML = '<div class=\"vide\">([^<]*)</div>';",
        r"document.getElementById('\1').outerHTML = '<div class=\"vide\" id=\"\1\">\2</div>';",
        contenu
    )
    print(f"OK (partie 5/5) : {nb_vides} messages vides corriges pour garder leur id")


with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
