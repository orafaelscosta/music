import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "AI Vocal Studio",
  description: "Sistema de geração de vocais por IA sobre instrumentais",
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
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
                    <svg
                      className="h-5 w-5 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
                      />
                    </svg>
                  </div>
                  <span className="text-lg font-bold text-white">
                    AI Vocal Studio
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
                    href="/docs"
                    className="text-sm text-gray-400 transition-colors hover:text-white"
                  >
                    Docs
                  </a>
                </nav>
              </div>
            </header>
            <main className="flex-1">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
