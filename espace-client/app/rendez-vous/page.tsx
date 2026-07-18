"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_CLIENT_API_URL;

export default function RendezVousPage() {
  const { user, loading, getToken } = useAuth();
  const router = useRouter();

  const [sujet, setSujet] = useState("");
  const [message, setMessage] = useState("");
  const [disponibilites, setDisponibilites] = useState("");
  const [envoye, setEnvoye] = useState(false);
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErreur("");
    setEnvoiEnCours(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/leads`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tool: "rendez-vous-expert",
          montant_estime: 0,
          economie_estimee: 0,
          details: { sujet, message, disponibilites },
        }),
      });
      if (!res.ok) throw new Error("Erreur");
      setEnvoye(true);
    } catch {
      setErreur("Une erreur est survenue, merci de réessayer.");
    } finally {
      setEnvoiEnCours(false);
    }
  }

  if (loading || !user) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-gray-500">Chargement...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        {envoye ? (
          <div className="text-center py-6">
            <div className="w-14 h-14 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-2xl mx-auto mb-4">
              ✓
            </div>
            <h1 className="text-xl font-bold text-gray-900 mb-2">
              Demande envoyée !
            </h1>
            <p className="text-sm text-gray-500">
              Un expert vous recontacte sous 48h pour convenir d&apos;un
              rendez-vous. Vous pouvez suivre cette demande dans{" "}
              <span className="font-medium">Mes simulations</span>.
            </p>
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-bold text-gray-900 mb-1">
              Rendez-vous avec un expert
            </h1>
            <p className="text-sm text-gray-500 mb-6">
              Décrivez votre besoin, un conseiller vous recontacte pour fixer
              un créneau.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sujet
                </label>
                <select
                  required
                  value={sujet}
                  onChange={(e) => setSujet(e.target.value)}
                  className="w-full h-11 px-3 border border-gray-300 rounded-lg bg-white text-gray-900"
                >
                  <option value="">Sélectionnez un sujet</option>
                  <option value="solaire">Panneaux solaires</option>
                  <option value="renovation">Rénovation énergétique</option>
                  <option value="aides">Aides & subventions</option>
                  <option value="contrat">Contrat gaz/électricité</option>
                  <option value="autre">Autre</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Votre message
                </label>
                <textarea
                  required
                  rows={4}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 resize-none"
                  placeholder="Décrivez votre projet ou votre question..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Disponibilités (optionnel)
                </label>
                <input
                  type="text"
                  value={disponibilites}
                  onChange={(e) => setDisponibilites(e.target.value)}
                  className="w-full h-11 px-3 border border-gray-300 rounded-lg bg-white text-gray-900"
                  placeholder="Ex : en semaine après 18h"
                />
              </div>

              {erreur && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {erreur}
                </p>
              )}

              <button
                type="submit"
                disabled={envoiEnCours}
                className="w-full h-11 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
              >
                {envoiEnCours ? "Envoi..." : "Envoyer ma demande"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
