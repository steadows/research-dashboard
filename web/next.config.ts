import type { NextConfig } from "next";

const API_BACKEND_URL =
  process.env.API_BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactCompiler: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
