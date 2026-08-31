FICHIER = "wordpress-plugins/simulateur-solaire/simulateur-solaire.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = """      details:{kwc:R.kwc,nb_panneaux:R.nb,production:R.prod,roi:R.roi,co2:R.co2}
    };
    if(window.CME_APP_TOKEN){"""

nouveau = """      details:{kwc:R.kwc,nb_panneaux:R.nb,production:R.prod,roi:R.roi,co2:R.co2}
    };
    // CHANTIER G.1 : evenement de conversion fiable, independant du CTA source
    window.dataLayer=window.dataLayer||[];
    window.dataLayer.push({
      'event':'generate_lead',
      'tool':'solaire',
      'value':R.eco||0,
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
