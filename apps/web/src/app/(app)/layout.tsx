import { AppNav } from "@/components/shell/app-nav";

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="mx-auto grid min-h-dvh max-w-[1440px] grid-cols-1 px-4 lg:grid-cols-[240px_minmax(0,1fr)] lg:gap-6">
      <AppNav />
      <main id="contenido" className="min-w-0 pt-4 pb-16 lg:pt-6">
        {children}
      </main>
    </div>
  );
}
