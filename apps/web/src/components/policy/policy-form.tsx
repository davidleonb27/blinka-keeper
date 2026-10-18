"use client";

import { Check } from "lucide-react";
import { useId, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import type { Policy } from "@/lib/api/contracts";
import { messageOf } from "@/lib/api/errors";
import { useApplyPolicy } from "@/lib/api/hooks";
import { formatPolicyValue } from "./proposal-view";

type NumericField =
  | "approval_threshold"
  | "per_payment_limit"
  | "period_budget"
  | "reserve"
  | "agreement_tolerance_pct"
  | "duplicate_window_days"
  | "split_window_days";

const FIELDS: { field: NumericField; label: string; help: string }[] = [
  { field: "approval_threshold", label: "Tope de aprobación automática", help: "Sobre este monto, Blinka Keeper pide permiso a una persona." },
  { field: "per_payment_limit", label: "Límite por pago", help: "Ningún pago pasa de aquí sin aprobación, aunque el proveedor sea conocido." },
  { field: "period_budget", label: "Cupo de pago automático", help: "Lo máximo que Blinka Keeper paga solo en el mes." },
  { field: "reserve", label: "Reserva que no se toca", help: "El saldo nunca baja de aquí, ni siquiera con aprobación." },
  { field: "agreement_tolerance_pct", label: "Tolerancia frente a lo acordado", help: "Cuánto puede variar una factura frente al acuerdo, en %." },
  { field: "duplicate_window_days", label: "Ventana de duplicados", help: "Mismo proveedor y monto dentro de estos días cuenta como posible duplicado." },
  { field: "split_window_days", label: "Ventana de fraccionamiento", help: "Cobros del mismo proveedor en estos días se suman antes de comparar." },
];

function NumberRow({ policy, draft, field, label, help, onChange }: {
  policy: Policy;
  draft: Policy;
  field: NumericField;
  label: string;
  help: string;
  onChange: (value: number) => void;
}) {
  const id = useId();
  const changed = policy[field] !== draft[field];
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_140px] items-center gap-x-4 gap-y-1 py-3">
      <label htmlFor={id} className="text-[13.5px] font-semibold">
        {label}
        {changed ? <span className="ml-2 rounded-full bg-brand-weak px-2 py-0.5 text-[11px] text-brand">cambió</span> : null}
      </label>
      <input
        id={id}
        type="number"
        min={0}
        inputMode="decimal"
        aria-describedby={`${id}-help`}
        value={draft[field]}
        onChange={(e) => onChange(Number(e.target.value))}
        className="row-span-2 h-10 w-full rounded-[10px] border border-line-2 bg-surface-2 px-2.5 text-right font-mono text-[13px]"
      />
      <p id={`${id}-help`} className="text-[12.5px] text-ink-3">
        {help} Hoy: {formatPolicyValue({ field }, policy[field], policy.base_currency)}.
      </p>
    </li>
  );
}

/** The classic alternative to writing rules: every threshold as a number, every supplier as a switch. */
export function PolicyForm({ policy }: { policy: Policy }) {
  const [draft, setDraft] = useState(policy);
  const apply = useApplyPolicy();
  const dirty = JSON.stringify(draft) !== JSON.stringify(policy);

  const setBeneficiaryAllowed = (id: string, allowed: boolean) =>
    setDraft((d) => ({ ...d, beneficiaries: d.beneficiaries.map((b) => (b.id === id ? { ...b, allowed } : b)) }));

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section className="card-surface p-5" aria-label="Límites">
        <h2 className="font-semibold">Límites</h2>
        <ul className="divide-y divide-line">
          {FIELDS.map((f) => (
            <NumberRow key={f.field} policy={policy} draft={draft} {...f} onChange={(value) => setDraft((d) => ({ ...d, [f.field]: value }))} />
          ))}
        </ul>
        <Button
          variant="approve"
          className="mt-3"
          disabled={!dirty || apply.isPending}
          onClick={() =>
            apply.mutate(draft, {
              onSuccess: () => toast.success("Reglas aplicadas. El cambio quedó en el registro."),
              onError: (e) => toast.error(messageOf(e)),
            })
          }
        >
          <Check aria-hidden /> Aplicar cambios
        </Button>
      </section>
      <section className="card-surface p-5" aria-label="Beneficiarios permitidos">
        <h2 className="font-semibold">Beneficiarios permitidos</h2>
        <p className="text-[12.5px] text-ink-3">Solo se paga a quien está aquí, a su cuenta registrada.</p>
        <ul className="mt-2 max-h-[560px] divide-y divide-line overflow-y-auto">
          {draft.beneficiaries.map((b) => (
            <li key={b.id} className="flex items-center justify-between gap-3 py-2.5">
              <span className="min-w-0">
                <b className="block truncate text-[13.5px] font-semibold">{b.name}</b>
                <span className="text-xs text-ink-3">{b.bank_name} {b.account_number}</span>
              </span>
              <Switch
                checked={b.allowed !== false}
                aria-label={`Permitir pagos a ${b.name}`}
                onCheckedChange={(allowed) => setBeneficiaryAllowed(b.id, allowed)}
              />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
