import { useMemo } from "react";
import { encodeQr } from "@/lib/qr";
import { cn } from "@/lib/utils";

/** The spec asks for four light modules around the code so a camera finds its edges. */
const QUIET_ZONE = 4;

function modulesPath(modules: boolean[][]): string {
  return modules
    .flatMap((row, y) => row.map((dark, x) => (dark ? `M${x + QUIET_ZONE} ${y + QUIET_ZONE}h1v1h-1z` : "")))
    .join("");
}

/** Always dark on white, whatever the theme: phone cameras read that contrast best. */
export function QrCode({ value, className }: { value: string; className?: string }) {
  const { size, path } = useMemo(() => {
    const code = encodeQr(value);
    return { size: code.size + QUIET_ZONE * 2, path: modulesPath(code.modules) };
  }, [value]);
  return (
    <svg
      role="img"
      aria-label={`Código QR a ${value}`}
      viewBox={`0 0 ${size} ${size}`}
      shapeRendering="crispEdges"
      className={cn("block aspect-square rounded-xl bg-white", className)}
    >
      <path d={path} fill="#000" />
    </svg>
  );
}
