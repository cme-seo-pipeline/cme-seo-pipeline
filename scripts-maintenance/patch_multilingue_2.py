FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien1 = '''<div id="chat">
    <div class="msg orcaas">Bonjour, je suis ORCAAS. Posez-moi une question sur l'etat du site, mes dernieres actions, ou les resultats obtenus.</div>
  </div>
  <div id="input-zone">
    <input type="text" id="question" placeholder="Posez votre question..." autocomplete="off" />
    <button id="send">Envoyer</button>
  </div>'''
nouveau1 = '''<div id="chat">
    <div class="msg orcaas" data-i18n="bienvenue">Bonjour, je suis ORCAAS. Posez-moi une question sur l'etat du site, mes dernieres actions, ou les resultats obtenus.</div>
  </div>
  <div id="input-zone">
    <input type="text" id="question" placeholder="Posez votre question..." autocomplete="off" data-i18n-placeholder="placeholder_question" />
    <button id="send" data-i18n="bouton_envoyer">Envoyer</button>
  </div>'''

if 'data-i18n="bienvenue"' in contenu:
    print("SKIP (partie 1) : deja present")
elif ancien1 not in contenu:
    print("ERREUR (partie 1) : ancre chat non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("OK (partie 1/4)")

ancien2 = '''  <div id="barre-filtre">
    <label>Du <input type="date" id="date-debut"></label>
    <label>au <input type="date" id="date-fin"></label>
    <button id="appliquer-filtre" onclick="rechargerAvecFiltre()">Appliquer</button>
    <span id="periode-affichee"></span>
  </div>
  <div class="carte">
    <h2>Top pages par impressions (GSC, periode selectionnee)</h2>
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
nouveau2 = '''  <div id="barre-filtre">
    <label><span data-i18n="label_du">Du</span> <input type="date" id="date-debut"></label>
    <label><span data-i18n="label_au">au</span> <input type="date" id="date-fin"></label>
    <button id="appliquer-filtre" onclick="rechargerAvecFiltre()" data-i18n="bouton_appliquer">Appliquer</button>
    <span id="periode-affichee"></span>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_pages">Top pages par impressions (GSC, periode selectionnee)</h2>
    <canvas id="chartPages"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_briefs">Corrections ORCAAS par type de probleme</h2>
    <canvas id="chartBriefs"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_evals">Evaluations d'impact par verdict</h2>
    <canvas id="chartEvals"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_opportunites">Top 10 opportunites SEO (score)</h2>
    <canvas id="chartOpportunites"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_rankmath">Couverture RankMath (mot-cle cible)</h2>
    <canvas id="chartRankmath"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_audit">Sante technique du site (495 pages)</h2>
    <canvas id="chartAudit"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_leads">Leads par outil (tous canaux)</h2>
    <canvas id="chartLeads"></canvas>
  </div>
  <div class="carte">
    <h2 data-i18n="titre_publications">Publications par silo</h2>
    <canvas id="chartPublications"></canvas>
  </div>
</div>'''

if 'data-i18n="titre_pages"' in contenu:
    print("SKIP (partie 2) : deja present")
elif ancien2 not in contenu:
    print("ERREUR (partie 2) : ancre dashboard non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("OK (partie 2/4)")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
