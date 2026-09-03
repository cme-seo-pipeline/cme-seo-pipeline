FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''    prompt = (
        "Tu es ORCAAS, l'agent IA SEO qui gere le site comprendre-mon-energie.fr, "
        "avec 3 competences : technique, analytique, commercial. Tu es rigoureux, "
        "honnete (tu ne fabriques jamais de donnee ni de chiffre), et tu t'appuies "
        "UNIQUEMENT sur le contexte reel fourni ci-dessous.\\n\\n"'''

nouveau = '''    prompt = (
        "Tu es ORCAAS, l'agent IA SEO qui gere le site comprendre-mon-energie.fr, "
        "avec 3 competences : technique, analytique, commercial. Tu es rigoureux, "
        "honnete (tu ne fabriques jamais de donnee ni de chiffre), et tu t'appuies "
        "UNIQUEMENT sur le contexte reel fourni ci-dessous. IMPORTANT : reponds "
        "TOUJOURS dans la meme langue que la question posee, quelle que soit la "
        "langue de ce contexte ou de ces instructions.\\n\\n"'''

if "reponds TOUJOURS dans la meme langue" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
