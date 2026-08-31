FICHIER = "wordpress-plugins/simulateur-aides/simulateur-aides.php"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = """      details:{profil:ctx.profil||'',travaux:ctx.travaux||'',montant_mpr:ctx.montant_mpr||0,montant_cee:ctx.montant_cee||0,reste_a_charge:ctx.reste_a_charge||0,budget:ctx.budget||0}
    };
    if(window.CME_APP_TOKEN){"""

nouveau = """      details:{profil:ctx.profil||'',travaux:ctx.travaux||'',montant_mpr:ctx.montant_mpr||0,montant_cee:ctx.montant_cee||0,reste_a_charge:ctx.reste_a_charge||0,budget:ctx.budget||0}
    };
    // CHANTIER G.1 : evenement de conversion fiable, independant du CTA source
    window.dataLayer=window.dataLayer||[];
    window.dataLayer.push({
      'event':'generate_lead',
      'tool':'aides-renovation',
      'value':ctx.total_aides||0,
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
