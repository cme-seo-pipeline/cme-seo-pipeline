with open('pipeline.py', 'r') as f:
    content = f.read()

fixes = [
    ('"5. Electricite": {', '"5. Électricité": {'),
    ('"2. Renovation Energetique": {', '"2. Rénovation Énergétique": {'),
    ('"3. Aide Energetique": {', '"3. Aide Énergétique": {'),
]

for old, new in fixes:
    if old in content:
        content = content.replace(old, new, 1)
        print(f"✅ {old} -> {new}")
    else:
        print(f"❌ Non trouvé: {old}")

with open('pipeline.py', 'w') as f:
    f.write(content)
