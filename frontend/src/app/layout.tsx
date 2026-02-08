import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";
import ToastContainer from "@/components/Toast";

export const metadata: Metadata = {
  title: "ClovisAI - Music Creation",
  description: "Sistema de criação musical com IA",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="font-sans noise-overlay">
        <Providers>
          <div className="flex min-h-screen flex-col mesh-gradient">
            <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-gray-950/70 backdrop-blur-xl">
              <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
                <a href="/" className="group flex items-center gap-2.5">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/logo.svg"
                    alt="ClovisAI"
                    className="h-8 w-8 rounded-lg transition-transform duration-200 group-hover:scale-110"
                  />
                  <span className="text-base font-bold tracking-tight text-white">
                    Clovis<span className="bg-gradient-to-r from-brand-400 to-purple-400 bg-clip-text text-transparent">AI</span>
                  </span>
                </a>
                <nav className="flex items-center gap-1">
                  <a
                    href="/"
                    className="rounded-lg px-3 py-1.5 text-sm text-gray-400 transition-all duration-200 hover:bg-white/[0.05] hover:text-white"
                  >
                    Projetos
                  </a>
                  <a
                    href="/quick-start"
                    className="rounded-lg px-3 py-1.5 text-sm font-medium text-brand-400 transition-all duration-200 hover:bg-brand-500/10 hover:text-brand-300"
                  >
                    Quick Start
                  </a>
                  <a
                    href="/settings"
                    className="rounded-lg px-3 py-1.5 text-sm text-gray-400 transition-all duration-200 hover:bg-white/[0.05] hover:text-white"
                  >
                    Config
                  </a>
                </nav>
              </div>
            </header>
            <main className="flex-1">{children}</main>
          </div>
          <ToastContainer />
        </Providers>
      </body>
    </html>
  );
}
