FICHIER = "cme-mobile/app/(tabs)/dossiers.tsx"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''  const { getToken } = useAuth();
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

nouveau = '''  const { getToken } = useAuth();
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

# Detection precise : la vraie declaration d'etat, pas juste le mot "horsLigne"
# qui existe deja ailleurs (dans le JSX de la banniere).
if "const [horsLigne, setHorsLigne]" in contenu:
    print("⏭️  PATCH : deja reellement present, ignore")
elif ancien not in contenu:
    print("❌ PATCH : ancre non trouvee (fichier dans un etat inattendu)")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH : etat + logique de cache ajoutes (fichier repare)")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
