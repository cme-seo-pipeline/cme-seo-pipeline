FICHIER = "cme-mobile/app/(tabs)/index.tsx"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Import cache
# ============================================================
ancien1 = '''import { router } from "expo-router";'''
nouveau1 = '''import { router } from "expo-router";
import { sauvegarderCache, lireCache, formaterDateCache } from "../../lib/cache";'''

if "sauvegarderCache" in contenu:
    print("⏭️  PATCH 1 (import cache) : deja present, ignore")
elif ancien1 not in contenu:
    print("❌ PATCH 1 (import cache) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("✅ PATCH 1 (import cache) : ajoute")

# ============================================================
# PATCH 2 — Etat + logique de fetch avec repli sur le cache
# ============================================================
ancien2 = '''  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  async function fetchArticles() {
    try {
      const res = await fetch(
        "https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts?per_page=8&_embed"
      );
      const data = await res.json();
      setArticles(Array.isArray(data) ? data : []);
    } catch {
      // silencieux : section actualites simplement vide si echec reseau
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }'''

nouveau2 = '''  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [horsLigne, setHorsLigne] = useState(false);
  const [dateCache, setDateCache] = useState<number | null>(null);
  const CLE_CACHE = "cache_articles";
  async function fetchArticles() {
    try {
      const res = await fetch(
        "https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts?per_page=8&_embed"
      );
      const data = await res.json();
      const liste = Array.isArray(data) ? data : [];
      setArticles(liste);
      setHorsLigne(false);
      sauvegarderCache(CLE_CACHE, liste);
    } catch {
      const cache = await lireCache<Article[]>(CLE_CACHE);
      if (cache) {
        setArticles(cache.donnees);
        setDateCache(cache.date);
        setHorsLigne(true);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }'''

if "horsLigne" in contenu:
    print("⏭️  PATCH 2 (etat + fetch) : deja present, ignore")
elif ancien2 not in contenu:
    print("❌ PATCH 2 (etat + fetch) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (etat + fetch) : ajoute")

# ============================================================
# PATCH 3 — Banniere hors-ligne (juste avant la section Actualites)
# ============================================================
ancien3 = '''      <Text style={styles.sectionTitre}>Actualités</Text>
      {loading ? ('''

nouveau3 = '''      <Text style={styles.sectionTitre}>Actualités</Text>
      {horsLigne && (
        <View style={styles.banniereHorsLigne}>
          <Text style={styles.banniereTexte}>
            📡 Hors ligne — dernières données du {dateCache ? formaterDateCache(dateCache) : "..."}
          </Text>
        </View>
      )}
      {loading ? ('''

if "banniereHorsLigne" in contenu:
    print("⏭️  PATCH 3 (banniere JSX) : deja present, ignore")
elif ancien3 not in contenu:
    print("❌ PATCH 3 (banniere JSX) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien3, nouveau3, 1)
    print("✅ PATCH 3 (banniere JSX) : ajoutee")

# ============================================================
# PATCH 4 — Style de la banniere
# ============================================================
ancien4 = '''  videTexte: { color: "#9ca3af", fontSize: 13, marginHorizontal: 16 },'''
nouveau4 = ancien4 + '''
  banniereHorsLigne: {
    backgroundColor: "#fef3c7",
    borderRadius: 10,
    padding: 10,
    marginHorizontal: 16,
    marginBottom: 10,
  },
  banniereTexte: { fontSize: 12, color: "#92400e", fontWeight: "500" },'''

if "banniereHorsLigne:" in contenu:
    print("⏭️  PATCH 4 (style banniere) : deja present, ignore")
elif ancien4 not in contenu:
    print("❌ PATCH 4 (style banniere) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien4, nouveau4, 1)
    print("✅ PATCH 4 (style banniere) : ajoute")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
