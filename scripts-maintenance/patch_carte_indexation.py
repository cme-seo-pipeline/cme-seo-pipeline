FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien_html = '''  <div class="carte">
    <h2 data-i18n="titre_publications">Publications par silo</h2>
    <canvas id="chartPublications"></canvas>
  </div>
</div>'''
nouveau_html = '''  <div class="carte">
    <h2 data-i18n="titre_publications">Publications par silo</h2>
    <canvas id="chartPublications"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_indexation">Indexation Google (statut reel par page)</h2>
    <canvas id="chartIndexation"></canvas>
  </div>
</div>'''

if 'id="chartIndexation"' in contenu:
    print("SKIP (partie 1) : deja present")
elif ancien_html not in contenu:
    print("ERREUR (partie 1) : ancre HTML non trouvee")
else:
    contenu = contenu.replace(ancien_html, nouveau_html, 1)
    print("OK (partie 1/3) : carte HTML ajoutee")

ancien_js = '''  if (DONNEES.publications_par_silo && DONNEES.publications_par_silo.length > 0) {
    new Chart(assurerCanvas('chartPublications'), {
      type: 'bar',
      data: {
        labels: DONNEES.publications_par_silo.map(p => p.silo),
        datasets: [{ label: 'Articles publies', data: DONNEES.publications_par_silo.map(p => p.nb), backgroundColor: '#f59e0b' }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });
  } else {
    document.getElementById('chartPublications').outerHTML = '<div class="vide" id="chartPublications">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }
}'''
nouveau_js = '''  if (DONNEES.publications_par_silo && DONNEES.publications_par_silo.length > 0) {
    new Chart(assurerCanvas('chartPublications'), {
      type: 'bar',
      data: {
        labels: DONNEES.publications_par_silo.map(p => p.silo),
        datasets: [{ label: 'Articles publies', data: DONNEES.publications_par_silo.map(p => p.nb), backgroundColor: '#f59e0b' }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });
  } else {
    document.getElementById('chartPublications').outerHTML = '<div class="vide" id="chartPublications">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }

  if (DONNEES.indexation && DONNEES.indexation.length > 0) {
    const couleursIndex = { 'Submitted and indexed': '#16a34a', 'Crawled - currently not indexed': '#f59e0b', 'URL is unknown to Google': '#dc2626' };
    new Chart(assurerCanvas('chartIndexation'), {
      type: 'doughnut',
      data: {
        labels: DONNEES.indexation.map(i => i.etat),
        datasets: [{ data: DONNEES.indexation.map(i => i.nb), backgroundColor: DONNEES.indexation.map(i => couleursIndex[i.etat] || '#2563eb') }]
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
  } else {
    document.getElementById('chartIndexation').outerHTML = '<div class="vide" id="chartIndexation">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }
}'''

if "chartIndexation" in contenu and "couleursIndex" in contenu:
    print("SKIP (partie 2) : deja present")
elif ancien_js not in contenu:
    print("ERREUR (partie 2) : ancre JS non trouvee")
else:
    contenu = contenu.replace(ancien_js, nouveau_js, 1)
    print("OK (partie 2/3) : logique JS ajoutee")

ancien_i18n_fr = '''    titre_publications: "Publications par silo",
  },'''
nouveau_i18n_fr = '''    titre_publications: "Publications par silo",
    titre_indexation: "Indexation Google (statut reel par page)",
  },'''
ancien_i18n_en = '''    titre_publications: "Publications by silo",
  }'''
nouveau_i18n_en = '''    titre_publications: "Publications by silo",
    titre_indexation: "Google indexing (real per-page status)",
  }'''

nb_i18n = 0
if 'titre_indexation: "Indexation Google' not in contenu and ancien_i18n_fr in contenu:
    contenu = contenu.replace(ancien_i18n_fr, nouveau_i18n_fr, 1)
    nb_i18n += 1
if 'titre_indexation: "Google indexing' not in contenu and ancien_i18n_en in contenu:
    contenu = contenu.replace(ancien_i18n_en, nouveau_i18n_en, 1)
    nb_i18n += 1
print(f"OK (partie 3/3) : {nb_i18n}/2 traductions ajoutees")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
