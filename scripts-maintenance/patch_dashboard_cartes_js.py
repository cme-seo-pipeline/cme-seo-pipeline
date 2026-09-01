FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# Partie 1 : ajouter les cartes HTML
ancien_html = '''  <div class="carte">
    <h2>Evaluations d'impact par verdict</h2>
    <canvas id="chartEvals"></canvas>
  </div>
</div>'''

nouveau_html = '''  <div class="carte">
    <h2>Evaluations d'impact par verdict</h2>
    <canvas id="chartEvals"></canvas>
  </div>
  <div class="carte">
    <h2>Top 10 opportunites SEO (score)</h2>
    <canvas id="chartOpportunites"></canvas>
  </div>
  <div class="carte">
    <h2>Couverture RankMath (mot-cle cible)</h2>
    <canvas id="chartRankmath"></canvas>
  </div>
  <div class="carte">
    <h2>Sante technique du site (495 pages)</h2>
    <canvas id="chartAudit"></canvas>
  </div>
  <div class="carte">
    <h2>Leads par outil (tous canaux)</h2>
    <canvas id="chartLeads"></canvas>
  </div>
  <div class="carte">
    <h2>Publications par silo</h2>
    <canvas id="chartPublications"></canvas>
  </div>
</div>'''

if "chartOpportunites" in contenu:
    print("SKIP (partie 1) : deja present")
elif ancien_html not in contenu:
    print("ERREUR (partie 1) : ancre HTML non trouvee")
else:
    contenu = contenu.replace(ancien_html, nouveau_html, 1)
    print("OK (partie 1/2) : cartes HTML ajoutees")

# Partie 2 : ajouter la logique JS des graphiques
ancien_js = '''  } else {
    document.getElementById('chartEvals').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }
}
</script>'''

nouveau_js = '''  } else {
    document.getElementById('chartEvals').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.opportunites && DONNEES.opportunites.length > 0) {
    new Chart(document.getElementById('chartOpportunites'), {
      type: 'bar',
      data: {
        labels: DONNEES.opportunites.map(o => o.url.length > 25 ? o.url.slice(0,25)+'...' : o.url),
        datasets: [{ label: 'Score d\\'opportunite', data: DONNEES.opportunites.map(o => o.score), backgroundColor: '#7e22ce' }]
      },
      options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } } }
    });
  } else {
    document.getElementById('chartOpportunites').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.rankmath_couverture) {
    const rm = DONNEES.rankmath_couverture;
    if ((rm.avec_mot_cle + rm.sans_mot_cle) > 0) {
      new Chart(document.getElementById('chartRankmath'), {
        type: 'doughnut',
        data: {
          labels: ['Avec mot-cle cible', 'Sans mot-cle cible'],
          datasets: [{ data: [rm.avec_mot_cle, rm.sans_mot_cle], backgroundColor: ['#16a34a', '#dc2626'] }]
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
      });
    } else {
      document.getElementById('chartRankmath').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
    }
  }

  if (DONNEES.audit_technique && DONNEES.audit_technique.length > 0) {
    new Chart(document.getElementById('chartAudit'), {
      type: 'doughnut',
      data: {
        labels: DONNEES.audit_technique.map(a => a.categorie),
        datasets: [{ data: DONNEES.audit_technique.map(a => a.nb), backgroundColor: ['#16a34a','#f59e0b','#dc2626','#64748b'] }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
  } else {
    document.getElementById('chartAudit').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.leads_par_outil && DONNEES.leads_par_outil.length > 0) {
    new Chart(document.getElementById('chartLeads'), {
      type: 'bar',
      data: {
        labels: DONNEES.leads_par_outil.map(l => l.outil),
        datasets: [{ label: 'Leads', data: DONNEES.leads_par_outil.map(l => l.nb), backgroundColor: '#2563eb' }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });
  } else {
    document.getElementById('chartLeads').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }

  if (DONNEES.publications_par_silo && DONNEES.publications_par_silo.length > 0) {
    new Chart(document.getElementById('chartPublications'), {
      type: 'bar',
      data: {
        labels: DONNEES.publications_par_silo.map(p => p.silo),
        datasets: [{ label: 'Articles publies', data: DONNEES.publications_par_silo.map(p => p.nb), backgroundColor: '#f59e0b' }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });
  } else {
    document.getElementById('chartPublications').outerHTML = '<div class="vide">Aucune donnee disponible</div>';
  }
}
</script>'''

if "chartOpportunites" in contenu and "new Chart(document.getElementById('chartOpportunites')" in contenu:
    print("SKIP (partie 2) : deja present")
elif ancien_js not in contenu:
    print("ERREUR (partie 2) : ancre JS non trouvee")
else:
    contenu = contenu.replace(ancien_js, nouveau_js, 1)
    print("OK (partie 2/2) : logique JS ajoutee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
