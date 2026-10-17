import { UserPlus } from "lucide-react";
import Link from "next/link";
import type { Decision } from "@/lib/api/contracts";

export const SUPPLIERS_PATH = "/proveedores";

/** An invoice from a supplier the policy does not list: say how to register it, for the next invoice. */
export function UnknownSupplierHint({ decision }: { decision: Decision }) {
  if (decision.beneficiary_id !== null || decision.status === "paid_human") return null;
  return (
    <p className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl bg-surface-2 px-3.5 py-3 text-[13.5px] text-ink-2">
      <span className="min-w-0 flex-1">
        {decision.supplier_name ?? "Este proveedor"} no está entre tus proveedores registrados. Si es tuyo, regístralo
        con su cuenta y las próximas facturas se decidirán con tus reglas.
      </span>
      <Link href={SUPPLIERS_PATH} className="inline-flex items-center gap-1.5 font-semibold text-brand underline-offset-4 hover:underline">
        <UserPlus aria-hidden className="size-4" /> Agregar proveedores
      </Link>
    </p>
  );
}
