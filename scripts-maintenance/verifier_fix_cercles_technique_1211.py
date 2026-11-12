"""
CME — Verification VISUELLE + au pixel (lecture seule, ne touche a rien en
prod) du correctif du 12/11/2026 sur generer_technique_svg() (pipeline.py,
commit a792110) : cercles 52/44 -> 58/50 + budget de texte uniformise a
120px, en reponse au signalement operateur ("le premier schema comporte
encore des textes qui sortent des petits cercles").

Rend REELLEMENT le schema via cairosvg (comme en prod, pas un calcul
theorique) avec des composants representatifs (noms/descriptions de
longueur realiste, dont le cas le plus long deja identifie comme
provoquant un depassement avec les anciens reglages), puis mesure au
pixel le depassement eventuel du texte "desc" hors du cercle qui
l'entoure -- meme methodologie (fenetre de scan serree par cercle,
heuristique min(r,g,b)<200 ou saturation>60) que celle utilisee pour
confirmer le bug signale par l'operateur sur l'image en prod.

Encode l'image rendue en base64 dans ce log (le seul canal lisible par
Claude Code depuis ce sandbox, voir CLAUDE.md) pour une verification
visuelle en plus de la mesure numerique.

LECTURE SEULE.
"""
import sys
import os
import base64
from unittest import mock

# Modules externes non necessaires pour cette fonction pure (pas de reseau,
# pas de BigQuery) -- mockes avant import pour isoler generer_technique_svg()
# sans toucher a la prod, meme pattern que le test local du 12/11 pour
# generer_comparatif_svg().
for modname in ["google", "google.cloud", "google.cloud.bigquery", "google.oauth2",
                "google.auth", "requests", "bs4", "anthropic"]:
    sys.modules[modname] = mock.MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
try:
    import pipeline
except Exception as e:
    sys.exit(f"Import de pipeline/pipeline.py impossible : {e}")

try:
    import cairosvg
except Exception as e:
    sys.exit(f"cairosvg indisponible sur ce runner : {e}")

from PIL import Image


def section(titre):
    print("\n" + "=" * 100)
    print(titre)
    print("=" * 100)


def est_pixel_contenu(px):
    r, g, b = px[0], px[1], px[2]
    mn = min(r, g, b)
    sat = max(r, g, b) - mn
    return mn < 200 or sat > 60


def mesurer_depassement(img, cx, cy, rayon, fenetre_x=100):
    """Scanne une fenetre etroite autour du centre (cx,cy) et renvoie le
    depassement en px du contenu (texte/trait) hors du rayon donne, a
    gauche et a droite. Fenetre volontairement etroite pour ne pas capter
    les composants voisins (meme piege que lors de la premiere mesure, le
    12/11, qui scannait toute la largeur de l'image)."""
    largeur, hauteur = img.size
    x0 = max(0, cx - fenetre_x)
    x1 = min(largeur, cx + fenetre_x)
    gauche_min = cx
    droite_max = cx
    for y in range(max(0, cy - rayon - 5), min(hauteur, cy + rayon + 10)):
        for x in range(x0, x1):
            if est_pixel_contenu(img.getpixel((x, y))):
                gauche_min = min(gauche_min, x)
                droite_max = max(droite_max, x)
    depassement_gauche = max(0, (cx - rayon) - gauche_min)
    depassement_droite = max(0, droite_max - (cx + rayon))
    return depassement_gauche, depassement_droite, gauche_min, droite_max


def main():
    section("1. Rendu REEL via generer_technique_svg() (code commit a792110, rayon 58, budget 120)")
    # 5 composants -- meme layout (nb=5, le plus contraint, distance mini
    # 130px entre centres) et des descriptions de longueur realiste, dont
    # le cas le plus long deja identifie dans le test arithmetique local
    # comme le plus proche de la limite.
    composants = [
        {"icone": "🔧", "nom": "Bouteille de gaz", "desc": "Raccordement étanche obligatoire"},
        {"icone": "🔩", "nom": "Détendeur de pression", "desc": "Vérification visuelle du joint"},
        {"icone": "🔗", "nom": "Tuyau raccord", "desc": "Contrôle de l'étanchéité au savon"},
        {"icone": "🛡️", "nom": "Support / Chaîne", "desc": "Remplacement tous les 5 ans"},
        {"icone": "👷", "nom": "Valve de sécurité", "desc": "Installation par un professionnel agréé"},
    ]
    svg_bytes = pipeline.generer_technique_svg(
        "Installer une bouteille de gaz : les éléments clés", composants, "#1A73E8", index=0
    )
    print(f"SVG genere : {len(svg_bytes)} octets")

    png_bytes = cairosvg.svg2png(bytestring=svg_bytes, output_width=680)
    print(f"PNG rendu : {len(png_bytes)} octets")

    tmp_path = "/tmp/technique_test_1211.png"
    with open(tmp_path, "wb") as f:
        f.write(png_bytes)
    img = Image.open(tmp_path).convert("RGB")
    print(f"Dimensions : {img.size}")

    section("2. Mesure au pixel du depassement (rayon reel = 58, meme methodologie que le diagnostic initial)")
    # Positions nb=5 (voir pipeline.py) : [(110,160),(290,160),(470,160),(200,290),(480,290)]
    positions = [(110, 160), (290, 160), (470, 160), (200, 290), (480, 290)]
    # SVG_RAYON_CERCLE_TECHNIQUE est une variable LOCALE a la fonction (pas
    # un global de module) -- valeur reprise ici telle que committee dans
    # a792110, pas introspectee dynamiquement.
    rayon = 58
    print(f"Rayon utilise pour la mesure : {rayon}")
    pire = 0
    for i, (cx, cy) in enumerate(positions):
        dg, dd, gmin, dmax = mesurer_depassement(img, cx, cy, rayon)
        pire = max(pire, dg, dd)
        tag = "✅ aucun depassement" if (dg == 0 and dd == 0) else f"❌ DEPASSEMENT gauche={dg}px droite={dd}px"
        print(f"  Composant {i+1} ({composants[i]['nom']!r}) centre=({cx},{cy}) -- {tag}")

    section("3. Verdict")
    if pire == 0:
        print("✅ 0px de depassement mesure sur les 5 composants -- correctif confirme par un rendu REEL cairosvg.")
    else:
        print(f"❌ Depassement residuel mesure : {pire}px -- le correctif ne suffit pas, a reexaminer.")

    section("4. Image rendue, encodee en base64 (verification visuelle)")
    b64 = base64.b64encode(png_bytes).decode("ascii")
    print(f"\n--- DEBUT_IMAGE type=technique_apres_correctif taille_octets={len(png_bytes)} ---")
    for i in range(0, len(b64), 2000):
        print(b64[i:i + 2000])
    print("--- FIN_IMAGE ---")

    section("FIN")


if __name__ == "__main__":
    main()
