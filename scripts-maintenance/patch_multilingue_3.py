FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''<script>
function afficherOnglet(nom) {'''

nouveau = '''<script>
const TRADUCTIONS = {
  fr: {
    badge: "SEO Specialiste IA", onglet_chat: "Chat", onglet_dashboard: "Dashboard",
    bienvenue: "Bonjour, je suis ORCAAS. Posez-moi une question sur l'etat du site, mes dernieres actions, ou les resultats obtenus.",
    placeholder_question: "Posez votre question...", bouton_envoyer: "Envoyer",
    reflexion: "ORCAAS reflechit...", erreur_inconnue: "Erreur inconnue",
    erreur_connexion: "Erreur de connexion : ", erreur_chargement: "Erreur de chargement : ",
    aucune_donnee: "Aucune donnee disponible",
    label_du: "Du", label_au: "au", bouton_appliquer: "Appliquer", periode_prefixe: "Periode : ",
    titre_pages: "Top pages par impressions (GSC, periode selectionnee)",
    titre_briefs: "Corrections ORCAAS par type de probleme",
    titre_evals: "Evaluations d'impact par verdict",
    titre_opportunites: "Top 10 opportunites SEO (score)",
    titre_rankmath: "Couverture RankMath (mot-cle cible)",
    titre_audit: "Sante technique du site (495 pages)",
    titre_leads: "Leads par outil (tous canaux)",
    titre_publications: "Publications par silo",
  },
  en: {
    badge: "AI SEO Specialist", onglet_chat: "Chat", onglet_dashboard: "Dashboard",
    bienvenue: "Hello, I'm ORCAAS. Ask me about the site's status, my latest actions, or the results obtained.",
    placeholder_question: "Ask your question...", bouton_envoyer: "Send",
    reflexion: "ORCAAS is thinking...", erreur_inconnue: "Unknown error",
    erreur_connexion: "Connection error: ", erreur_chargement: "Loading error: ",
    aucune_donnee: "No data available",
    label_du: "From", label_au: "to", bouton_appliquer: "Apply", periode_prefixe: "Period: ",
    titre_pages: "Top pages by impressions (GSC, selected period)",
    titre_briefs: "ORCAAS corrections by problem type",
    titre_evals: "Impact evaluations by verdict",
    titre_opportunites: "Top 10 SEO opportunities (score)",
    titre_rankmath: "RankMath coverage (target keyword)",
    titre_audit: "Site technical health (495 pages)",
    titre_leads: "Leads by tool (all channels)",
    titre_publications: "Publications by silo",
  }
};

function langueActuelle() {
  return localStorage.getItem('orcaas_langue') || 'fr';
}

function appliquerLangue(lang) {
  const dict = TRADUCTIONS[lang] || TRADUCTIONS.fr;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const cle = el.getAttribute('data-i18n');
    if (dict[cle]) el.textContent = dict[cle];
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const cle = el.getAttribute('data-i18n-placeholder');
    if (dict[cle]) el.placeholder = dict[cle];
  });
  document.getElementById('bouton-langue').textContent = lang === 'fr' ? 'EN' : 'FR';
  document.documentElement.lang = lang;
}

function changerLangue() {
  const actuelle = langueActuelle();
  const nouvelle = actuelle === 'fr' ? 'en' : 'fr';
  localStorage.setItem('orcaas_langue', nouvelle);
  appliquerLangue(nouvelle);
  if (window.dashboardCharge) { window.dashboardCharge = false; chargerDashboard(); }
}

appliquerLangue(langueActuelle());

function afficherOnglet(nom) {'''

if "const TRADUCTIONS" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
