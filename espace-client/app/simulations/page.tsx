"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_CLIENT_API_URL;

const TOOL_LABELS: Record<string, string> = {
  solaire: "☀️ Solaire",
  "comparateur-energie": "⚡ Comparateur Énergie",
  "aides-renovation": "🏠 Aides Rénovation",
  "rendez-vous-expert": "📅 Rendez-vous expert",
};

const SUJET_LABELS: Record<string, string> = {
  solaire: "Panneaux solaires",
  renovation: "Rénovation énergétique",
  aides: "Aides & subventions",
  contrat: "Contrat gaz/électricité",
  autre: "Autre",
};

const MONTANT_LABELS: Record<string, string> = {
  solaire: "Investissement estimé",
  "comparateur-energie": "Prix annuel estimé",
  "aides-renovation": "Total aides estimées",
};

const STATUT_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  nouveau: { label: "Nouveau", color: "text-blue-700", bg: "bg-blue-100" },
  en_cours: { label: "En cours", color: "text-amber-700", bg: "bg-amber-100" },
  documents_manquants: { label: "Documents manquants", color: "text-red-700", bg: "bg-red-100" },
  traite: { label: "Traité", color: "text-green-700", bg: "bg-green-100" },
  abandonne: { label: "Abandonné", color: "text-gray-600", bg: "bg-gray-100" },
};

interface Lead {
  id: string;
  tool: string;
  statut: string;
  montant_estime?: number;
  economie_estimee?: number;
  details?: Record<string, string | number>;
  derniere_maj?: string;
}

interface Ligne {
  label: string;
  valeur: string;
}

function lignesDetails(item: Lead): Ligne[] {
  const d = item.details || {};
  const lignes: Ligne[] = [];

  switch (item.tool) {
    case "solaire":
      if (d.nb_panneaux) lignes.push({ label: "Installation", valeur: `${d.nb_panneaux} panneaux · ${d.kwc || "?"} kWc` });
      if (d.production) lignes.push({ label: "Production estimée", valeur: `${Number(d.production).toLocaleString("fr-FR")} kWh/an` });
      if (d.roi) lignes.push({ label: "Retour sur investissement", valeur: `${d.roi} ans` });
      if (d.co2) lignes.push({ label: "CO2 évité", valeur: `${Number(d.co2).toLocaleString("fr-FR")} kg/an` });
      break;
    case "comparateur-energie":
      if (d.fournisseur) lignes.push({ label: "Fournisseur", valeur: `${d.fournisseur}${d.offre ? " — " + d.offre : ""}` });
      if (d.energie) lignes.push({ label: "Énergie", valeur: String(d.energie) });
      if (d.kwh) lignes.push({ label: "Consommation", valeur: `${Number(d.kwh).toLocaleString("fr-FR")} kWh/an` });
      if (d.option_tarifaire) lignes.push({ label: "Option tarifaire", valeur: String(d.option_tarifaire) });
      break;
    case "aides-renovation":
      if (d.profil) lignes.push({ label: "Profil", valeur: String(d.profil) });
      if (d.travaux) lignes.push({ label: "Travaux", valeur: String(d.travaux) });
      if (d.montant_mpr) lignes.push({ label: "MaPrimeRénov'", valeur: `${Number(d.montant_mpr).toLocaleString("fr-FR")} €` });
      if (d.montant_cee) lignes.push({ label: "Prime CEE", valeur: `${Number(d.montant_cee).toLocaleString("fr-FR")} €` });
      if (d.reste_a_charge) lignes.push({ label: "Reste à charge", valeur: `${Number(d.reste_a_charge).toLocaleString("fr-FR")} €` });
      if (d.budget) lignes.push({ label: "Budget travaux", valeur: `${Number(d.budget).toLocaleString("fr-FR")} €` });
      break;
    case "rendez-vous-expert":
      if (d.sujet) lignes.push({ label: "Sujet", valeur: SUJET_LABELS[d.sujet as string] || String(d.sujet) });
      if (d.disponibilites) lignes.push({ label: "Disponibilités", valeur: String(d.disponibilites) });
      break;
  }
  return lignes;
}

function formaterDate(iso?: string): string | null {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return null;
  }
}

export default function SimulationsPage() {
  const { user, loading, getToken } = useAuth();
  const router = useRouter();

  const [leads, setLeads] = useState<Lead[]>([]);
  const [chargement, setChargement] = useState(true);

  const fetchLeads = useCallback(async () => {
    setChargement(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/leads`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setLeads(data.leads || []);
    } catch {
      // silencieux
    } finally {
      setChargement(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
      return;
    }
    if (user) fetchLeads();
  }, [user, loading, router, fetchLeads]);

  if (loading || chargement) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-gray-500">Chargement...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 max-w-4xl w-full mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes simulations</h1>
        <button
          onClick={fetchLeads}
          className="text-sm text-green-600 font-medium hover:underline"
        >
          Actualiser
        </button>
      </div>

      {leads.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-10 text-center">
          <p className="text-gray-500">Aucun dossier pour le moment</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {leads.map((item) => {
            const statut = STATUT_LABELS[item.statut] || STATUT_LABELS.nouveau;
            const date = formaterDate(item.derniere_maj);
            const lignes = lignesDetails(item);
            const message = item.details?.message ? String(item.details.message) : null;
            const montantLabel = MONTANT_LABELS[item.tool];

            return (
              <div
                key={item.id}
                className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-900">
                    {TOOL_LABELS[item.tool] || item.tool}
                  </span>
                  <span
                    className={`text-xs font-semibold px-2.5 py-1 rounded-full ${statut.bg} ${statut.color}`}
                  >
                    {statut.label}
                  </span>
                </div>

                {date && <p className="text-xs text-gray-400 mt-1.5">{date}</p>}

                {lignes.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100 space-y-1.5">
                    {lignes.map((l, i) => (
                      <div key={i} className="flex justify-between text-xs gap-2">
                        <span className="text-gray-400 shrink-0">{l.label}</span>
                        <span className="text-gray-700 font-medium text-right">{l.valeur}</span>
                      </div>
                    ))}
                  </div>
                )}

                {message && (
                  <p className="text-sm text-gray-500 italic mt-3 line-clamp-3">
                    « {message} »
                  </p>
                )}

                {item.montant_estime ? (
                  <div className="mt-3 bg-green-50 rounded-lg px-3 py-2.5">
                    <p className="text-xs text-green-800">
                      {montantLabel || "Montant estimé"}
                    </p>
                    <p className="text-lg font-bold text-green-700">
                      {item.montant_estime.toLocaleString("fr-FR")} €
                    </p>
                    {item.economie_estimee ? (
                      <p className="text-xs text-green-600 mt-0.5">
                        {item.economie_estimee.toLocaleString("fr-FR")} €/an d&apos;économie
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
