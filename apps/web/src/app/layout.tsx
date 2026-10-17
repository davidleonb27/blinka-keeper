import type { Metadata, Viewport } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import { Providers } from "@/components/providers/providers";
import "./globals.css";

// The type pair: Inter for the interface and text, Source Serif 4 for large titles. Changing the pair means changing
// these two calls and the font tokens in globals.css; nothing else names a font.
const sans = Inter({ subsets: ["latin"], display: "swap", variable: "--font-sans" });
const serif = Source_Serif_4({ subsets: ["latin"], display: "swap", variable: "--font-serif", preload: true });

export const metadata: Metadata = {
  title: { default: "Custodio · el agente de cuentas por pagar de código abierto", template: "%s · Custodio" },
  description:
    "Custodio revisa las facturas de tu empresa: el modelo lee, el código decide y una persona autoriza. Código abierto bajo licencia MIT: úsalo en la demo o autoalójalo con un comando.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#edf2f2" },
    { media: "(prefers-color-scheme: dark)", color: "#0a1012" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" suppressHydrationWarning className={`${sans.variable} ${serif.variable}`}>
      <body className="min-h-dvh">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
