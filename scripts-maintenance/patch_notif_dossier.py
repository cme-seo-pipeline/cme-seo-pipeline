FICHIER = "client-api/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Fonction de notification ciblee + libelles de statut
# ============================================================
ancre1 = "@app.route('/admin/leads/<lead_owner_uid>/<lead_id>/status', methods=['PATCH', 'OPTIONS'])"

bloc_notif = '''def envoyer_notification_utilisateur(uid, titre, corps, payload_data=None):
    """Envoie une notification push ciblee a un utilisateur precis. Appel
    interne (pas besoin de cle partagee, contrairement au broadcast utilise
    par le pipeline externe)."""
    try:
        doc = db.collection('users').document(uid).get()
        if not doc.exists:
            return
        jetons = doc.to_dict().get('expo_push_tokens', [])
        if not jetons:
            return
        messages = [
            {"to": jeton, "title": titre, "body": corps, "data": payload_data or {}}
            for jeton in jetons
        ]
        requests.post(
            "https://exp.host/--/api/v2/push/send",
            json=messages,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=15
        )
    except Exception:
        pass


STATUT_LABELS_NOTIF = {
    'nouveau': "a ete remis en attente",
    'en_cours': "est maintenant en cours de traitement",
    'documents_manquants': "necessite des documents supplementaires",
    'traite': "a ete traite",
    'abandonne': "a ete cloture",
}


'''

if "envoyer_notification_utilisateur" in contenu:
    print("⏭️  PATCH 1 (fonction notif ciblee) : deja present, ignore")
elif ancre1 not in contenu:
    print("❌ PATCH 1 (fonction notif ciblee) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre1, bloc_notif + ancre1, 1)
    print("✅ PATCH 1 (fonction notif ciblee) : ajoutee")

# ============================================================
# PATCH 2 — Declenchement apres mise a jour du statut
# ============================================================
ancre2 = '''        lead_ref.update({
            'statut': nouveau_statut,
            'derniere_maj': firestore.SERVER_TIMESTAMP
        })
        return _cors(jsonify({"status": "ok"})), 200'''

nouveau2 = '''        lead_ref.update({
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
        return _cors(jsonify({"status": "ok"})), 200'''

if "STATUT_LABELS_NOTIF.get(nouveau_statut" in contenu:
    print("⏭️  PATCH 2 (declenchement) : deja present, ignore")
elif ancre2 not in contenu:
    print("❌ PATCH 2 (declenchement) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre2, nouveau2, 1)
    print("✅ PATCH 2 (declenchement) : notification ajoutee apres maj statut")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
