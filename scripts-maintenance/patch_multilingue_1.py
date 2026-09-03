FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien1 = '''  #periode-affichee { font-size: 13px; color: #64748b; margin-left: auto; }'''
nouveau1 = '''  #periode-affichee { font-size: 13px; color: #64748b; margin-left: auto; }
  #bouton-langue { background: transparent; border: 1px solid #334155; color: #94a3b8; padding: 5px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; margin-left: auto; }
  #bouton-langue:hover { background: #1e293b; color: #e2e8f0; }'''

if "#bouton-langue" in contenu:
    print("SKIP (partie 1) : deja present")
elif ancien1 not in contenu:
    print("ERREUR (partie 1) : ancre CSS non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("OK (partie 1/6)")

ancien2 = '''  <span class="badge">SEO Specialiste IA</span>
  <nav>
    <button id="onglet-chat" class="actif" onclick="afficherOnglet('chat')">Chat</button>
    <button id="onglet-dashboard" onclick="afficherOnglet('dashboard')">Dashboard</button>
  </nav>
</header>'''
nouveau2 = '''  <span class="badge" data-i18n="badge">SEO Specialiste IA</span>
  <nav>
    <button id="onglet-chat" class="actif" onclick="afficherOnglet('chat')" data-i18n="onglet_chat">Chat</button>
    <button id="onglet-dashboard" onclick="afficherOnglet('dashboard')" data-i18n="onglet_dashboard">Dashboard</button>
  </nav>
  <button id="bouton-langue" onclick="changerLangue()">EN</button>
</header>'''

if 'id="bouton-langue" onclick' in contenu:
    print("SKIP (partie 2) : deja present")
elif ancien2 not in contenu:
    print("ERREUR (partie 2) : ancre header non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("OK (partie 2/6)")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde (etape 1/2) :", FICHIER)
