import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Autorise le HMR (rechargement a chaud) depuis l'URL de preview Cloud Shell.
  // A retirer/ajuster une fois le vrai domaine de production connu.
  allowedDevOrigins: [
    "*.cloudshell.dev",
    "3000-cs-bb7a6b2f-1b3b-479a-b551-5cb6bbe543ea.cs-europe-west1-haha.cloudshell.dev",
  ],
};

export default nextConfig;
