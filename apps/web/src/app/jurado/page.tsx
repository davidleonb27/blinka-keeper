import type { Metadata } from "next";
import { JudgePage } from "@/components/judge/judge-page";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";

export const metadata: Metadata = {
  title: "Guía para el jurado",
  description: "Custodio frente a la rúbrica de la Hackathon 30X: cada afirmación con el enlace que la prueba en el producto.",
};

export default function JuryPage() {
  return (
    <div className="site min-h-dvh">
      <SiteHeader />
      <main id="contenido">
        <JudgePage />
      </main>
      <SiteFooter />
    </div>
  );
}
