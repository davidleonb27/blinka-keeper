import type { NextConfig } from "next";

// On Vercel the platform routes /api/v1 to the API service before Next sees it. Locally (and anywhere the
// binding sets API_INTERNAL_URL) Next forwards it, so the browser always calls the same relative path.
const apiUrl = process.env.API_INTERNAL_URL;

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return apiUrl ? [{ source: "/api/v1/:path*", destination: `${apiUrl}/api/v1/:path*` }] : [];
  },
};

export default nextConfig;
