FICHIER = "client-api/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Libelles d'outils (juste apres STATUT_LABELS_NOTIF)
# ============================================================
ancre1 = """STATUT_LABELS_NOTIF = {
    'nouveau': "a ete remis en attente",
    'en_cours': "est maintenant en cours de traitement",
    'documents_manquants': "necessite des documents supplementaires",
    'traite': "a ete traite",
    'abandonne': "a ete cloture",
}"""

nouveau1 = ancre1 + '''

TOOL_LABELS_NOTIF = {
    'solaire': "Solaire",
    'comparateur-energie': "Comparateur Énergie",
    'aides-renovation': "Aides Rénovation",
    'rendez-vous-expert': "Rendez-vous expert",
}'''

if "TOOL_LABELS_NOTIF" in contenu:
    print("⏭️  PATCH 1 (libelles outils) : deja present, ignore")
elif ancre1 not in contenu:
    print("❌ PATCH 1 (libelles outils) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre1, nouveau1, 1)
    print("✅ PATCH 1 (libelles outils) : ajoutes")

# ============================================================
# PATCH 2 — Recuperer le lead AVANT modification pour connaitre
# son outil, et enrichir le message + les donnees de la notif
# ============================================================
ancien2 = '''    try:
        lead_ref = db.collection('users').document(lead_owner_uid).collection('leads').document(lead_id)
        lead_ref.update({
            'statut': nouveau_statut,
            'derniere_maj': firestore.SERVER_TIMESTAMP
        })
        libelle = STATUT_LABELS_NOTIF.get(nouveau_statut, "a ete mis a jour")
        envoyer_notification_utilisateur(
            lead_owner_uid,
            "Mise a jour de votre dossier",
            f"Votre dossier {libelle}.",
            {"type": "statut_dossier", "lead_id": lead_id, "statut": nouveau_statut}
        )
        return _cors(jsonify({"status": "ok"})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500'''

nouveau2 = '''    try:
        lead_ref = db.collection('users').document(lead_owner_uid).collection('leads').document(lead_id)
        lead_avant = lead_ref.get()
        outil = lead_avant.to_dict().get('tool', '') if lead_avant.exists else ''
        outil_libelle = TOOL_LABELS_NOTIF.get(outil, "")
        lead_ref.update({
            'statut': nouveau_statut,
            'derniere_maj': firestore.SERVER_TIMESTAMP
        })
        libelle = STATUT_LABELS_NOTIF.get(nouveau_statut, "a ete mis a jour")
        prefixe = f"Votre dossier {outil_libelle}" if outil_libelle else "Votre dossier"
        envoyer_notification_utilisateur(
            lead_owner_uid,
            "Mise a jour de votre dossier",
            f"{prefixe} {libelle}.",
            {
                "type": "statut_dossier",
                "lead_id": lead_id,
                "statut": nouveau_statut,
                "tool": outil,
                "tool_libelle": outil_libelle
            }
        )
        return _cors(jsonify({"status": "ok"})), 200
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500'''

if ancien2 not in contenu:
    print("❌ PATCH 2 (enrichissement notif) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (enrichissement notif) : nom d'outil + donnees structurees ajoutes")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
