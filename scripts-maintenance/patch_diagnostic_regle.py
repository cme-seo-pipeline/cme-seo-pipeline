FICHIER = "pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH A — Diagnostic + injection plus directive
# ============================================================
ancien_a = '''    donnees_officielles_str = ""
    if client_bq is not None:
        donnees = recuperer_donnees_officielles(brief.get('silo', ''), brief.get('sous_silo', ''), client_bq)
        if donnees:
            donnees_officielles_str = f"\\nDONNÉES OFFICIELLES ACTUELLES (source : CRE/ANAH, verifiees) :\\n{donnees}\\n"'''

nouveau_a = '''    donnees_officielles_str = ""
    if client_bq is not None:
        donnees = recuperer_donnees_officielles(brief.get('silo', ''), brief.get('sous_silo', ''), client_bq)
        print(f"  🔎 Donnees officielles pour {brief.get('silo')} | {brief.get('sous_silo')} : {'TROUVEES' if donnees else 'aucune'}")
        if donnees:
            donnees_officielles_str = f"\\nDONNÉES OFFICIELLES ACTUELLES (source : CRE/ANAH, vérifiées — utilise IMPÉRATIVEMENT ces valeurs exactes dans au moins un exemple chiffré concret) :\\n{donnees}\\n"'''

if "🔎 Donnees officielles pour" in contenu:
    print("⏭️  PATCH A (diagnostic + injection) : deja present, ignore")
elif ancien_a not in contenu:
    print("❌ PATCH A (diagnostic + injection) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien_a, nouveau_a, 1)
    print("✅ PATCH A (diagnostic + injection) : ajoute")

# ============================================================
# PATCH B — Regle renforcee
# ============================================================
ancien_b = """5. Chiffres précis (prix, taux, tarifs) : utilise EXCLUSIVEMENT les valeurs de la section DONNÉES OFFICIELLES ACTUELLES ci-dessus si elle est présente. INTERDIT d'inventer un prix, un taux ou une offre commerciale attribuée à une marque réelle (EDF, Engie, TotalEnergies...). Si aucune donnée officielle n'est fournie pour un point précis, reste général (ex: "les tarifs varient selon les fournisseurs") plutôt que d'inventer un chiffre ou un nom de marque avec un prix associé."""

nouveau_b = """5. Chiffres précis (prix, taux, tarifs) : SI la section DONNÉES OFFICIELLES ACTUELLES est présente ci-dessus, tu DOIS OBLIGATOIREMENT reprendre ces valeurs exactes dans au moins un exemple chiffré concret de l'article — ne construis JAMAIS un exemple "simplifié" ou fictif avec un prix inventé si une donnée officielle existe pour ce sujet. INTERDIT d'inventer un prix, un taux ou une offre commerciale attribuée à une marque réelle (EDF, Engie, TotalEnergies...). Si aucune donnée officielle n'est fournie pour un point précis, reste général (ex: "les tarifs varient selon les fournisseurs") plutôt que d'inventer un chiffre."""

if "tu DOIS OBLIGATOIREMENT reprendre ces valeurs exactes" in contenu:
    print("⏭️  PATCH B (regle renforcee) : deja present, ignore")
elif ancien_b not in contenu:
    print("❌ PATCH B (regle renforcee) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien_b, nouveau_b, 1)
    print("✅ PATCH B (regle renforcee) : ajoutee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
