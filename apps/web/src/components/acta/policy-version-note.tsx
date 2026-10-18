import { History } from "lucide-react";
import type { LedgerEntry } from "@/lib/api/contracts";

const DECIDING_KINDS = new Set(["decision", "approval"]);

function numberOf(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

/** Which policy version the decision was taken with, and how a person approved it, as the ledger holds it. */
export function PolicyVersionNote({ ledger }: { ledger: LedgerEntry[] }) {
  const last = ledger.filter((entry) => DECIDING_KINDS.has(entry.kind)).at(-1);
  const version = numberOf(last?.payload.policy_version);
  if (!last || version === null) return null;
  const mode = last.payload.approval_mode;
  const agreementVersion = numberOf(last.payload.agreement_policy_version);
  return (
    <p className="flex flex-wrap items-center gap-x-1.5 text-[13px] text-ink-2">
      <History aria-hidden className="size-3.5 text-ink-3" />
      Decidida con la política <b className="text-ink">v{version}</b>
      {mode === "once" ? <span>· aprobada sólo esta vez, sin cambiar la política</span> : null}
      {mode === "agreement_updated" && agreementVersion !== null ? (
        <span>
          · al aprobarla se actualizó el acuerdo en la <b className="text-ink">v{agreementVersion}</b>
        </span>
      ) : null}
    </p>
  );
}
