"""
CME — Diagnostic (lecture seule) : pourquoi le depassement mesure par
diagnostiquer_overflow_schemas_svg.py reste identique au octet AVANT et
APRES le bundling de Liberation Sans (pipeline/assets/fonts/, commit
1bdc241, 11/11/2026), alors que fc-list confirme desormais la police
installee et enregistree sur le runner.

Hypothese a trancher : cairosvg ne respecte peut-etre pas font-family
de la meme facon que fc-list/fontconfig le suggere (guillemets autour
du nom, ordre de fallback, ou moteur de rendu texte different de celui
que fontconfig utilise pour lister les polices). Mesure le texte REEL
rendu par cairosvg pour plusieurs variantes de declaration font-family,
et le compare a la largeur mesuree par PIL (ImageFont.getlength) avec
le vrai fichier TTF Liberation Sans -- les deux doivent correspondre
pour que ajuster_texte_svg() (qui mesure via PIL) soit fiable.

LECTURE SEULE -- aucun secret necessaire, ne touche ni WordPress ni
BigQuery.
"""
import os
import sys

try:
    import cairosvg
except ImportError:
    sys.exit("❌ cairosvg manquant")

try:
    from PIL import Image, ImageFont
except ImportError:
    sys.exit("❌ Pillow manquant")

OUT_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(OUT_DIR, exist_ok=True)

FONT_REG = os.path.join(os.path.dirname(__file__), "..", "pipeline", "assets", "fonts", "LiberationSans-Regular.ttf")
TEXTE = "Disjoncteur differentiel protege"
TAILLE = 14


def mesurer_pil():
    f = ImageFont.truetype(FONT_REG, TAILLE)
    return f.getlength(TEXTE)


def mesurer_cairosvg(font_family_css):
    larg, haut = 900, 60
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{larg}" height="{haut}">
  <rect width="{larg}" height="{haut}" fill="white"/>
  <text x="10" y="35" font-family="{font_family_css}" font-size="{TAILLE}" fill="black">{TEXTE}</text>
</svg>'''
    png_bytes = cairosvg.svg2png(bytestring=svg.encode("utf-8"), dpi=150, output_width=larg)
    chemin = os.path.join(OUT_DIR, "diag_police_" + "".join(c if c.isalnum() else "_" for c in font_family_css) + ".png")
    with open(chemin, "wb") as fh:
        fh.write(png_bytes)
    img = Image.open(chemin).convert("RGB")
    # cairosvg rend a dpi=150 pour un SVG dont le viewport logique est
    # en px CSS (96dpi) -- le facteur d'echelle reel vient de output_width
    # demande vs largeur logique du SVG (ici identiques : 900 -> 900),
    # donc pas de mise a l'echelle supplementaire a appliquer ici.
    gauche, droite = None, None
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = img.getpixel((x, y))
            if not (r > 245 and g > 245 and b > 245):
                if gauche is None or x < gauche:
                    gauche = x
                if droite is None or x > droite:
                    droite = x
    largeur = (droite - gauche) if (gauche is not None and droite is not None) else None
    return largeur, chemin


def main():
    import subprocess
    print("cairosvg version :", getattr(cairosvg, "__version__", "?"))
    try:
        import cairocffi
        print("cairocffi version :", getattr(cairocffi, "VERSION", "?"))
    except ImportError:
        print("cairocffi : non importable directement (normal si cairosvg l'encapsule)")
    try:
        fonts = subprocess.run(["fc-list", ":family"], capture_output=True, text=True, timeout=10).stdout
        print("Liberation dans fc-list :", "Liberation Sans" in fonts)
    except Exception as e:
        print("fc-list indisponible :", e)
    print()

    largeur_pil = mesurer_pil()
    print(f"Largeur mesuree par PIL (vrai TTF Liberation Sans Regular, {TAILLE}px) : {largeur_pil:.1f}px")
    print()

    variantes = [
        "Liberation Sans",
        "'Liberation Sans'",
        "\"Liberation Sans\"",
        "'Liberation Sans', Arial, sans-serif",
        "Arial",
        "sans-serif",
        "DejaVu Sans",
    ]
    for v in variantes:
        try:
            largeur, chemin = mesurer_cairosvg(v)
            ecart = (largeur - largeur_pil) if largeur else None
            print(f"  font-family=\"{v}\" -> largeur rendue cairosvg = {largeur}px  (ecart vs PIL Liberation : {ecart:+.1f}px)" if largeur else f"  font-family=\"{v}\" -> aucun pixel detecte")
        except Exception as e:
            print(f"  font-family=\"{v}\" -> ERREUR : {e}")


if __name__ == "__main__":
    main()
