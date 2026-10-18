import { Check, X } from "lucide-react";
import type { FieldCrossCheck, ReaderValue, ReadingCrossCheck } from "@/lib/api/contracts";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

const FIELD_LABELS: Record<FieldCrossCheck["field"], string> = {
  supplier_name: "Proveedor",
  amount: "Monto",
  currency: "Moneda",
  account_number: "Cuenta",
};

const SUMMARY: Record<ReadingCrossCheck["status"], string> = {
  agree: "Las dos lecturas coinciden en los cuatro campos que deciden el pago.",
  disagree: "Las dos lecturas no coinciden: no se paga sola, la revisa una persona.",
  unavailable: "No hubo segunda lectura: no se paga sola, la revisa una persona.",
};

function shown(field: FieldCrossCheck["field"], reading: ReaderValue): string {
  if (!reading.value) return "Sin leer";
  const amount = Number(reading.value);
  return field === "amount" && Number.isFinite(amount) ? formatNumber(amount, 2) : reading.value;
}

function FieldRow({ check }: { check: FieldCrossCheck }) {
  const Icon = check.agree ? Check : X;
  return (
    <li className={cn("rounded-[10px] border px-3 py-2", check.agree ? "border-line" : "border-crit bg-crit-weak")}>
      <p className="flex items-center gap-1.5 text-[11.5px] text-ink-3">
        <Icon aria-hidden className={cn("size-3.5", check.agree ? "text-pay" : "text-crit")} />
        {FIELD_LABELS[check.field]} · {check.agree ? "coinciden" : "no coinciden"}
      </p>
      <dl className="mt-1 grid gap-1">
        {check.readings.map((reading) => (
          <div key={reading.reader} className="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)] gap-x-2.5">
            <dt className="truncate font-mono text-[11.5px] text-ink-3">{reading.reader}</dt>
            <dd className="min-w-0 break-words">
              <span className="font-semibold tabular">{shown(check.field, reading)}</span>
              {reading.quote ? <q className="block text-[12px] text-ink-3">{reading.quote}</q> : null}
            </dd>
          </div>
        ))}
      </dl>
    </li>
  );
}

export function ReadingCrossCheckBlock({ crossCheck }: { crossCheck: ReadingCrossCheck }) {
  return (
    <div className="flex flex-col gap-2.5">
      <p className={cn("max-w-[62ch] text-[14px]", crossCheck.status === "agree" ? "text-ink-2" : "text-crit")}>
        {SUMMARY[crossCheck.status]}
        {crossCheck.error ? ` Motivo: ${crossCheck.error}.` : null}
      </p>
      {crossCheck.fields.length > 0 ? (
        <ul aria-label="Dos lecturas independientes" className="grid gap-2 sm:grid-cols-2">
          {crossCheck.fields.map((check) => (
            <FieldRow key={check.field} check={check} />
          ))}
        </ul>
      ) : null}
    </div>
  );
}
