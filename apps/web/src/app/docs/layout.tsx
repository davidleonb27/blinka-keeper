import type { Metadata } from "next";
import { DocsSidebar } from "@/components/site/docs-sidebar";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";

export const metadata: Metadata = {
  title: { default: "Documentación", template: "%s · Documentación de Blinka Keeper" },
  description: "Cómo usar, autoalojar, configurar e integrar Blinka Keeper, el agente de cuentas por pagar de código abierto.",
};

export default function DocsLayout({ children }: LayoutProps<"/docs">) {
  return (
    <div className="site min-h-dvh">
      <SiteHeader />
      <div className="mx-auto max-w-6xl px-4 pt-20 lg:pt-36 lg:grid lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-12">
        <aside className="min-w-0">
          <DocsSidebar />
        </aside>
        <main id="contenido" className="min-w-0 pt-6 lg:pt-8">
          {children}
        </main>
      </div>
      <SiteFooter />
    </div>
  );
}
