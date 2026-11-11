"""
CME — Diagnostic (lecture seule, aucune ecriture WordPress/BigQuery) du
depassement visuel signale par l'operateur le 11/11/2026 : "les titres a
l'interieur [des schemas generes] depassent souvent leur petit bloc".

Les 3 generateurs de schemas (pipeline/pipeline.py :
generer_flowchart_svg/generer_technique_svg/generer_comparatif_svg)
tronquent chaque texte par NOMBRE DE CARACTERES (ex: nom[:15]) comme
approximation de "ca va rentrer dans la boite" -- mais le nombre de
caracteres n'est PAS proportionnel a la largeur en pixels reellement
rendue. Un test local (Liberation Sans, metriquement equivalent a Arial)
ne montrait AUCUN depassement -- mais le SVG declare font-family="Arial,
sans-serif", et la police reellement substituee sur le runner GitHub
Actions en production (pas le sandbox Claude Code) peut etre differente
(DejaVu Sans, plus large qu'Arial/Liberation, est le repli historique
d'Ubuntu pour "sans-serif"). Ce script tranche en mesurant les PIXELS
REELLEMENT RENDUS par cairosvg sur CE runner -- exactement le meme appel
que la prod (upload_svg_wordpress: cairosvg.svg2png(dpi=150,
output_width=680)) -- au lieu de deviner la police avec un calcul local.

Methode : genere les 3 types de schemas avec des donnees realistes (texte
source volontairement plus long que la limite de caracteres, pour que la
troncature reelle du code s'applique), rend en PNG via cairosvg EXACTEMENT
comme la prod, puis mesure au pixel l'empan horizontal du texte rendu
(pixels non-fond dans la bande verticale ou le texte est dessine) et le
compare a l'empan geometrique de la "boite" (rect ou cercle) prevue par le
code. Flag un depassement reel si le texte rendu deborde le cercle/rect.

LECTURE SEULE -- ne touche ni WordPress ni BigQuery, n'a besoin d'aucun
secret. Sauvegarde les PNG generes dans scripts-maintenance/logs/ (commit
automatique par le bridge) pour inspection visuelle directe si besoin.
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

from pipeline import generer_flowchart_svg, generer_technique_svg, generer_comparatif_svg

OUT_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(OUT_DIR, exist_ok=True)


def rendre_png(svg_bytes, nom_fichier):
    png_bytes = cairosvg.svg2png(bytestring=svg_bytes, dpi=150, output_width=680)
    chemin = os.path.join(OUT_DIR, nom_fichier)
    with open(chemin, "wb") as f:
        f.write(png_bytes)
    # RGBA, pas RGB : les 3 generateurs ne remplissent pas tout le canevas
    # (ex. flowchart n'a pas de rect de fond plein, seul le bandeau titre
    # + les cartes d'etape sont dessines -- "background:#FAFAFA" en CSS
    # sur la racine <svg> n'est PAS une propriete SVG standard et n'est
    # pas honoree par cairosvg). Les zones non dessinees restent donc
    # TRANSPARENTES, et un .convert("RGB") direct les aplatit en noir --
    # un faux "contenu" detecte jusqu'au bord du canevas, sans rapport
    # avec un vrai debordement de texte. Corrige le 11/11/2026 (meme
    # session que le bundling des polices) : traiter alpha~0 comme fond,
    # peu importe la couleur RGB sous-jacente.
    return Image.open(chemin).convert("RGBA"), chemin


def est_pixel_fond(rgba, tolerance=10):
    """Fond = pixel transparent (zone non dessinee par le SVG), OU blanc
    pur, #FAFAFA (250,250,250), ou dans le degrade #F8F9FA -> #E8F0FE
    (schema technique). Tout pixel opaque sensiblement different
    (texte, icone, trait) est considere 'contenu'."""
    r, g, b, a = rgba
    if a < 20:
        return True
    fonds = [(255, 255, 255), (250, 250, 250), (248, 249, 250), (232, 240, 254)]
    return any(abs(r - fr) <= tolerance and abs(g - fg) <= tolerance and abs(b - fb) <= tolerance
               for fr, fg, fb in fonds)


def empan_horizontal_contenu(img, y_min, y_max, x_min_recherche=0, x_max_recherche=None):
    """Dans la bande verticale [y_min, y_max], trouve le x le plus a
    gauche et le plus a droite ou un pixel 'contenu' (non-fond, opaque)
    existe -- c'est l'empan horizontal reel du texte/icone dessine a cet
    endroit."""
    largeur = img.width
    x_max_recherche = x_max_recherche or largeur
    gauche, droite = None, None
    for y in range(max(0, y_min), min(img.height, y_max)):
        for x in range(max(0, x_min_recherche), min(largeur, x_max_recherche)):
            if not est_pixel_fond(img.getpixel((x, y))):
                if gauche is None or x < gauche:
                    gauche = x
                if droite is None or x > droite:
                    droite = x
    return gauche, droite


def diagnostiquer_technique():
    print("=" * 100)
    print("1/ generer_technique_svg -- texte flottant autour d'un cercle (pas de boite rect)")
    print("=" * 100)
    titre = "Les composants du compteur electrique intelligent"  # >45 car, troncature reelle du code
    composants = [
        {"nom": "Disjoncteur differentiel", "desc": "Protege contre les surtensions electriques", "icone": "⚡"},
        {"nom": "Compteur communicant Linky", "desc": "Releve et transmet votre consommation", "icone": "📡"},
        {"nom": "Tableau de repartition", "desc": "Distribue le courant vers chaque circuit", "icone": "🔌"},
    ]
    svg_bytes = generer_technique_svg(titre, composants, "#1A73E8", index=0)
    img, chemin = rendre_png(svg_bytes, "diag_technique_3comp.png")
    print(f"  PNG sauvegarde : {chemin} ({img.width}x{img.height})")

    # Budget de label reel du code pour 3 composants (LARGEUR_LABEL_TECHNIQUE_PAR_NB[3] = 170,
    # texte centre sur x) -- design assume : le texte DEBORDE INTENTIONNELLEMENT du cercle
    # (pas de boite reelle), donc le vrai critere n'est PAS le cercle mais ce budget.
    largeur_label = 170
    # 3 composants -> positions = [(130,200),(340,200),(550,200)], cercle rayon 52
    positions = [(130, 200), (340, 200), (550, 200)]
    for i, (x, y) in enumerate(positions):
        boite_gauche, boite_droite = x - 52, x + 52
        budget_gauche, budget_droite = x - largeur_label // 2, x + largeur_label // 2

        # 3 bandes distinctes pour isoler la source d'un eventuel depassement :
        # icone seule (emoji, taille 22, pas de troncature possible -> glyphe
        # de remplacement potentiellement large si la police n'a pas l'emoji),
        # puis nom et desc (tous deux passes par ajuster_texte_svg).
        g_icone, d_icone = empan_horizontal_contenu(img, y - 28, y - 4, x_min_recherche=max(0, x - 140), x_max_recherche=min(680, x + 140))
        g_nom, d_nom = empan_horizontal_contenu(img, y + 2, y + 14, x_min_recherche=max(0, x - 140), x_max_recherche=min(680, x + 140))
        g_desc, d_desc = empan_horizontal_contenu(img, y + 16, y + 28, x_min_recherche=max(0, x - 140), x_max_recherche=min(680, x + 140))

        def _rapport(label, g, d):
            if g is None:
                return f"    {label} : aucun pixel detecte"
            dep_cercle = max(0, boite_gauche - g) + max(0, d - boite_droite)
            dep_budget = max(0, budget_gauche - g) + max(0, d - budget_droite)
            statut = "⚠️ hors budget label" if dep_budget else ("ok (deborde le cercle par design)" if dep_cercle else "OK")
            return f"    {label} : [{g},{d}]  vs cercle=[{boite_gauche},{boite_droite}] (depasse:{dep_cercle}px)  vs budget_label=[{budget_gauche},{budget_droite}] (depasse:{dep_budget}px)  -> {statut}"

        print(f"  Composant {i+1} '{composants[i]['nom'][:20]}' (icone={composants[i]['icone']}) :")
        print(_rapport("icone", g_icone, d_icone))
        print(_rapport("nom  ", g_nom, d_nom))
        print(_rapport("desc ", g_desc, d_desc))

    # Titre header : bande y=10 a y=30, boite = 0..680
    g, d = empan_horizontal_contenu(img, 8, 30)
    print(f"\n  Titre header : contenu_reel=[{g},{d}] (largeur {d-g if g is not None else '?'}px) sur bandeau 680px -> {'OK' if (d or 0) <= 680 else 'DEPASSEMENT'}")


def diagnostiquer_flowchart():
    print()
    print("=" * 100)
    print("2/ generer_flowchart_svg -- texte dans un rect explicite")
    print("=" * 100)
    labels = ["Contacter votre fournisseur actuel", "Rassembler les documents necessaires", "Signer le nouveau contrat"]
    descs = ["Preparez votre numero de contrat et vos coordonnees", "Facture recente, RIB, piece d'identite valide", "Verifiez les conditions avant signature"]
    svg_bytes = generer_flowchart_svg(labels, descs, "#1A73E8", index=0)
    img, chemin = rendre_png(svg_bytes, "diag_flowchart_3etapes.png")
    print(f"  PNG sauvegarde : {chemin} ({img.width}x{img.height})")

    marge = 35
    largeur = 680
    boite_gauche = marge + 52
    boite_droite = largeur - marge - 15  # ~marge interne du rect (largeur-marge-72 a partir de x=marge+52)
    for i in range(len(labels)):
        y = 50 + i * 85
        g, d = empan_horizontal_contenu(img, y + 4, y + 46, x_min_recherche=boite_gauche, x_max_recherche=680)
        depasse = max(0, (d or 0) - boite_droite)
        statut = "⚠️ DEPASSEMENT" if depasse else "OK"
        print(f"  Etape {i+1} : rect=[{boite_gauche},{boite_droite}]  contenu_reel=[{g},{d}]  -> {statut} ({depasse}px)")


def diagnostiquer_comparatif():
    print()
    print("=" * 100)
    print("3/ generer_comparatif_svg -- entetes de colonnes dans un rect explicite")
    print("=" * 100)
    items = ["Offre Electricite Verte", "Offre Standard Classique"]
    criteres = [
        {"nom": "Delai de mise en service", "item_0": "Environ 15 jours ouvres", "item_1": "Sous 48h en moyenne", "score_0": 7, "score_1": 9},
    ]
    svg_bytes = generer_comparatif_svg(items, criteres, "#1A73E8", index=0)
    img, chemin = rendre_png(svg_bytes, "diag_comparatif_2items.png")
    print(f"  PNG sauvegarde : {chemin} ({img.width}x{img.height})")

    nb_items = 2
    col_w = (680 - 160) // nb_items
    for i in range(nb_items):
        boite_gauche = 160 + i * col_w
        boite_droite = boite_gauche + col_w
        g, d = empan_horizontal_contenu(img, 44, 72, x_min_recherche=boite_gauche, x_max_recherche=boite_droite + 30)
        depasse = max(0, (d or 0) - boite_droite)
        statut = "⚠️ DEPASSEMENT" if depasse else "OK"
        print(f"  Colonne {i+1} '{items[i][:14]}' : rect=[{boite_gauche},{boite_droite}]  contenu_reel=[{g},{d}]  -> {statut} ({depasse}px)")


def main():
    import subprocess
    try:
        fonts = subprocess.run(["fc-list", ":family"], capture_output=True, text=True, timeout=10).stdout
        print("Polices disponibles sur ce runner (extrait) :")
        lignes = sorted(set(fonts.splitlines()))
        for l in [x for x in lignes if any(k in x.lower() for k in ["arial", "liberation", "dejavu", "sans"])][:20]:
            print(f"  {l}")
    except Exception as e:
        print(f"(fc-list indisponible : {e})")
    print()

    diagnostiquer_technique()
    diagnostiquer_flowchart()
    diagnostiquer_comparatif()


if __name__ == "__main__":
    main()
