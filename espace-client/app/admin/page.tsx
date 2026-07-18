"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_CLIENT_API_URL;

interface Lead {
  id: string;
  owner_uid: string;
  tool: string;
  statut: string;
  montant_estime: number;
  economie_estimee: number;
  source_post_id?: string;
  derniere_maj?: string;
}

interface ClientUser {
  uid: string;
  email: string;
  nom: string;
  prenom: string;
  telephone: string;
  role: string;
}

const TOOL_LABELS: Record<string, { label: string; color: string }> = {
  solaire: { label: "☀️ Solaire", color: "bg-green-100 text-green-800" },
  "comparateur-energie": { label: "⚡ Comparateur", color: "bg-blue-100 text-blue-800" },
  "aides-renovation": { label: "🏠 Aides", color: "bg-amber-100 text-amber-800" },
};

const STATUT_OPTIONS = [
  { value: "nouveau", label: "Nouveau", color: "bg-gray-100 text-gray-700" },
  { value: "en_cours", label: "En cours", color: "bg-blue-100 text-blue-700" },
  { value: "documents_manquants", label: "Documents manquants", color: "bg-orange-100 text-orange-700" },
  { value: "traite", label: "Traité", color: "bg-green-100 text-green-700" },
  { value: "abandonne", label: "Abandonné", color: "bg-red-100 text-red-700" },
];

export default function AdminPage() {
  const { user, loading, getToken } = useAuth();
  const router = useRouter();

  const [autorise, setAutorise] = useState<boolean | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [users, setUsers] = useState<Record<string, ClientUser>>({});
  const [dataLoading, setDataLoading] = useState(true);
  const [erreur, setErreur] = useState("");
  const [filtreOutil, setFiltreOutil] = useState("");
  const [filtreStatut, setFiltreStatut] = useState("");
  const [majEnCours, setMajEnCours] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setDataLoading(true);
    setErreur("");
    try {
      const token = await getToken();
      if (!token) return;

      const [leadsRes, usersRes] = await Promise.all([
        fetch(`${API_URL}/admin/leads`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/admin/users`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);

      if (leadsRes.status === 403 || usersRes.status === 403) {
        setAutorise(false);
        return;
      }
      if (!leadsRes.ok || !usersRes.ok) throw new Error("Erreur de chargement");

      const leadsData = await leadsRes.json();
      const usersData = await usersRes.json();

      const usersMap: Record<string, ClientUser> = {};
      (usersData.users || []).forEach((u: ClientUser) => {
        usersMap[u.uid] = u;
      });

      setLeads(leadsData.leads || []);
      setUsers(usersMap);
      setAutorise(true);
    } catch {
      setErreur("Impossible de charger les données.");
    } finally {
      setDataLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
      return;
    }
    if (user) {
      fetchData();
    }
  }, [user, loading, router, fetchData]);

  async function changerStatut(lead: Lead, nouveauStatut: string) {
    setMajEnCours(lead.id);
    try {
      const token = await getToken();
      const res = await fetch(
        `${API_URL}/admin/leads/${lead.owner_uid}/${lead.id}/status`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ statut: nouveauStatut }),
        }
      );
      if (res.ok) {
        setLeads((prev) =>
          prev.map((l) => (l.id === lead.id ? { ...l, statut: nouveauStatut } : l))
        );
      }
    } finally {
      setMajEnCours(null);
    }
  }

  if (loading || dataLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-gray-500">Chargement...</p>
      </div>
    );
  }

  if (autorise === false) {
    return (
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="bg-red-50 border border-red-200 rounded-xl px-6 py-8 text-center max-w-md">
          <p className="text-red-700 font-semibold mb-1">Accès refusé</p>
          <p className="text-sm text-red-600">
            Cette page est réservée aux administrateurs.
          </p>
        </div>
      </div>
    );
  }

  const leadsFiltres = leads.filter((l) => {
    if (filtreOutil && l.tool !== filtreOutil) return false;
    if (filtreStatut && l.statut !== filtreStatut) return false;
    return true;
  });

  return (
    <div className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Back-office — Tous les dossiers</h1>
        <p className="text-sm text-gray-500">
          {leads.length} dossier{leads.length > 1 ? "s" : ""} au total
        </p>
      </div>

      {/* Filtres */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={filtreOutil}
          onChange={(e) => setFiltreOutil(e.target.value)}
          className="h-10 px-3 border border-gray-300 rounded-lg bg-white text-gray-900 text-sm"
        >
          <option value="">Tous les outils</option>
          <option value="solaire">☀️ Solaire</option>
          <option value="comparateur-energie">⚡ Comparateur</option>
          <option value="aides-renovation">🏠 Aides</option>
        </select>

        <select
          value={filtreStatut}
          onChange={(e) => setFiltreStatut(e.target.value)}
          className="h-10 px-3 border border-gray-300 rounded-lg bg-white text-gray-900 text-sm"
        >
          <option value="">Tous les statuts</option>
          {STATUT_OPTIONS.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
      </div>

      {erreur && (
        <p className="text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
          {erreur}
        </p>
      )}

      {/* Tableau */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Client</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Outil</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Montant</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Statut</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Dernière MAJ</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {leadsFiltres.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-10 text-gray-400">
                  Aucun dossier ne correspond aux filtres
                </td>
              </tr>
            ) : (
              leadsFiltres.map((lead) => {
                const client = users[lead.owner_uid];
                const tool = TOOL_LABELS[lead.tool] || { label: lead.tool, color: "bg-gray-100 text-gray-700" };
                return (
                  <tr key={lead.id}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">
                        {client ? `${client.prenom} ${client.nom}` : "—"}
                      </div>
                      <div className="text-xs text-gray-500">
                        {client?.email || lead.owner_uid}
                      </div>
                      {client?.telephone && (
                        <div className="text-xs text-gray-500">{client.telephone}</div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${tool.color}`}>
                        {tool.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-900">
                      {lead.montant_estime?.toLocaleString("fr-FR")} €
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={lead.statut}
                        disabled={majEnCours === lead.id}
                        onChange={(e) => changerStatut(lead, e.target.value)}
                        className="text-xs font-medium border border-gray-300 rounded-lg px-2 py-1 bg-white text-gray-900"
                      >
                        {STATUT_OPTIONS.map((s) => (
                          <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {lead.derniere_maj
                        ? new Date(lead.derniere_maj).toLocaleString("fr-FR")
                        : "—"}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
