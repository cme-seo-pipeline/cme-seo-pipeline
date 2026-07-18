"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

const OUTILS = [
  {
    label: "☀️ Solaire",
    desc: "Estimez votre installation en 2 minutes",
    url: "https://www.comprendre-mon-energie.fr/devis-panneau-solaire/",
    color: "bg-green-100 text-green-800 hover:bg-green-200",
  },
  {
    label: "⚡ Comparateur Énergie",
    desc: "Trouvez l'offre gaz/élec la moins chère",
    url: "https://www.comprendre-mon-energie.fr/comparateur-energie-electricite-gaz/",
    color: "bg-blue-100 text-blue-800 hover:bg-blue-200",
  },
  {
    label: "🏠 Aides Rénovation",
    desc: "MaPrimeRénov', CEE, Éco-PTZ...",
    url: "https://www.comprendre-mon-energie.fr/simulateur-aides-renovation-energetique/",
    color: "bg-amber-100 text-amber-800 hover:bg-amber-200",
  },
];

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-gray-500">Chargement...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 max-w-5xl w-full mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Bonjour {user.email?.split("@")[0]} 👋
        </h1>
        <p className="text-sm text-gray-500">
          Bienvenue sur votre espace Comprendre Mon Énergie
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Bloc News */}
        <Link
          href="/news"
          className="bg-white rounded-2xl border border-gray-200 p-6 hover:shadow-md transition-shadow flex flex-col"
        >
          <div className="text-3xl mb-3">📰</div>
          <h2 className="font-bold text-gray-900 mb-1">News</h2>
          <p className="text-sm text-gray-500 flex-1">
            Les derniers articles sur l&apos;énergie, mis à jour en continu
          </p>
          <span className="text-sm font-medium text-green-600 mt-4">
            Voir les articles →
          </span>
        </Link>

        {/* Bloc Énergie */}
        <Link
          href="/energie"
          className="bg-white rounded-2xl border border-gray-200 p-6 hover:shadow-md transition-shadow flex flex-col"
        >
          <div className="text-3xl mb-3">⚡</div>
          <h2 className="font-bold text-gray-900 mb-1">Énergie</h2>
          <p className="text-sm text-gray-500 flex-1">
            Guides gaz, électricité, solaire, rénovation et aides
          </p>
          <span className="text-sm font-medium text-green-600 mt-4">
            Explorer →
          </span>
        </Link>

        {/* Bloc Réaliser un projet */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6 flex flex-col">
          <div className="text-3xl mb-3">🚀</div>
          <h2 className="font-bold text-gray-900 mb-3">Réaliser un projet</h2>
          <div className="space-y-2 flex-1">
            {OUTILS.map((outil) => (
              <a
                key={outil.label}
                href={outil.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${outil.color}`}
              >
                {outil.label}
              </a>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 bg-gradient-to-r from-green-600 to-green-700 rounded-2xl p-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="font-bold text-white mb-1">Suivez vos dossiers</h2>
          <p className="text-sm text-green-50">
            Retrouvez l&apos;historique et le statut de vos demandes
          </p>
        </div>
        <Link
          href="/simulations"
          className="bg-white text-green-700 font-semibold text-sm px-5 py-2.5 rounded-lg hover:bg-green-50 transition-colors whitespace-nowrap"
        >
          Mes simulations →
        </Link>
      </div>
    </div>
  );
}
