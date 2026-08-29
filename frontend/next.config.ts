import type { NextConfig } from "next";

const api = process.env.NEXT_PUBLIC_API_URL;
if (!api) {
  throw new Error(
    "NEXT_PUBLIC_API_URL is required. Copy frontend/.env.example to frontend/.env.local and set the API base URL.",
  );
}

const nextConfig: NextConfig = {
  eslint: { ignoreDuringBuilds: true },
  async rewrites() {
    return [
      { source: "/v1/:path*", destination: `${api}/v1/:path*` },
      { source: "/health", destination: `${api}/health` },
      { source: "/ready", destination: `${api}/ready` },
    ];
  },
};

export default nextConfig;
