import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/components/providers/providers";
import "./globals.css";

// One typeface: Inter for the interface, the text and (heavy, tightly tracked) the titles; the system monospace for
// figures and code. Changing it means changing this call and the font tokens in globals.css; nothing else names a font.
const sans = Inter({ subsets: ["latin"], display: "swap", variable: "--font-sans", preload: true });

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
    { media: "(prefers-color-scheme: light)", color: "#f7f7f4" },
    { media: "(prefers-color-scheme: dark)", color: "#111720" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" suppressHydrationWarning className={sans.variable}>
      <body className="min-h-dvh">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
