import type { Metadata } from "next";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import { VerifyPage } from "@/components/verify/verify-page";

export const metadata: Metadata = {
  title: "Verificar un recibo",
  description: "Comprueba la firma Ed25519 de un recibo de Blinka Keeper con su clave pública, sin acceso al sistema.",
};

export default function VerifyReceiptPage() {
  return (
    <div className="site min-h-dvh">
      <SiteHeader />
      <main id="contenido">
        <VerifyPage />
      </main>
      <SiteFooter />
    </div>
  );
}
