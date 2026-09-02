FICHIER = "/home/contact/cme-pipeline/pipeline/server.py"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien_css = "  header h1 { margin: 0; font-size: 20px; }"
nouveau_css = """  header h1 { margin: 0; font-size: 20px; }
  .logo-icone { flex-shrink: 0; }"""

ancien_html = '''<header>
  <h1>ORCAAS</h1>'''
nouveau_html = '''<header>
  <svg class="logo-icone" viewBox="80 10 420 300" width="40" height="40">
    <path d="M 160 260 C 158 200 190 145 245 125 C 250 80 285 45 335 35 C 365 29 395 35 415 52 C 398 58 380 70 370 88 C 395 80 425 82 448 98 C 432 102 415 112 405 128 C 432 125 460 135 478 158 C 460 158 442 165 430 178 C 455 182 478 198 490 222 C 470 220 450 224 434 234 C 452 244 465 262 468 285 C 448 277 425 276 405 282 C 413 298 412 315 402 328 C 388 315 370 308 350 308 C 355 322 352 336 340 346 C 322 334 305 320 292 302 C 260 308 228 300 205 280 C 185 282 168 276 160 260 Z" fill="#0a1120"/>
    <path d="M 250 130 C 285 98 330 88 368 102 C 398 113 418 138 418 168 C 396 166 375 172 358 184 C 368 196 371 210 366 222 C 348 213 328 210 310 213 C 314 226 311 239 302 248 C 285 234 268 226 250 227 C 236 212 230 193 233 174 C 237 158 242 143 250 130 Z" fill="#f8fafc"/>
    <path d="M 205 280 C 202 265 208 250 222 240 C 232 248 236 260 233 273 C 224 280 214 281 205 280 Z" fill="#f8fafc"/>
    <circle cx="352" cy="148" r="19" fill="#60a5fa"/>
    <circle cx="352" cy="148" r="7.5" fill="#1e3a5f"/>
    <circle cx="349" cy="145" r="2.5" fill="#f8fafc"/>
    <g stroke="#93c5fd" stroke-width="2" opacity="0.9">
      <path d="M 352 129 L 352 110 L 385 110" fill="none"/>
      <circle cx="388" cy="110" r="3.5" fill="#93c5fd"/>
      <path d="M 371 148 L 405 148 L 405 170" fill="none"/>
      <circle cx="405" cy="173" r="3.5" fill="#93c5fd"/>
      <path d="M 335 160 L 305 185 L 305 212" fill="none"/>
      <circle cx="305" cy="215" r="3.5" fill="#93c5fd"/>
    </g>
    <path d="M 160 260 C 140 258 122 260 108 268 C 122 274 138 278 155 277 Z" fill="#0a1120"/>
  </svg>
  <h1>ORCAAS</h1>'''

if 'class="logo-icone"' in contenu:
    print("SKIP : deja present")
elif ancien_css not in contenu or ancien_html not in contenu:
    print("ERREUR : ancre non trouvee")
else:
    contenu = contenu.replace(ancien_css, nouveau_css, 1)
    contenu = contenu.replace(ancien_html, nouveau_html, 1)
    print("OK : logo integre dans l'en-tete")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("Fichier sauvegarde :", FICHIER)
