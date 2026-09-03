FICHIER = "/home/contact/cme-pipeline/pipeline/pipeline.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien_fonction = "def agent_orcaas_donnees_dashboard(client_bq, date_debut=None, date_fin=None):"

nouvelle_tache = '''def _dash_indexation(client_bq, date_debut, date_fin):
    try:
        df = client_bq.query(f"""
            SELECT coverage_state, COUNT(*) AS nb
            FROM `{PROJECT_ID}.04_pipeline_seo.indexation_google`
            GROUP BY coverage_state ORDER BY nb DESC
        """).to_dataframe()
        liste = [{"etat": r['coverage_state'] or 'Non verifie', "nb": int(r['nb'])} for _, r in df.iterrows()]
        return ("indexation", liste, None)
    except Exception as e:
        return ("indexation", [], f"indexation: {e}")


'''

if "_dash_indexation" in contenu:
    print("SKIP (partie 1) : deja present")
elif ancien_fonction not in contenu:
    print("ERREUR (partie 1) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien_fonction, nouvelle_tache + ancien_fonction, 1)
    print("OK (partie 1/3) : fonction _dash_indexation ajoutee")

ancien_init = '''        "audit_technique": [], "leads_par_outil": [], "publications_par_silo": [],
        "erreur": None,
    }'''
nouveau_init = '''        "audit_technique": [], "leads_par_outil": [], "publications_par_silo": [],
        "indexation": [],
        "erreur": None,
    }'''

if '"indexation": [],' in contenu:
    print("SKIP (partie 2) : deja present")
elif ancien_init not in contenu:
    print("ERREUR (partie 2) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien_init, nouveau_init, 1)
    print("OK (partie 2/3) : champ indexation ajoute au resultat par defaut")

ancien_taches = '''    taches = [_dash_top_pages, _dash_briefs, _dash_evals, _dash_opportunites,
              _dash_rankmath, _dash_audit, _dash_leads, _dash_publications]'''
nouveau_taches = '''    taches = [_dash_top_pages, _dash_briefs, _dash_evals, _dash_opportunites,
              _dash_rankmath, _dash_audit, _dash_leads, _dash_publications,
              _dash_indexation]'''

if "_dash_indexation]" in contenu:
    print("SKIP (partie 3) : deja present")
elif ancien_taches not in contenu:
    print("ERREUR (partie 3) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien_taches, nouveau_taches, 1)
    print("OK (partie 3/3) : tache ajoutee a la liste executee en parallele")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
