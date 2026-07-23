"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import PasswordInput from "@/components/PasswordInput";

const API_URL = process.env.NEXT_PUBLIC_CLIENT_API_URL;

function RegisterForm() {
  const { register, getToken } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [form, setForm] = useState({
    prenom: "",
    nom: "",
    email: "",
    telephone: "",
    password: "",
  });
  const [accepteCgu, setAccepteCgu] = useState(false);
  const [erreur, setErreur] = useState("");
  const [loading, setLoading] = useState(false);
  const [venantDunSimulateur, setVenantDunSimulateur] = useState(false);

  useEffect(() => {
    const prenom = searchParams.get("prenom") || "";
    const nom = searchParams.get("nom") || "";
    const email = searchParams.get("email") || "";
    const telephone = searchParams.get("telephone") || "";
    if (prenom || nom || email || telephone) {
      setForm((f) => ({ ...f, prenom, nom, email, telephone }));
      setVenantDunSimulateur(true);
    }
  }, [searchParams]);

  function update(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErreur("");

    if (form.password.length < 6) {
      setErreur("Le mot de passe doit contenir au moins 6 caractères.");
      return;
    }
    if (!accepteCgu) {
      setErreur("Merci d'accepter les conditions générales pour continuer.");
      return;
    }

    setLoading(true);
    try {
      await register(form);

      const leadDataRaw = searchParams.get("lead_data");
      if (leadDataRaw) {
        try {
          const leadData = JSON.parse(decodeURIComponent(leadDataRaw));
          const token = await getToken();
          if (token) {
            await fetch(`${API_URL}/leads`, {
              method: "POST",
              headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              },
              body: JSON.stringify(leadData),
            });
          }
        } catch {
          // silencieux : ne bloque jamais l'inscription
        }
      }

      router.push("/simulations");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Erreur lors de l'inscription.";
      setErreur(message);
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    "w-full h-11 px-3 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent";

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Créer un compte</h1>
        <p className="text-sm text-gray-500 mb-6">
          Suivez vos dossiers solaire, aides et énergie en un seul endroit
        </p>

        {venantDunSimulateur && (
          <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 mb-4 text-sm text-green-800">
            ✓ Vos informations ont été pré-remplies depuis votre simulation
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Prénom
              </label>
              <input
                type="text"
                required
                value={form.prenom}
                onChange={(e) => update("prenom", e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nom
              </label>
              <input
                type="text"
                required
                value={form.nom}
                onChange={(e) => update("nom", e.target.value)}
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              required
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
              className={inputClass}
              placeholder="vous@exemple.fr"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Téléphone
            </label>
            <input
              type="tel"
              required
              value={form.telephone}
              onChange={(e) => update("telephone", e.target.value)}
              className={inputClass}
              placeholder="06 12 34 56 78"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Mot de passe
            </label>
            <PasswordInput
              required
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              className={inputClass}
              placeholder="6 caractères minimum"
            />
          </div>

          <div className="flex items-start gap-2">
            <input
              type="checkbox"
              id="cgu"
              checked={accepteCgu}
              onChange={(e) => setAccepteCgu(e.target.checked)}
              className="mt-1 h-4 w-4 accent-green-600"
            />
            <label htmlFor="cgu" className="text-sm text-gray-600">
              J&apos;accepte les{" "}
              <a
                href="https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-green-600 font-medium hover:underline"
              >
                conditions générales et la politique de confidentialité
              </a>
            </label>
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
            {loading ? "Création en cours..." : "Créer mon compte"}
          </button>
        </form>

        <p className="text-sm text-gray-500 mt-6 text-center">
          Déjà un compte ?{" "}
          <Link href="/login" className="text-green-600 font-medium hover:underline">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div className="flex-1 flex items-center justify-center">
          <p className="text-gray-500">Chargement...</p>
        </div>
      }
    >
      <RegisterForm />
    </Suspense>
  );
}
