import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Navbar } from "@/components/Navbar";
import { ChatWidget } from "@/components/ChatWidget";
import { I18nProvider } from "@/lib/i18n";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Durin",
  description: "What the AI interpreted, what the engine verified, what the merchant authorized.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${mono.variable} app-bg font-sans`}>
        <I18nProvider>
          <Navbar />
          <main className="mx-auto max-w-5xl px-5 py-8">{children}</main>
          <ChatWidget />
        </I18nProvider>
      </body>
    </html>
  );
}
