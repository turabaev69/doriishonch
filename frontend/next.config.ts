import type { NextConfig } from "next";

// Backend manzili (server tomonida). Frontend /api/* soʻrovlarini shu yerga yoʻnaltiradi.
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  devIndicators: false,
  // Docker obrazi uchun (NEXT_STANDALONE=1); ./start.sh esa oddiy "next start" ishlatadi
  output: process.env.NEXT_STANDALONE ? "standalone" : undefined,
  poweredByHeader: false,
  async redirects() {
    return ["/inspektor/:path*", "/bojxona/:path*", "/manufacturer/:path*", "/kirish/:path*"].map(source => ({
      source,
      destination: "/",
      permanent: false,
    }));
  },
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        // Kamera faqat oʻz saytimizga; Telegram Mini App ichida ochilishi uchun frame-ancestors cheklanmaydi
        { key: "Permissions-Policy", value: "camera=(self), geolocation=(self), microphone=()" },
      ],
    }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/:path*` }];
  },
};

export default nextConfig;
