import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { Providers } from "@/components/providers/providers";
import "./globals.css";

// Blinka's type pair (docs/design-system/blinka), self-hosted: Inter ("Blinka Inter") for the interface and titles,
// Geist Mono for figures, codes and ids. Changing it means changing these two calls and the font tokens in
// globals.css; nothing else names a font.
const sans = localFont({
  src: "./fonts/blinka-inter-latin-variable.woff2",
  weight: "100 900",
  display: "swap",
  variable: "--font-sans",
});
const mono = localFont({
  src: "./fonts/geist-mono-latin-variable.woff2",
  weight: "100 900",
  display: "swap",
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: { default: "Blinka Keeper · el agente de cuentas por pagar de código abierto", template: "%s · Blinka Keeper" },
  description:
    "Blinka Keeper revisa las facturas de tu empresa: el modelo lee, el código decide y una persona autoriza. Código abierto bajo licencia MIT: úsalo en la demo o autoalójalo con un comando.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f7f7f4" },
    { media: "(prefers-color-scheme: dark)", color: "#111720" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" suppressHydrationWarning className={`${sans.variable} ${mono.variable}`}>
      <body className="min-h-dvh">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
