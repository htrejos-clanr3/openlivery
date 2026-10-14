import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import { ToastProvider } from "@/components/toast";
import { CarouselGenerationProvider } from "@/lib/carousel-generation-context";
import { LanguageProvider } from "@/lib/i18n";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });

export const metadata: Metadata = {
  title: "OpenLivery — AI agents for your agency",
  description: "Open source platform to build and manage AI agents.",
  icons: { icon: "/brand/app-logo-icon.png", apple: "/brand/app-logo-icon.png" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body className={geist.variable}>
        <LanguageProvider>
          <ToastProvider>
            <CarouselGenerationProvider>
              <AppShell>{children}</AppShell>
            </CarouselGenerationProvider>
          </ToastProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
