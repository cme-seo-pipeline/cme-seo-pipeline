FICHIER = "espace-client/app/profil/page.tsx"

with open(FICHIER, "r", encoding="utf-8") as f:
    contenu = f.read()

# ============================================================
# PATCH 1 — Import Image (next/image)
# ============================================================
ancien1 = '''"use client";
import { useState, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import PasswordInput from "@/components/PasswordInput";'''

nouveau1 = '''"use client";
import { useState, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import PasswordInput from "@/components/PasswordInput";'''

if 'import Image from "next/image";' in contenu:
    print("⏭️  PATCH 1 (import Image) : deja present, ignore")
elif ancien1 not in contenu:
    print("❌ PATCH 1 (import Image) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien1, nouveau1, 1)
    print("✅ PATCH 1 (import Image) : ajoute")

# ============================================================
# PATCH 2 — Constante RESEAUX
# ============================================================
ancien2 = '''const API_URL = process.env.NEXT_PUBLIC_CLIENT_API_URL;'''

nouveau2 = ancien2 + '''
const RESEAUX = [
  {
    nom: "Facebook",
    image: "https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/07/Facebook_logo_comprendre-mon-energie.png",
    lien: "https://www.facebook.com/people/Comprendre-Mon-%C3%89nergie/61592180973793/",
  },
  {
    nom: "Instagram",
    image: "https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/08/image_instagram.png",
    lien: "https://www.instagram.com/cme262026/",
  },
  {
    nom: "LinkedIn",
    image: "https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/05/icone-linkedin-comprendre-mon-energie.jpg",
    lien: "https://www.linkedin.com/company/comprendre-mon-energie/",
  },
];'''

if "const RESEAUX" in contenu:
    print("⏭️  PATCH 2 (constante RESEAUX) : deja present, ignore")
elif ancien2 not in contenu:
    print("❌ PATCH 2 (constante RESEAUX) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien2, nouveau2, 1)
    print("✅ PATCH 2 (constante RESEAUX) : ajoutee")

# ============================================================
# PATCH 3 — Ouverture : envelopper le bloc "infos" dans un Fragment
# ============================================================
ancien3 = '''      {onglet === "infos" && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">'''

nouveau3 = '''      {onglet === "infos" && (
        <>
        <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">'''

if 'onglet === "infos" && (\n        <>' in contenu:
    print("⏭️  PATCH 3 (ouverture Fragment) : deja present, ignore")
elif ancien3 not in contenu:
    print("❌ PATCH 3 (ouverture Fragment) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien3, nouveau3, 1)
    print("✅ PATCH 3 (ouverture Fragment) : ajoutee")

# ============================================================
# PATCH 4 — Fermeture : nouvelle carte + fermeture du Fragment
# ============================================================
ancien4 = '''          <button
            onClick={() => handleSave(["nom", "prenom", "telephone", "adresse_postale"])}
            disabled={sauvegarde}
            className="w-full h-11 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
          >
            {sauvegarde ? "Enregistrement..." : "Enregistrer"}
          </button>
        </div>
      )}
      {onglet === "fournisseur" && ('''

nouveau4 = '''          <button
            onClick={() => handleSave(["nom", "prenom", "telephone", "adresse_postale"])}
            disabled={sauvegarde}
            className="w-full h-11 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
          >
            {sauvegarde ? "Enregistrement..." : "Enregistrer"}
          </button>
        </div>
        <div className="bg-white rounded-2xl border border-gray-200 p-6 mt-6">
          <h2 className="text-sm font-semibold text-gray-900 mb-1">Suivez-nous</h2>
          <p className="text-xs text-gray-500 mb-4">
            Restez informé de nos actualités sur tous nos canaux
          </p>
          <div className="divide-y divide-gray-100">
            {RESEAUX.map((reseau) => (
              <a
                key={reseau.nom}
                href={reseau.lien}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 py-3 hover:bg-gray-50 -mx-2 px-2 rounded-lg transition-colors"
              >
                <Image
                  src={reseau.image}
                  alt={reseau.nom}
                  width={32}
                  height={32}
                  className="rounded-lg object-cover"
                />
                <span className="flex-1 text-sm font-medium text-gray-900">{reseau.nom}</span>
                <span className="text-gray-300">›</span>
              </a>
            ))}
          </div>
        </div>
        </>
      )}
      {onglet === "fournisseur" && ('''

if "Suivez-nous" in contenu:
    print("⏭️  PATCH 4 (carte + fermeture Fragment) : deja present, ignore")
elif ancien4 not in contenu:
    print("❌ PATCH 4 (carte + fermeture Fragment) : ancre non trouvee")
else:
    contenu = contenu.replace(ancien4, nouveau4, 1)
    print("✅ PATCH 4 (carte + fermeture Fragment) : ajoutee")

with open(FICHIER, "w", encoding="utf-8") as f:
    f.write(contenu)

print("📝 Fichier sauvegarde :", FICHIER)
