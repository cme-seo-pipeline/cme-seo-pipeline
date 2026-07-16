"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_CLIENT_API_URL;

interface Lead {
  id: string;
  tool: string;
  statut: string;
  montant_estime: number;
  economie_estimee: number;
  source_post_id?: string;
  derniere_maj?: string;
  details?: Record<string, unknown>;
}

const TOOL_LABELS: Record<string, { label: string; url: string; color: string }> = {
  solaire: {
    label: "☀️ Solaire",
    url: "https://www.comprendre-mon-energie.fr/devis-panneau-solaire/",
    color: "bg-green-100 text-green-800",
  },
  "comparateur-energie": {
    label: "⚡ Comparateur Énergie",
    url: "https://www.comprendre-mon-energie.fr/comparateur-energie-electricite-gaz/",
    color: "bg-blue-100 text-blue-800",
  },
  "aides-renovation": {
    label: "🏠 Aides Rénovation",
    url: "https://www.comprendre-mon-energie.fr/simulateur-aides-renovation-energetique/",
    color: "bg-amber-100 text-amber-800",
  },
};

const STATUT_LABELS: Record<string, { label: string; color: string }> = {
  nouveau: { label: "Nouveau", color: "bg-gray-100 text-gray-700" },
  en_cours: { label: "En cours", color: "bg-blue-100 text-blue-700" },
  documents_manquants: {
    label: "Documents manquants",
    color: "bg-orange-100 text-orange-700",
  },
  traite: { label: "Traité", color: "bg-green-100 text-green-700" },
  abandonne: { label: "Abandonné", color: "bg-red-100 text-red-700" },
};

export default function DashboardPage() {
  const { user, loading, logout, getToken } = useAuth();
  const router = useRouter();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [leadsLoading, setLeadsLoading] = useState(true);
  const [erreur, setErreur] = useState("");

  const fetchLeads = useCallback(async () => {
    setLeadsLoading(true);
    setErreur("");
    try {
      const token = await getToken();
      if (!token) return;
      const res = await fetch(`${API_URL}/leads`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Erreur de chargement");
      const data = await res.json();
      setLeads(data.leads || []);
    } catch {
      setErreur("Impossible de charger vos dossiers pour le moment.");
    } finally {
      setLeadsLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
      return;
    }
    if (user) {
      fetchLeads();
    }
  }, [user, loading, router, fetchLeads]);

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  if (loading || !user) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-gray-500">Chargement...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 max-w-4xl w-full mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mes dossiers</h1>
          <p className="text-sm text-gray-500">{user.email}</p>
        </div>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-700 hover:text-gray-900 border border-gray-300 rounded-lg px-4 h-10 bg-white"
        >
          Déconnexion
        </button>
      </div>

      {/* Relancer une simulation */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Lancer une nouvelle simulation
        </h2>
        <div className="flex flex-wrap gap-3">
          {Object.entries(TOOL_LABELS).map(([key, tool]) => (
            <a
              key={key}
              href={tool.url}
              target="_blank"
              rel="noopener noreferrer"
              className={`px-4 py-2 rounded-lg text-sm font-medium ${tool.color} hover:opacity-80 transition-opacity`}
            >
              {tool.label}
            </a>
          ))}
        </div>
      </div>

      {/* Liste des dossiers */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            Historique de vos dossiers
          </h2>
        </div>

        {leadsLoading ? (
          <p className="text-gray-500 text-center py-10">Chargement...</p>
        ) : erreur ? (
          <p className="text-red-600 text-center py-10">{erreur}</p>
        ) : leads.length === 0 ? (
          <div className="text-center py-12 px-6">
            <p className="text-gray-700 mb-1">Aucun dossier pour le moment</p>
            <p className="text-sm text-gray-400">
              Lancez une simulation ci-dessus pour commencer
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {leads.map((lead) => {
              const tool = TOOL_LABELS[lead.tool] || {
                label: lead.tool,
                color: "bg-gray-100 text-gray-700",
              };
              const statut = STATUT_LABELS[lead.statut] || STATUT_LABELS.nouveau;
              return (
                <li key={lead.id} className="px-6 py-4 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${tool.color}`}>
                        {tool.label}
                      </span>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statut.color}`}>
                        {statut.label}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700">
                      Montant estimé : {lead.montant_estime?.toLocaleString("fr-FR")} €
                      {lead.economie_estimee ? (
                        <span className="text-green-600">
                          {" "}
                          · Économie : {lead.economie_estimee.toLocaleString("fr-FR")} €
                        </span>
                      ) : null}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
