FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien_js = """  if (DONNEES.publications_par_silo && DONNEES.publications_par_silo.length > 0) {
    new Chart(assurerCanvas('chartPublications'), {
      type: 'bar',
      data: {
        labels: DONNEES.publications_par_silo.map(p => p.silo),
        datasets: [{ label: 'Articles publies', data: DONNEES.publications_par_silo.map(p => p.nb), backgroundColor: '#f59e0b' }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });
  } else {
    document.getElementById('chartPublications').outerHTML = '<div class=\\"vide\\" id=\\"chartPublications\\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }
}"""

nouveau_js = """  if (DONNEES.publications_par_silo && DONNEES.publications_par_silo.length > 0) {
    new Chart(assurerCanvas('chartPublications'), {
      type: 'bar',
      data: {
        labels: DONNEES.publications_par_silo.map(p => p.silo),
        datasets: [{ label: 'Articles publies', data: DONNEES.publications_par_silo.map(p => p.nb), backgroundColor: '#f59e0b' }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });
  } else {
    document.getElementById('chartPublications').outerHTML = '<div class=\\"vide\\" id=\\"chartPublications\\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
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
    document.getElementById('chartIndexation').outerHTML = '<div class=\\"vide\\" id=\\"chartIndexation\\">' + TRADUCTIONS[langueActuelle()].aucune_donnee + '</div>';
  }
}"""

if "chartIndexation" in contenu and "couleursIndex" in contenu:
    print("SKIP : deja present")
elif ancien_js not in contenu:
    print("ERREUR : ancre non trouvee (toujours)")
else:
    contenu = contenu.replace(ancien_js, nouveau_js, 1)
    print("OK : logique JS ajoutee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
