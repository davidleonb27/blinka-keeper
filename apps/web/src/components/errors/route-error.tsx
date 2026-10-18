"use client";

import { RotateCw, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { reloadForNewDeploy, shouldReloadForNewDeploy } from "@/lib/stale-deploy";

/** What a page shows instead of crashing: a plain explanation, a retry and a way back, never a blank screen. */
export function RouteError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const [reloading] = useState(() => shouldReloadForNewDeploy(error));
  useEffect(() => {
    if (reloading) reloadForNewDeploy();
  }, [reloading]);

  if (reloading) {
    return (
      <p role="status" className="card-surface m-4 p-5 text-ink-2">
        Hay una versión nueva de Blinka Keeper. Actualizando…
      </p>
    );
  }
  return (
    <div role="alert" className="card-surface mx-auto my-10 flex max-w-xl flex-col items-start gap-3 p-6">
      <p className="flex items-center gap-2 font-semibold">
        <TriangleAlert aria-hidden className="size-4 text-esc" />
        Esta parte no cargó
      </p>
      <p className="text-ink-2">
        No se hizo ningún pago ni cambio. Vuelve a intentarlo; si sigue igual, recarga la página.
        {error.digest ? <span className="mt-1 block font-mono text-[12px] text-ink-3">Código: {error.digest}</span> : null}
      </p>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={reset}>
          <RotateCw aria-hidden /> Reintentar
        </Button>
        <Button size="sm" variant="outline" onClick={() => window.location.reload()}>
          Recargar la página
        </Button>
        <Button size="sm" variant="ghost" asChild>
          <Link href="/panel">Ir al panel</Link>
        </Button>
      </div>
    </div>
  );
}
