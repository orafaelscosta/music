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
      <body className="font-sans">
        <Providers>
          <div className="flex min-h-screen flex-col">
            <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
              <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
                <a href="/" className="flex items-center gap-2">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src="/logo.svg" alt="ClovisAI" className="h-9 w-9 rounded-lg" />
                  <span className="text-lg font-bold text-white">
                    ClovisAI
                  </span>
                </a>
                <nav className="flex items-center gap-4">
                  <a
                    href="/"
                    className="text-sm text-gray-400 transition-colors hover:text-white"
                  >
                    Projetos
                  </a>
                  <a
                    href="/quick-start"
                    className="text-sm text-brand-400 transition-colors hover:text-brand-300"
                  >
                    Quick Start
                  </a>
                  <a
                    href="/settings"
                    className="text-sm text-gray-400 transition-colors hover:text-white"
                  >
                    Configurações
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
