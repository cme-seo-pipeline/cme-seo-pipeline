import re

# ============================================================
# FICHIER 1 — dossiers.tsx (patch 2)
# ============================================================
FICHIER1 = "cme-mobile/app/(tabs)/dossiers.tsx"

with open(FICHIER1, "r", encoding="utf-8") as f:
    contenu1 = f.read()

ancien1 = '''  const { getToken } = useAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  async function fetchLeads() {
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/leads`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setLeads(data.leads || []);
    } catch {
      // silencieux : liste vide affichee par defaut
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }'''

nouveau1 = '''  const { getToken } = useAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [horsLigne, setHorsLigne] = useState(false);
  const [dateCache, setDateCache] = useState<number | null>(null);
  const CLE_CACHE = "cache_leads";

  async function fetchLeads() {
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/leads`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      const liste = data.leads || [];
      setLeads(liste);
      setHorsLigne(false);
      sauvegarderCache(CLE_CACHE, liste);
    } catch {
      const cache = await lireCache<Lead[]>(CLE_CACHE);
      if (cache) {
        setLeads(cache.donnees);
        setDateCache(cache.date);
        setHorsLigne(true);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }'''

if "horsLigne" in contenu1:
    print("⏭️  dossiers.tsx PATCH 2 : deja present, ignore")
elif ancien1 not in contenu1:
    print("❌ dossiers.tsx PATCH 2 : ancre TOUJOURS non trouvee")
else:
    contenu1 = contenu1.replace(ancien1, nouveau1, 1)
    print("✅ dossiers.tsx PATCH 2 : ajoute cette fois")

with open(FICHIER1, "w", encoding="utf-8") as f:
    f.write(contenu1)

# ============================================================
# FICHIER 2 — index.tsx (patch 2 et patch 3)
# ============================================================
FICHIER2 = "cme-mobile/app/(tabs)/index.tsx"

with open(FICHIER2, "r", encoding="utf-8") as f:
    contenu2 = f.read()

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

if "horsLigne" in contenu2:
    print("⏭️  index.tsx PATCH 2 : deja present, ignore")
elif ancien2 not in contenu2:
    print("❌ index.tsx PATCH 2 : ancre TOUJOURS non trouvee")
else:
    contenu2 = contenu2.replace(ancien2, nouveau2, 1)
    print("✅ index.tsx PATCH 2 : ajoute cette fois")

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

if "banniereHorsLigne" in contenu2:
    print("⏭️  index.tsx PATCH 3 : deja present, ignore")
elif ancien3 not in contenu2:
    print("❌ index.tsx PATCH 3 : ancre TOUJOURS non trouvee")
else:
    contenu2 = contenu2.replace(ancien3, nouveau3, 1)
    print("✅ index.tsx PATCH 3 : ajoutee cette fois")

with open(FICHIER2, "w", encoding="utf-8") as f:
    f.write(contenu2)

print("📝 Fichiers sauvegardes :", FICHIER1, "et", FICHIER2)
