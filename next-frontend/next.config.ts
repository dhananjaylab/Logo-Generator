import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.r2.dev",
      },
      {
        protocol: "https",
        hostname: process.env.R2_PUBLIC_DOMAIN?.replace("https://", "").replace("http://", "") ?? "",
      },
    ],
  },
};

export default nextConfig;
