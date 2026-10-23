import type { NextConfig } from "next";

const backendTarget = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  agentRules: false,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
