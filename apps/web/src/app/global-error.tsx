"use client";

import { useEffect } from "react";
import { reloadForNewDeploy, shouldReloadForNewDeploy } from "@/lib/stale-deploy";

// Replaces the root layout when even it fails, so it carries its own html and plain styles.
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    if (shouldReloadForNewDeploy(error)) reloadForNewDeploy();
  }, [error]);
  return (
    <html lang="es">
      <body style={{ fontFamily: "system-ui, sans-serif", background: "#f7f7f4", color: "#1c253a", margin: 0 }}>
        <main style={{ maxWidth: 520, margin: "15vh auto", padding: 24 }}>
          <h1 style={{ fontSize: 22 }}>Blinka Keeper no cargó</h1>
          <p>No se hizo ningún pago ni cambio. Recarga la página para continuar.</p>
          <p style={{ display: "flex", gap: 8 }}>
            <button type="button" onClick={reset}>Reintentar</button>
            <button type="button" onClick={() => window.location.reload()}>Recargar</button>
          </p>
        </main>
      </body>
    </html>
  );
}
