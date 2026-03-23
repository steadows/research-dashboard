import { Suspense } from "react";
import type { Metadata } from "next";
import { Inter, Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { MotionProvider } from "@/components/effects/MotionProvider";
import { BackgroundSystem } from "@/components/effects/BackgroundSystem";
import { ScanLines } from "@/components/effects/ScanLines";
import { CursorEffect } from "@/components/effects/CursorEffect";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "R.I.D. | Research Intelligence Dashboard",
  description: "Tactical intelligence HUD for research insights",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable} dark h-full`}
    >
      <body className="min-h-full bg-bg-base text-text-primary font-sans antialiased">
        <MotionProvider>
          <BackgroundSystem />
          <ScanLines />
          <CursorEffect />
          <Header />
          <div className="flex min-h-screen pt-16">
            <Sidebar />
            <main className="flex-1 ml-0 md:ml-20 p-6 overflow-x-hidden relative z-10" aria-label="Page content">
              <Suspense fallback={null}>
                {children}
              </Suspense>
            </main>
          </div>
        </MotionProvider>
      </body>
    </html>
  );
}
