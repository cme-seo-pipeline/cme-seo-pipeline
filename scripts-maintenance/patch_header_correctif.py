FICHIER = "espace-client/components/Header.tsx"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

ancien = '''export default function Header() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [menuOuvert, setMenuOuvert] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function fermerSiExterieur(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOuvert(false);
      }
    }
    document.addEventListener("mousedown", fermerSiExterieur);
    return () => document.removeEventListener("mousedown", fermerSiExterieur);
  }, []);'''

nouveau = '''export default function Header() {
  const { user, logout, getToken } = useAuth();
  const router = useRouter();
  const [menuOuvert, setMenuOuvert] = useState(false);
  const [notifOuvert, setNotifOuvert] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const menuRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function fermerSiExterieur(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOuvert(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOuvert(false);
      }
    }
    document.addEventListener("mousedown", fermerSiExterieur);
    return () => document.removeEventListener("mousedown", fermerSiExterieur);
  }, []);

  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/notifications`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setNotifications(data.notifications || []);
    } catch {
      // silencieux
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      fetchNotifications();
      const intervalle = setInterval(fetchNotifications, 30000);
      return () => clearInterval(intervalle);
    }
  }, [user, fetchNotifications]);

  async function marquerLue(notif: any) {
    if (notif.lu) return;
    setNotifications((prev) =>
      prev.map((n) => (n.id === notif.id ? { ...n, lu: true } : n))
    );
    try {
      const token = await getToken();
      await fetch(`${API_URL}/notifications/${notif.id}/read`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // silencieux
    }
  }

  function formaterDateNotif(date: any): string {
    try {
      const seconds = date?._seconds ?? date?.seconds;
      if (!seconds) return "";
      return new Date(seconds * 1000).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "long",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  }

  const nonLues = notifications.filter((n) => !n.lu).length;'''

if "fetchNotifications" in contenu:
    print("⏭️  PATCH (etat + fonctions) : deja present, ignore")
elif ancien not in contenu:
    print("❌ PATCH (etat + fonctions) : ancre TOUJOURS non trouvee")
else:
    contenu = contenu.replace(ancien, nouveau, 1)
    print("✅ PATCH (etat + fonctions) : ajoutes cette fois")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
