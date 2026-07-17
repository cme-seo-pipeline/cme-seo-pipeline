import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  allowedDevOrigins: [
    "*.cloudshell.dev",
  ],

  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "www.comprendre-mon-energie.fr",
      },
    ],
  },
};

export default nextConfig;
