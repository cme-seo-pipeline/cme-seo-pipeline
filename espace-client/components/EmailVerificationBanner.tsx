"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

export default function EmailVerificationBanner() {
  const { user, emailVerified, resendVerification, refreshEmailStatus } = useAuth();
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  const [rafraichissementEnCours, setRafraichissementEnCours] = useState(false);
  const [message, setMessage] = useState("");

  if (!user || emailVerified) return null;

  async function handleResend() {
    setEnvoiEnCours(true);
    setMessage("");
    try {
      await resendVerification();
      setMessage("Email renvoyé !");
    } catch {
      setMessage("Erreur, réessayez dans quelques minutes.");
    } finally {
      setEnvoiEnCours(false);
    }
  }

  async function handleRefresh() {
    setRafraichissementEnCours(true);
    setMessage("");
    try {
      await refreshEmailStatus();
    } finally {
      setRafraichissementEnCours(false);
    }
  }

  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-2.5">
      <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-amber-800">
          📧 Vérifiez votre adresse email — un lien de confirmation a été envoyé à{" "}
          <strong>{user.email}</strong>.
          {message && <span className="ml-2 font-medium">{message}</span>}
        </p>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={handleRefresh}
            disabled={rafraichissementEnCours}
            className="text-xs font-medium text-amber-900 bg-amber-100 hover:bg-amber-200 px-3 py-1.5 rounded-lg disabled:opacity-60 transition-colors"
          >
            {rafraichissementEnCours ? "..." : "J'ai vérifié"}
          </button>
          <button
            onClick={handleResend}
            disabled={envoiEnCours}
            className="text-xs font-medium text-amber-700 hover:underline px-2 disabled:opacity-60"
          >
            {envoiEnCours ? "Envoi..." : "Renvoyer l'email"}
          </button>
        </div>
      </div>
    </div>
  );
}
