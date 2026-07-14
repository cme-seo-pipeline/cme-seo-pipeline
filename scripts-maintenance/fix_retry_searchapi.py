with open('pipeline.py', 'r') as f:
    content = f.read()

old = """        try:
            response = requests.get(
                "https://www.searchapi.io/api/v1/search",
                params=params, timeout=30
            )
            organic_results = response.json().get("organic_results", [])
            count = 0
            for r in organic_results:
                if count >= 5:
                    break
                link = r.get("link", "")
                title = r.get("title", "").lower()
                if not any(d in link for d in BLACKLIST_DOMAINS) \\
                   and not any(w in title for w in NEGATIVE_WORDS):
                    all_market_data.append({
                        "Requête_Niche": search_query,
                        "Silo": silo,
                        "Sous-Silo": subcat,
                        "Position": r.get("position"),
                        "Concurrent": r.get("title"),
                        "URL": link
                    })
                    count += 1
        except Exception as e:
            print(f"❌ Erreur scraping : {e}")"""

new = """        organic_results = []
        for tentative in range(3):
            try:
                response = requests.get(
                    "https://www.searchapi.io/api/v1/search",
                    params=params, timeout=45
                )
                organic_results = response.json().get("organic_results", [])
                break
            except Exception as e:
                if tentative < 2:
                    attente = 5 * (tentative + 1)
                    print(f"⚠️ Scraping échoué (tentative {tentative+1}/3) : {e} — retry dans {attente}s")
                    time.sleep(attente)
                else:
                    print(f"❌ Scraping abandonné après 3 tentatives pour '{search_query}' : {e}")

        count = 0
        for r in organic_results:
            if count >= 5:
                break
            link = r.get("link", "")
            title = r.get("title", "").lower()
            if not any(d in link for d in BLACKLIST_DOMAINS) \\
               and not any(w in title for w in NEGATIVE_WORDS):
                all_market_data.append({
                    "Requête_Niche": search_query,
                    "Silo": silo,
                    "Sous-Silo": subcat,
                    "Position": r.get("position"),
                    "Concurrent": r.get("title"),
                    "URL": link
                })
                count += 1"""

if old in content:
    content = content.replace(old, new, 1)
    print("✅ Retry SearchAPI appliqué")
else:
    print("❌ Pattern non trouvé")

with open('pipeline.py', 'w') as f:
    f.write(content)
