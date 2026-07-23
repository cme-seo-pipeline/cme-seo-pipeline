"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import PasswordInput from "@/components/PasswordInput";

const API_URL = process.env.NEXT_PUBLIC_CLIENT_API_URL;

interface Profil {
  nom?: string;
  prenom?: string;
  email?: string;
  telephone?: string;
  adresse_postale?: string;
  fournisseurs?: {
    nb_energies?: "1" | "2";
    gaz?: string;
    electricite?: string;
  };
}

const FOURNISSEURS_LISTE = [
  "EDF", "Engie", "TotalEnergies", "Eni", "Ekwateur",
  "Mint Énergie", "OHM Énergie", "Alterna", "Vattenfall", "Autre",
];

function messageErreurMdp(err: unknown): string {
  const code = err instanceof Error ? err.message : "";
  if (code.includes("wrong-password") || code.includes("invalid-credential")) {
    return "Mot de passe actuel incorrect.";
  }
  if (code.includes("weak-password")) {
    return "Le nouveau mot de passe doit contenir au moins 6 caractères.";
  }
  if (code.includes("requires-recent-login")) {
    return "Par sécurité, merci de vous reconnecter puis de réessayer.";
  }
  return "Une erreur est survenue, merci de réessayer.";
}

function ProfilContent() {
  const { user, loading, getToken, changePassword, deleteAccount } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [onglet, setOnglet] = useState<"infos" | "fournisseur" | "securite">("infos");
  const [profil, setProfil] = useState<Profil>({});
  const [dataLoading, setDataLoading] = useState(true);
  const [sauvegarde, setSauvegarde] = useState(false);
  const [succes, setSucces] = useState(false);
  const [erreur, setErreur] = useState("");

  const [mdpActuel, setMdpActuel] = useState("");
  const [mdpNouveau, setMdpNouveau] = useState("");
  const [mdpConfirmation, setMdpConfirmation] = useState("");
  const [mdpEnCours, setMdpEnCours] = useState(false);
  const [mdpErreur, setMdpErreur] = useState("");
  const [mdpSucces, setMdpSucces] = useState(false);

  const [suppressionOuverte, setSuppressionOuverte] = useState(false);
  const [confirmationTexte, setConfirmationTexte] = useState("");
  const [suppressionEnCours, setSuppressionEnCours] = useState(false);
  const [suppressionErreur, setSuppressionErreur] = useState("");

  useEffect(() => {
    if (searchParams.get("tab") === "fournisseur") {
      setOnglet("fournisseur");
    }
  }, [searchParams]);

  const fetchProfil = useCallback(async () => {
    setDataLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setProfil(data);
      }
    } catch {
      setErreur("Impossible de charger votre profil.");
    } finally {
      setDataLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
      return;
    }
    if (user) fetchProfil();
  }, [user, loading, router, fetchProfil]);

  function update<K extends keyof Profil>(champ: K, valeur: Profil[K]) {
    setProfil((p) => ({ ...p, [champ]: valeur }));
    setSucces(false);
  }

  function updateFournisseur(champ: string, valeur: string) {
    setProfil((p) => ({
      ...p,
      fournisseurs: { ...p.fournisseurs, [champ]: valeur },
    }));
    setSucces(false);
  }

  async function handleSave(champs: (keyof Profil)[]) {
    setSauvegarde(true);
    setErreur("");
    setSucces(false);
    try {
      const token = await getToken();
      const payload: Partial<Profil> = {};
      champs.forEach((c) => {
        (payload as Record<string, unknown>)[c] = profil[c];
      });
      const res = await fetch(`${API_URL}/users/me`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error();
      setSucces(true);
    } catch {
      setErreur("La sauvegarde a échoué, merci de réessayer.");
    } finally {
      setSauvegarde(false);
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setMdpErreur("");
    setMdpSucces(false);

    if (mdpNouveau.length < 6) {
      setMdpErreur("Le nouveau mot de passe doit contenir au moins 6 caractères.");
      return;
    }
    if (mdpNouveau !== mdpConfirmation) {
      setMdpErreur("Les deux mots de passe ne correspondent pas.");
      return;
    }

    setMdpEnCours(true);
    try {
      await changePassword(mdpActuel, mdpNouveau);
      setMdpSucces(true);
      setMdpActuel("");
      setMdpNouveau("");
      setMdpConfirmation("");
    } catch (err) {
      setMdpErreur(messageErreurMdp(err));
    } finally {
      setMdpEnCours(false);
    }
  }

  async function handleDeleteAccount() {
    if (confirmationTexte !== "SUPPRIMER") {
      setSuppressionErreur('Merci de saisir exactement "SUPPRIMER" pour confirmer.');
      return;
    }
    setSuppressionErreur("");
    setSuppressionEnCours(true);
    try {
      await deleteAccount();
      router.push("/login");
    } catch {
      setSuppressionErreur("Une erreur est survenue, merci de réessayer.");
      setSuppressionEnCours(false);
    }
  }

  if (loading || dataLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-gray-500">Chargement...</p>
      </div>
    );
  }

  const inputClass =
    "w-full h-11 px-3 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500";

  const nbEnergies = profil.fournisseurs?.nb_energies || "1";

  return (
    <div className="flex-1 max-w-2xl w-full mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Mon profil</h1>

      <div className="flex gap-1 mb-6 border-b border-gray-200">
        <button
          onClick={() => setOnglet("infos")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            onglet === "infos"
              ? "border-green-600 text-green-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Mes informations
        </button>
        <button
          onClick={() => setOnglet("fournisseur")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            onglet === "fournisseur"
              ? "border-green-600 text-green-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Fournisseur
        </button>
        <button
          onClick={() => setOnglet("securite")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            onglet === "securite"
              ? "border-green-600 text-green-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Sécurité
        </button>
      </div>

      {onglet !== "securite" && erreur && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-4">
          {erreur}
        </p>
      )}
      {onglet !== "securite" && succes && (
        <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2 mb-4">
          ✓ Enregistré avec succès
        </p>
      )}

      {onglet === "infos" && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Prénom</label>
              <input
                type="text"
                value={profil.prenom || ""}
                onChange={(e) => update("prenom", e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nom</label>
              <input
                type="text"
                value={profil.nom || ""}
                onChange={(e) => update("nom", e.target.value)}
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={profil.email || ""}
              disabled
              className={`${inputClass} bg-gray-50 text-gray-400 cursor-not-allowed`}
            />
            <p className="text-xs text-gray-400 mt-1">
              L&apos;email ne peut pas être modifié
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Téléphone</label>
            <input
              type="tel"
              value={profil.telephone || ""}
              onChange={(e) => update("telephone", e.target.value)}
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Adresse postale</label>
            <input
              type="text"
              value={profil.adresse_postale || ""}
              onChange={(e) => update("adresse_postale", e.target.value)}
              className={inputClass}
              placeholder="Numéro, rue, code postal, ville"
            />
          </div>

          <button
            onClick={() => handleSave(["nom", "prenom", "telephone", "adresse_postale"])}
            disabled={sauvegarde}
            className="w-full h-11 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
          >
            {sauvegarde ? "Enregistrement..." : "Enregistrer"}
          </button>
        </div>
      )}

      {onglet === "fournisseur" && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Combien d&apos;énergies utilisez-vous ?
            </label>
            <div className="flex gap-3">
              <button
                onClick={() => updateFournisseur("nb_energies", "1")}
                className={`flex-1 h-11 rounded-lg text-sm font-medium border-2 transition-colors ${
                  nbEnergies === "1"
                    ? "border-green-600 bg-green-50 text-green-700"
                    : "border-gray-200 text-gray-600"
                }`}
              >
                1 seule énergie
              </button>
              <button
                onClick={() => updateFournisseur("nb_energies", "2")}
                className={`flex-1 h-11 rounded-lg text-sm font-medium border-2 transition-colors ${
                  nbEnergies === "2"
                    ? "border-green-600 bg-green-50 text-green-700"
                    : "border-gray-200 text-gray-600"
                }`}
              >
                Gaz + Électricité
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {nbEnergies === "2" ? "Fournisseur Électricité" : "Fournisseur"}
            </label>
            <select
              value={profil.fournisseurs?.electricite || ""}
              onChange={(e) => updateFournisseur("electricite", e.target.value)}
              className={inputClass}
            >
              <option value="">Sélectionnez...</option>
              {FOURNISSEURS_LISTE.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>

          {nbEnergies === "2" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fournisseur Gaz
              </label>
              <select
                value={profil.fournisseurs?.gaz || ""}
                onChange={(e) => updateFournisseur("gaz", e.target.value)}
                className={inputClass}
              >
                <option value="">Sélectionnez...</option>
                {FOURNISSEURS_LISTE.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => handleSave(["fournisseurs"])}
            disabled={sauvegarde}
            className="w-full h-11 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
          >
            {sauvegarde ? "Enregistrement..." : "Enregistrer"}
          </button>
        </div>
      )}

      {onglet === "securite" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-900 mb-1">
              Changer mon mot de passe
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              Par sécurité, indiquez votre mot de passe actuel avant de le modifier.
            </p>

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Mot de passe actuel
                </label>
                <PasswordInput
                  required
                  value={mdpActuel}
                  onChange={(e) => setMdpActuel(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nouveau mot de passe
                </label>
                <PasswordInput
                  required
                  value={mdpNouveau}
                  onChange={(e) => setMdpNouveau(e.target.value)}
                  className={inputClass}
                  placeholder="6 caractères minimum"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Confirmer le nouveau mot de passe
                </label>
                <PasswordInput
                  required
                  value={mdpConfirmation}
                  onChange={(e) => setMdpConfirmation(e.target.value)}
                  className={inputClass}
                />
              </div>

              {mdpErreur && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {mdpErreur}
                </p>
              )}
              {mdpSucces && (
                <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                  ✓ Mot de passe modifié avec succès
                </p>
              )}

              <button
                type="submit"
                disabled={mdpEnCours}
                className="w-full h-11 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
              >
                {mdpEnCours ? "Modification..." : "Modifier le mot de passe"}
              </button>
            </form>
          </div>

          {/* Zone dangereuse */}
          <div className="bg-white rounded-2xl border border-red-200 p-6">
            <h2 className="text-sm font-semibold text-red-700 mb-1">Zone dangereuse</h2>
            <p className="text-xs text-gray-500 mb-4">
              La suppression de votre compte est définitive et supprime l&apos;ensemble
              de vos données (profil, dossiers, historique). Cette action est
              irréversible.
            </p>

            {!suppressionOuverte ? (
              <button
                onClick={() => setSuppressionOuverte(true)}
                className="text-sm font-medium text-red-600 border border-red-300 hover:bg-red-50 rounded-lg px-4 py-2 transition-colors"
              >
                Supprimer mon compte
              </button>
            ) : (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-3">
                <p className="text-sm text-red-800">
                  Pour confirmer, saisissez <strong>SUPPRIMER</strong> ci-dessous :
                </p>
                <input
                  type="text"
                  value={confirmationTexte}
                  onChange={(e) => setConfirmationTexte(e.target.value)}
                  className="w-full h-11 px-3 border border-red-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="SUPPRIMER"
                />
                {suppressionErreur && (
                  <p className="text-sm text-red-700">{suppressionErreur}</p>
                )}
                <div className="flex gap-2">
                  <button
                    onClick={handleDeleteAccount}
                    disabled={suppressionEnCours}
                    className="flex-1 h-11 bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
                  >
                    {suppressionEnCours ? "Suppression..." : "Confirmer la suppression"}
                  </button>
                  <button
                    onClick={() => {
                      setSuppressionOuverte(false);
                      setConfirmationTexte("");
                      setSuppressionErreur("");
                    }}
                    disabled={suppressionEnCours}
                    className="h-11 px-4 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Annuler
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ProfilPage() {
  return (
    <Suspense
      fallback={
        <div className="flex-1 flex items-center justify-center">
          <p className="text-gray-500">Chargement...</p>
        </div>
      }
    >
      <ProfilContent />
    </Suspense>
  );
}
