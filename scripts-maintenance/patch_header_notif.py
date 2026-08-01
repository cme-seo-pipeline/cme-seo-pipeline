FICHIER = "espace-client/components/Header.tsx"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — import useCallback
# ============================================================
ancien1 = '''import { useState, useRef, useEffect } from "react";'''
nouveau1 = '''import { useState, useRef, useEffect, useCallback } from "react";'''

if "useCallback" in contenu.split("\n")[0]:
    print("⏭️  PATCH 1 (import useCallback) : deja present, ignore")
elif ancien1 not in contenu:
    print("❌ PATCH 1 (import useCallback) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("✅ PATCH 1 (import useCallback) : ajoute")

# ============================================================
# PATCH 2 — Constante API_URL, juste avant NAV_LINKS
# ============================================================
ancien2 = '''const NAV_LINKS = ['''
nouveau2 = '''const API_URL = process.env.NEXT_PUBLIC_CLIENT_API_URL;
const NAV_LINKS = ['''

if "const API_URL" in contenu:
    print("⏭️  PATCH 2 (API_URL) : deja present, ignore")
elif ancien2 not in contenu:
    print("❌ PATCH 2 (API_URL) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (API_URL) : ajoutee")

# ============================================================
# PATCH 3 — Etat, refs, fetch et marquage lu
# ============================================================
ancien3 = '''  const { user, logout } = useAuth();
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

nouveau3 = '''  const { user, logout, getToken } = useAuth();
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
    print("⏭️  PATCH 3 (etat + fonctions) : deja present, ignore")
elif ancien3 not in contenu:
    print("❌ PATCH 3 (etat + fonctions) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien3, nouveau3, 1)
    print("✅ PATCH 3 (etat + fonctions) : ajoutes")

# ============================================================
# PATCH 4 — JSX : cloche + menu deroulant, avant le menu profil
# ============================================================
ancien4 = '''        {/* Droite : menu profil */}
        {user && (
          <div className="relative shrink-0" ref={menuRef}>'''

nouveau4 = '''        {/* Cloche notifications */}
        {user && (
          <div className="relative shrink-0" ref={notifRef}>
            <button
              onClick={() => setNotifOuvert((v) => !v)}
              className="relative w-10 h-10 flex items-center justify-center rounded-lg hover:bg-gray-50 transition-colors"
            >
              <span className="text-lg">🔔</span>
              {nonLues > 0 && (
                <span className="absolute top-1 right-1 bg-red-600 text-white text-[10px] font-bold rounded-full min-w-[16px] h-4 flex items-center justify-center px-1">
                  {nonLues > 9 ? "9+" : nonLues}
                </span>
              )}
            </button>
            {notifOuvert && (
              <div className="absolute right-0 top-12 w-80 max-h-96 overflow-y-auto bg-white border border-gray-200 rounded-xl shadow-lg py-2 z-50">
                {notifications.length === 0 ? (
                  <p className="px-4 py-6 text-sm text-gray-400 text-center">
                    Aucune notification
                  </p>
                ) : (
                  notifications.map((n) => (
                    <button
                      key={n.id}
                      onClick={() => marquerLue(n)}
                      className={`w-full text-left px-4 py-3 border-b border-gray-50 last:border-0 hover:bg-gray-50 ${
                        !n.lu ? "bg-green-50" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-sm font-semibold text-gray-900">{n.titre}</span>
                        {!n.lu && <span className="w-2 h-2 rounded-full bg-green-600 mt-1 shrink-0" />}
                      </div>
                      <p className="text-xs text-gray-600 mt-0.5">{n.corps}</p>
                      <p className="text-[11px] text-gray-400 mt-1">{formaterDateNotif(n.date)}</p>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
        )}
        {/* Droite : menu profil */}
        {user && (
          <div className="relative shrink-0" ref={menuRef}>'''

if "Cloche notifications" in contenu:
    print("⏭️  PATCH 4 (JSX cloche) : deja present, ignore")
elif ancien4 not in contenu:
    print("❌ PATCH 4 (JSX cloche) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien4, nouveau4, 1)
    print("✅ PATCH 4 (JSX cloche) : ajoutee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
