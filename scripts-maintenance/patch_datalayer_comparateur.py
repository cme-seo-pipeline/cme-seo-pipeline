FICHIER = "wordpress-plugins/comparateur-energie/comparateur-energie.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = """      details:{energie:ctx.energie||'',fournisseur:ctx.fournisseur||'',offre:ctx.offre||'',kwh:ctx.kwh||0,option_tarifaire:ctx.option_tarifaire||''}
    };
    if(window.CME_APP_TOKEN){"""

nouveau = """      details:{energie:ctx.energie||'',fournisseur:ctx.fournisseur||'',offre:ctx.offre||'',kwh:ctx.kwh||0,option_tarifaire:ctx.option_tarifaire||''}
    };
    // CHANTIER G.1 : evenement de conversion fiable, envoye au moment reel
    // du succes — independant de QUEL bouton/CTA a amene le visiteur ici
    // (article, footer, menu flottant...), et independant du statut app.
    window.dataLayer=window.dataLayer||[];
    window.dataLayer.push({
      'event':'generate_lead',
      'tool':'comparateur-energie',
      'value':ctx.economie||0,
      'source_post_id':srcPost
    });
    if(window.CME_APP_TOKEN){"""

if "CHANTIER G.1" in contenu:
    print("SKIP : deja present")
elif ancien not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("OK : patch applique")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
