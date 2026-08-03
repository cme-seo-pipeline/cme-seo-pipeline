FICHIER = "cme-mobile/app/(tabs)/dossiers.tsx"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Import cache
# ============================================================
ancien1 = '''import { useAuth } from "../../contexts/AuthContext";'''
nouveau1 = '''import { useAuth } from "../../contexts/AuthContext";
import { sauvegarderCache, lireCache, formaterDateCache } from "../../lib/cache";'''

if "sauvegarderCache" in contenu.split("export default")[0]:
    print("⏭️  PATCH 1 (import cache) : deja present, ignore")
elif ancien1 not in contenu:
    print("❌ PATCH 1 (import cache) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("✅ PATCH 1 (import cache) : ajoute")

# ============================================================
# PATCH 2 — Etat + logique de fetch avec repli sur le cache
# ============================================================
ancien2 = '''  const { getToken } = useAuth();
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

nouveau2 = '''  const { getToken } = useAuth();
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

if "horsLigne" in contenu:
    print("⏭️  PATCH 2 (etat + fetch) : deja present, ignore")
elif ancien2 not in contenu:
    print("❌ PATCH 2 (etat + fetch) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (etat + fetch) : ajoute")

# ============================================================
# PATCH 3 — Banniere hors-ligne (juste avant la FlatList)
# ============================================================
ancien3 = '''      <Text style={styles.titre}>Mes simulations</Text>
      <FlatList'''

nouveau3 = '''      <Text style={styles.titre}>Mes simulations</Text>
      {horsLigne && (
        <View style={styles.banniereHorsLigne}>
          <Text style={styles.banniereTexte}>
            📡 Hors ligne — dernières données du {dateCache ? formaterDateCache(dateCache) : "..."}
          </Text>
        </View>
      )}
      <FlatList'''

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
ancien4 = '''  titre: { fontSize: 22, fontWeight: "700", color: "#111827", marginBottom: 16 },'''
nouveau4 = ancien4 + '''
  banniereHorsLigne: {
    backgroundColor: "#fef3c7",
    borderRadius: 10,
    padding: 10,
    marginBottom: 12,
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
