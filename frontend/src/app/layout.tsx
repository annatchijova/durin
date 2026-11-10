import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Barlow_Condensed } from "next/font/google";
import { Navbar } from "@/components/Navbar";
import { ChatWidget } from "@/components/ChatWidget";
import { DemoNotice } from "@/components/DemoNotice";
import { DEMO_RECORDED_ON, demoEnabled } from "@/lib/demo";
import { I18nProvider } from "@/lib/i18n";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });
// Display face for the landing masthead, the same one /vertice uses.
const display = Barlow_Condensed({ subsets: ["latin"], weight: "700", variable: "--font-display" });

export const metadata: Metadata = {
  title: "Durin",
  description: "What the AI interpreted, what the engine verified, what the merchant authorized.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${mono.variable} ${display.variable} app-bg font-sans`}>
        <I18nProvider>
          <Navbar />
          {demoEnabled() && <DemoNotice recordedOn={DEMO_RECORDED_ON} />}
          <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>
          <ChatWidget />
        </I18nProvider>
      </body>
    </html>
  );
}
