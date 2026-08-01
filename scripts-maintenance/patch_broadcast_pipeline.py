FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Configuration (URL client-api + cle partagee)
# ============================================================
ancre1 = '''FACEBOOK_CONFIG = {
    "page_id": os.environ.get("FACEBOOK_PAGE_ID", ""),
    "access_token": os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", ""),
}'''

if ancre1 not in contenu:
    print("❌ PATCH 1 (config) : ancre non trouvee")
else:
    nouveau1 = ancre1 + '''
CLIENT_API_URL = os.environ.get("CLIENT_API_URL", "https://cme-client-api-217943559750.europe-west1.run.app")
BROADCAST_API_KEY = os.environ.get("BROADCAST_API_KEY", "")'''
    if "CLIENT_API_URL" in contenu:
        print("⏭️  PATCH 1 (config) : deja present, ignore")
    else:
        contenu = contenu.replace(ancre1, nouveau1)
        print("✅ PATCH 1 (config) : CLIENT_API_URL + BROADCAST_API_KEY ajoutes")

# ============================================================
# PATCH 2 — Fonction de notification
# ============================================================
ancre2 = "def publier_tous_facebook(df_publications, client_bq, config, facebook_config):"

fonction_notif = '''def notifier_nouveaux_articles(df_publications, config):
    """Notifie tous les utilisateurs de l'app mobile ayant active les
    notifications qu'un nouveau lot d'articles vient d'etre publie.
    Un seul envoi groupe par run, pas un par article (evite le spam)."""
    nb = len(df_publications)
    if nb == 0 or not BROADCAST_API_KEY:
        return
    if nb == 1:
        corps = "1 nouvel article vient d'etre publie"
    else:
        corps = f"{nb} nouveaux articles viennent d'etre publies"
    try:
        r = requests.post(
            f"{CLIENT_API_URL}/notifications/broadcast",
            json={
                "title": "Nouveaux articles disponibles",
                "body": corps,
                "data": {"type": "nouveaux_articles"}
            },
            headers={"X-Broadcast-Key": BROADCAST_API_KEY, "Content-Type": "application/json"},
            timeout=15
        )
        if r.status_code == 200:
            print(f"  📱 Notification push envoyee : {r.json().get('count', 0)} appareils")
        else:
            print(f"  ⚠️ Notification push echouee : HTTP {r.status_code}")
    except Exception as e:
        print(f"  ⚠️ Erreur notification push : {e}")


'''

if "notifier_nouveaux_articles" in contenu:
    print("⏭️  PATCH 2 (fonction notif) : deja present, ignore")
elif ancre2 not in contenu:
    print("❌ PATCH 2 (fonction notif) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre2, fonction_notif + ancre2, 1)
    print("✅ PATCH 2 (fonction notif) : notifier_nouveaux_articles ajoutee")

# ============================================================
# PATCH 3 — Appel en fin de run_pipeline
# ============================================================
ancre3 = "    publier_tous_facebook(df_publications, client_bq, CONFIG, FACEBOOK_CONFIG)"

if "notifier_nouveaux_articles(df_publications, CONFIG)" in contenu:
    print("⏭️  PATCH 3 (appel notif) : deja present, ignore")
elif ancre3 not in contenu:
    print("❌ PATCH 3 (appel notif) : ancre non trouvee")
else:
    contenu = contenu.replace(
        ancre3,
        ancre3 + "\n    notifier_nouveaux_articles(df_publications, CONFIG)",
        1
    )
    print("✅ PATCH 3 (appel notif) : ajoute apres publier_tous_facebook")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
