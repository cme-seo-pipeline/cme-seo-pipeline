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
pixel le depassement eventuel du texte "nom"/"desc" hors du cercle qui
l'entoure -- UNIQUEMENT sur les bandes horizontales ou ce texte est
reellement dessine (y=cy+8 pour "nom", y=cy+22 pour "desc"), en
comparant a la courbe reelle de l'anneau du cercle (rayon + la moitie du
stroke-width, pas un rayon plat).

Piege trouve et corrige le 12/11/2026 (premiere version de ce script) :
scanner toute la hauteur du cercle contre un rayon plat compte a tort
l'anneau du cercle lui-meme (son bord EXTERIEUR reel est a
rayon + stroke/2, pas rayon) comme un "depassement de texte" sur
presque toute la hauteur du cercle -- confirme en inspectant l'image
ligne par ligne (le "depassement" mesure etait un 1-2px QUASI UNIFORME
de cy-11 a cy+10, signature typique d'un trait de cercle, pas de texte,
qui a des bords irreguliers).

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


import math

STROKE_ANNEAU = 2.5  # stroke-width du cercle exterieur dans generer_technique_svg()


def mesurer_depassement_ligne(img, cx, cy, rayon, y_offset, demi_hauteur=4, fenetre_x=100):
    """Mesure le depassement de TEXTE hors du cercle, sur une bande
    horizontale etroite centree sur y = cy + y_offset (une ligne de texte
    precise : nom a y_offset=8, desc a y_offset=22 dans generer_technique_svg()).

    Piege trouve et corrige le 12/11/2026 en analysant ligne par ligne une
    image reellement rendue : une premiere version de ce script scannait
    toute la hauteur du cercle (cy-rayon a cy+rayon) et mesurait a tort un
    "depassement" de 1-2px QUASI UNIFORME sur presque toute cette hauteur --
    pas du texte, mais l'anneau du cercle lui-meme (stroke-width=2.5,
    centre sur le rayon nominal, donc son bord EXTERIEUR reel est a
    rayon + 1.25px, pas rayon). La borne de comparaison est donc ici la
    courbe reelle de l'anneau (cercle de rayon rayon+1.25), pas un rayon
    plat -- jamais un flux de pixels "normal" au trait du cercle n'est
    compte comme depassement de texte.
    """
    largeur, hauteur = img.size
    rayon_anneau_ext = rayon + STROKE_ANNEAU / 2
    gauche_min, droite_max = None, None
    y0 = max(0, cy + y_offset - demi_hauteur)
    y1 = min(hauteur, cy + y_offset + demi_hauteur)
    for y in range(y0, y1):
        dy = y - cy
        if abs(dy) >= rayon_anneau_ext:
            borne = rayon  # hors de l'anneau, le rayon nominal suffit
        else:
            borne = math.sqrt(rayon_anneau_ext ** 2 - dy ** 2)
        for x in range(max(0, cx - fenetre_x), min(largeur, cx + fenetre_x)):
            if not est_pixel_contenu(img.getpixel((x, y))):
                continue
            if x < cx - borne:
                gauche_min = x if gauche_min is None else min(gauche_min, x)
            if x > cx + borne:
                droite_max = x if droite_max is None else max(droite_max, x)
    depassement_gauche = 0 if gauche_min is None else (cx - rayon) - gauche_min
    depassement_droite = 0 if droite_max is None else droite_max - (cx + rayon)
    return max(0, depassement_gauche), max(0, depassement_droite)


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

    section("2. Mesure au pixel du depassement de TEXTE (rayon reel = 58), ligne par ligne")
    # Positions nb=5 (voir pipeline.py) : [(110,160),(290,160),(470,160),(200,290),(480,290)]
    positions = [(110, 160), (290, 160), (470, 160), (200, 290), (480, 290)]
    # SVG_RAYON_CERCLE_TECHNIQUE est une variable LOCALE a la fonction (pas
    # un global de module) -- valeur reprise ici telle que committee dans
    # a792110, pas introspectee dynamiquement.
    rayon = 58
    print(f"Rayon utilise pour la mesure : {rayon}")
    pire = 0
    for i, (cx, cy) in enumerate(positions):
        dg_nom, dd_nom = mesurer_depassement_ligne(img, cx, cy, rayon, y_offset=8)
        dg_desc, dd_desc = mesurer_depassement_ligne(img, cx, cy, rayon, y_offset=22)
        pire = max(pire, dg_nom, dd_nom, dg_desc, dd_desc)
        tag_nom = "✅" if (dg_nom == 0 and dd_nom == 0) else f"❌ gauche={dg_nom}px droite={dd_nom}px"
        tag_desc = "✅" if (dg_desc == 0 and dd_desc == 0) else f"❌ gauche={dg_desc}px droite={dd_desc}px"
        print(f"  Composant {i+1} ({composants[i]['nom']!r}) centre=({cx},{cy}) -- "
              f"ligne nom: {tag_nom} -- ligne desc: {tag_desc}")

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
