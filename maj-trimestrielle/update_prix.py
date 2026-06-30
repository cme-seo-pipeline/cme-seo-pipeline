#!/usr/bin/env python3
"""
Script de mise à jour trimestrielle des prix du Comparateur Énergie CME
Usage : python3 update_prix.py
"""
import re
import sys
from datetime import datetime

PHP_FILE = "comparateur-energie.php"


def extraire_offres(content):
    pattern = r"\{id:'([^']+)',\s*logo:'([^']+)',\s*nom:'([^']+)',\s*offre:'([^']+)',\s*type:'([^']+)',\s*prix_kwh:([\d.]+),\s*abo_mois:([\d.]+)"
    matches = re.findall(pattern, content)
    offres = []
    for m in matches:
        offres.append({
            'id': m[0], 'logo': m[1], 'nom': m[2], 'offre': m[3],
            'type': m[4], 'prix_kwh': float(m[5]), 'abo_mois': float(m[6])
        })
    return offres


def main():
    print("MISE A JOUR TRIMESTRIELLE - Comparateur Energie CME")
    print(f"Date : {datetime.now().strftime('%d/%m/%Y')}\n")

    try:
        with open(PHP_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERREUR : fichier {PHP_FILE} introuvable.")
        sys.exit(1)

    offres = extraire_offres(content)
    if not offres:
        print("ERREUR : aucune offre trouvee dans le fichier.")
        sys.exit(1)

    print("=" * 70)
    print(f"PRIX ACTUELS - {len(offres)} offres")
    print("=" * 70)
    for o in offres:
        print(f"  {o['id']:20s} | {o['nom']:18s} | {o['prix_kwh']:.4f}EUR/kWh | abo {o['abo_mois']:.2f}EUR/mois")
    print("=" * 70 + "\n")

    print("Tapez ENTREE pour garder le prix actuel, ou le nouveau prix (ex: 0.2516)\n")

    nouveaux_prix = {}
    for o in offres:
        rep = input(f"{o['nom']} ({o['id']}) - actuel {o['prix_kwh']:.4f} EUR -> nouveau : ").strip()
        if rep:
            try:
                nouveaux_prix[o['id']] = float(rep)
            except ValueError:
                print("   Valeur invalide ignoree")

    if not nouveaux_prix:
        print("\nAucun changement - fichier inchange.")
        return

    for offre_id, nouveau_prix in nouveaux_prix.items():
        pattern = rf"(id:'{re.escape(offre_id)}'.*?prix_kwh:)[\d.]+(,)"
        content = re.sub(pattern, rf"\g<1>{nouveau_prix}\g<2>", content, count=1)

    today = datetime.now().strftime('%d/%m/%Y')
    content = re.sub(r"Tarifs indicatifs au [\d/]+", f"Tarifs indicatifs au {today}", content)

    output_file = f"comparateur-energie-MAJ-{datetime.now().strftime('%Y%m%d')}.php"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n{len(nouveaux_prix)} prix mis a jour")
    print(f"Nouveau fichier cree : {output_file}")
    print("\nProchaine etape : zippez ce fichier et installez-le sur WordPress")


if __name__ == "__main__":
    main()
