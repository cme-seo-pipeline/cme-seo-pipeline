"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export default function ForgotPasswordPage() {
  const { resetPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [envoye, setEnvoye] = useState(false);
  const [erreur, setErreur] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErreur("");
    setLoading(true);
    try {
      await resetPassword(email);
      setEnvoye(true);
    } catch {
      // Message volontairement generique : ne pas confirmer/infirmer
      // l'existence d'un compte pour cet email (bonne pratique securite).
      setEnvoye(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex-1 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        {envoye ? (
          <div className="text-center py-2">
            <div className="w-14 h-14 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-2xl mx-auto mb-4">
              ✓
            </div>
            <h1 className="text-xl font-bold text-gray-900 mb-2">Email envoyé</h1>
            <p className="text-sm text-gray-500">
              Si un compte existe avec l&apos;adresse <strong>{email}</strong>, vous
              recevrez un lien pour réinitialiser votre mot de passe. Vérifiez vos
              spams si vous ne le voyez pas.
            </p>
            <Link
              href="/login"
              className="inline-block mt-6 text-green-600 font-medium hover:underline text-sm"
            >
              Retour à la connexion
            </Link>
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-bold text-gray-900 mb-1">
              Mot de passe oublié
            </h1>
            <p className="text-sm text-gray-500 mb-6">
              Indiquez votre email, nous vous enverrons un lien de réinitialisation.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-11 px-3 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  placeholder="vous@exemple.fr"
                />
              </div>

              {erreur && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {erreur}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full h-11 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
              >
                {loading ? "Envoi..." : "Envoyer le lien"}
              </button>
            </form>

            <p className="text-sm text-gray-500 mt-6 text-center">
              <Link href="/login" className="text-green-600 font-medium hover:underline">
                Retour à la connexion
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
