with open('tracking-api/server.py', 'r') as f:
    content = f.read()

old = '            "source_page":       str(data.get("source_page", ""))[:250],'
new = '''            "source_page":       str(data.get("source_page", ""))[:250],
            "source_post_id":    str(data.get("source_post_id", ""))[:20],'''

if old in content:
    content = content.replace(old, new, 1)
    print("✅ Patch tracking-api appliqué")
else:
    print("❌ Pattern non trouvé")

with open('tracking-api/server.py', 'w') as f:
    f.write(content)
