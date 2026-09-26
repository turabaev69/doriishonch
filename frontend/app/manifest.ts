import type { MetadataRoute } from "next";

// Telefonda "Bosh ekranga qoʻshish" orqali ilova kabi ochiladi
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "DoriIshonch AI",
    short_name: "DoriIshonch",
    description: "Dori qutisini skanerlang: qayerdan kelgani va oldin sotilmaganini tekshiring",
    start_url: "/",
    display: "standalone",
    background_color: "#f3f6f8",
    theme_color: "#0e8c78",
    orientation: "portrait",
    lang: "uz",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
