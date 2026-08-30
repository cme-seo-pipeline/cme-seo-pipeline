FICHIER = "pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancre = "@app.route('/synchroniser-clarity', methods=['POST'])"

nouvelle_route = '''@app.route('/test-ip-sortante', methods=['GET'])
def test_ip_sortante():
    """
    VERIFICATION CHANTIER RESEAU : confirme l'IP sortante reelle utilisee
    par Cloud Run, pour valider le connecteur VPC + Cloud NAT. Endpoint
    temporaire de diagnostic (pas destine a rester en production).
    """
    try:
        r = requests.get("https://ifconfig.me", timeout=10)
        return jsonify({"ip_sortante": r.text.strip()}), 200
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


'''

if "test_ip_sortante" in contenu:
    print("⏭️  PATCH (test IP sortante) : deja present, ignore")
elif ancre not in contenu:
    print("❌ PATCH (test IP sortante) : ancre non trouvee")
else:
    contenu = contenu.replace(ancre, nouvelle_route + ancre, 1)
    print("✅ PATCH (test IP sortante) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
