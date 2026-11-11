"""
CME — Diagnostic (lecture seule) cible : pour chaque texte reellement
tronque par ajuster_texte_svg() dans les 3 vrais appels de
generer_technique_svg() (titre schema technique du diagnostic
precedent), isole dans une image a part (une seule ligne de texte, pas
de bandes qui peuvent se chevaucher entre nom/desc comme dans
diagnostiquer_overflow_schemas_svg.py) la largeur REELLEMENT rendue par
cairosvg du texte TEL QUE RENVOYE par la fonction, et la compare au
budget qui lui a ete donne. Objectif : trancher si ajuster_texte_svg()
sous-estime vraiment la largeur reelle sur ce runner (mesure PIL trop
optimiste vs rendu cairosvg), ou si le probleme vient d'ailleurs
(chevauchement de bandes de mesure dans le diagnostic precedent,
budget lui-meme insuffisant, etc.).

LECTURE SEULE -- aucun secret necessaire.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))

try:
    import cairosvg
except ImportError:
    sys.exit("❌ cairosvg manquant")

try:
    from PIL import Image
except ImportError:
    sys.exit("❌ Pillow manquant")

from pipeline import ajuster_texte_svg, _mesurer_largeur_texte_svg, SVG_POLICE_FAMILLE

OUT_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(OUT_DIR, exist_ok=True)


def largeur_rendue_cairosvg(texte, taille_px, gras):
    """Rend ce texte seul, sur fond blanc plein (pas de zone transparente
    possible ici), et mesure l'empan horizontal reel du texte rendu."""
    poids = "bold" if gras else "normal"
    larg_canvas = 900
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{larg_canvas}" height="40">
  <rect width="{larg_canvas}" height="40" fill="white"/>
  <text x="10" y="25" font-family="{SVG_POLICE_FAMILLE}" font-size="{taille_px}" font-weight="{poids}" fill="black">{texte}</text>
</svg>'''
    png_bytes = cairosvg.svg2png(bytestring=svg.encode("utf-8"), dpi=150, output_width=larg_canvas)
    img = Image.open(_save_tmp(png_bytes)).convert("RGB")
    gauche, droite = None, None
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = img.getpixel((x, y))
            if not (r > 245 and g > 245 and b > 245):
                if gauche is None or x < gauche:
                    gauche = x
                if droite is None or x > droite:
                    droite = x
    if gauche is None:
        return 0
    # Largeur du texte seul = empan total moins le point de depart (x=10)
    return droite - 10 + 1


_tmp_counter = [0]


def _save_tmp(png_bytes):
    _tmp_counter[0] += 1
    chemin = os.path.join(OUT_DIR, f"_tmp_troncature_{_tmp_counter[0]}.png")
    with open(chemin, "wb") as f:
        f.write(png_bytes)
    return chemin


def tester(label, texte_source, taille_px, gras, budget_px):
    tronque = ajuster_texte_svg(texte_source, taille_px, gras, budget_px)
    largeur_pil_tronque = _mesurer_largeur_texte_svg(tronque, taille_px, gras)
    largeur_pil_source = _mesurer_largeur_texte_svg(texte_source, taille_px, gras)
    largeur_cairo_tronque = largeur_rendue_cairosvg(tronque, taille_px, gras)
    marge = 10
    disponible = budget_px - marge
    print(f"  {label} (budget={budget_px}px, disponible apres marge={disponible}px) :")
    print(f"    texte source       : {texte_source!r}  (largeur PIL si non tronque : {largeur_pil_source:.1f}px)")
    print(f"    texte apres troncature : {tronque!r}")
    print(f"    largeur PIL du texte tronque    : {largeur_pil_tronque:.1f}px  (doit etre <= {disponible}px)")
    print(f"    largeur CAIROSVG du texte tronque : {largeur_cairo_tronque}px  <- CE QUI EST VRAIMENT RENDU EN PROD")
    ecart = largeur_cairo_tronque - disponible
    if ecart > 5:
        print(f"    ⚠️ Le texte tronque DEBORDE QUAND MEME du budget de {ecart:.0f}px au rendu reel (PIL sous-estime la largeur reelle)")
    else:
        print(f"    OK -- le texte tronque rentre bien dans le budget au rendu reel (ecart {ecart:+.0f}px)")
    print()


def main():
    print("=" * 100)
    print("Cas reels de generer_technique_svg (3 composants, budget label = 170px)")
    print("=" * 100)
    largeur_label = 170
    tester("nom (bold, 10px)", "Disjoncteur differentiel", 10, True, largeur_label)
    tester("desc (regular, 9px)", "Protege contre les surtensions electriques", 9, False, largeur_label)
    tester("nom (bold, 10px)", "Compteur communicant Linky", 10, True, largeur_label)
    tester("desc (regular, 9px)", "Releve et transmet votre consommation", 9, False, largeur_label)

    print("=" * 100)
    print("Cas reels de generer_flowchart_svg (largeur_dispo_texte = 550, calculee par le code)")
    print("=" * 100)
    tester("label (bold, 12px)", "Contacter votre fournisseur actuel", 12, True, 550)
    tester("desc (regular, 10px)", "Preparez votre numero de contrat et vos coordonnees", 10, False, 550)

    print("=" * 100)
    print("Cas reel de generer_comparatif_svg (entete colonne, budget = col_w-12 = 248)")
    print("=" * 100)
    tester("entete colonne (bold, 11px)", "Offre Electricite Verte", 11, True, 248)


if __name__ == "__main__":
    main()
