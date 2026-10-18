import type { Metadata } from "next";
import { Suspense } from "react";
import { SupplierCorrection } from "@/components/corrections/supplier-correction";

// The link is a one-time secret: kept out of search engines and out of the Referer of any page it leads to.
export const metadata: Metadata = {
  title: "Corregir una factura",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

async function Correction({ params }: Pick<PageProps<"/proveedor/c/[token]">, "params">) {
  const { token } = await params;
  return <SupplierCorrection token={token} />;
}

export default function Page({ params }: PageProps<"/proveedor/c/[token]">) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-[640px] flex-col gap-4 px-4 py-8">
      <p className="text-[13px] font-semibold tracking-[0.08em] text-ink-3 uppercase">Custodio · corrección de factura</p>
      <Suspense>
        <Correction params={params} />
      </Suspense>
    </main>
  );
}
