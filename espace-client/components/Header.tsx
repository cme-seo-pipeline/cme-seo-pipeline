"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_CLIENT_API_URL;
const NAV_LINKS = [
  { href: "/simulations", label: "Mes simulations" },
  { href: "/news", label: "News" },
  { href: "/energie", label: "Énergie" },
  { href: "/rendez-vous", label: "Rendez-vous avec un expert" },
];

export default function Header() {
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

  const nonLues = notifications.filter((n) => !n.lu).length;

  async function handleLogout() {
    setMenuOuvert(false);
    await logout();
    router.push("/login");
  }

  const initiale = user?.email ? user.email[0].toUpperCase() : "?";

  return (
    <header className="w-full border-b border-gray-200 bg-white">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
        {/* Gauche : logo + navigation */}
        <div className="flex items-center gap-8 min-w-0">
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <Image
              src="https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/03/cropped-logo-officiel-comprendre-mon-energie-observatoire.png"
              alt="Comprendre Mon Énergie"
              width={36}
              height={36}
              className="rounded"
              priority
            />
            <span className="font-bold text-gray-900 hidden lg:inline whitespace-nowrap">
              Comprendre Mon Énergie
            </span>
          </Link>

          {user && (
            <nav className="hidden md:flex items-center gap-6 overflow-x-auto">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="text-sm font-medium text-gray-600 hover:text-green-600 whitespace-nowrap transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          )}
        </div>

        {/* Cloche notifications */}
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
          <div className="relative shrink-0" ref={menuRef}>
            <button
              onClick={() => setMenuOuvert((v) => !v)}
              className="flex items-center gap-2 h-10 px-2 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <span className="w-8 h-8 rounded-full bg-green-600 text-white text-sm font-semibold flex items-center justify-center">
                {initiale}
              </span>
              <span className="text-sm text-gray-700 hidden sm:inline max-w-[140px] truncate">
                {user.email}
              </span>
            </button>

            {menuOuvert && (
              <div className="absolute right-0 top-12 w-56 bg-white border border-gray-200 rounded-xl shadow-lg py-2 z-50">
                <Link
                  href="/profil"
                  onClick={() => setMenuOuvert(false)}
                  className="block px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Mes informations
                </Link>
                <Link
                  href="/profil?tab=fournisseur"
                  onClick={() => setMenuOuvert(false)}
                  className="block px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Fournisseur
                </Link>
                <Link
                  href="/assistance"
                  onClick={() => setMenuOuvert(false)}
                  className="block px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Assistance
                </Link>
                <div className="border-t border-gray-100 mt-1 pt-1">
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2.5 text-sm text-red-600 hover:bg-red-50"
                  >
                    Déconnexion
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Navigation mobile (sous le header, visible seulement petit ecran) */}
      {user && (
        <nav className="md:hidden flex items-center gap-4 px-4 pb-3 overflow-x-auto">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-xs font-medium text-gray-600 hover:text-green-600 whitespace-nowrap"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
