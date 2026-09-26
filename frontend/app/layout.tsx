import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";
import { AppHeader } from "@/components/AppHeader";
import { Icon } from "@/components/Icon";
import { InstallHint } from "@/components/InstallHint";

export const viewport: Viewport = { themeColor: "#236449" };
export const metadata: Metadata = {
  title: { default: "DoriIshonch — har bir qutida ishonch", template: "%s · DoriIshonch" },
  applicationName: "DoriIshonch",
  appleWebApp: { capable: true, title: "DoriIshonch", statusBarStyle: "default" },
  icons: { icon: "/icon-192.png", apple: "/apple-touch-icon.png" },
  description: "Dori qutisini tekshiring, uning tarixini bilib oling va yaqin dorixonalarni toping. Sodda, tushunarli, oʻzbek tilida.",
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="uz"><body>
    <AppHeader />
    <main id="main-content" className="app-main" tabIndex={-1}>{children}</main>
    <footer className="app-footer">
      <div className="footer-brand"><Icon name="shield" size={20} /><span>DoriIshonch</span><span className="footer-tagline">Har bir qutida ishonch.</span></div>
      <div className="footer-links"><Link href="/demo-kodlar">Namuna bilan sinash</Link><Link href="/yordamchi">Yordam kerakmi?</Link></div>
      <p>Demo. Quti tekshiruvi dori tarkibini tasdiqlamaydi.</p>
    </footer><InstallHint />
  </body></html>;
}
