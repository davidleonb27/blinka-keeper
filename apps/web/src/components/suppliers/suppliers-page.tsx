"use client";

import { Check, FileUp, Plus, TriangleAlert, X } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/shell/page-header";
import { ErrorState, LoadingBlock } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Beneficiary, Policy } from "@/lib/api/contracts";
import { messageOf } from "@/lib/api/errors";
import { useAddSuppliers, useImportSuppliers, usePolicy } from "@/lib/api/hooks";
import { DemoNotice } from "./demo-notice";
import { planAdditions, supplierFromForm, type SupplierFields } from "./additions";

const EMPTY_FORM: SupplierFields = { name: "", tax_id: "", bank_name: "", account_number: "" };
const FORM_FIELDS: { field: keyof SupplierFields; label: string; placeholder: string }[] = [
  { field: "name", label: "Nombre", placeholder: "Panadería La Espiga SAS" },
  { field: "tax_id", label: "NIT o identificación tributaria", placeholder: "900.777.123-4" },
  { field: "bank_name", label: "Banco", placeholder: "Bancolombia" },
  { field: "account_number", label: "Cuenta, como aparece en sus facturas", placeholder: "4455 6677" },
];

function ManualForm({ currency, onAdd }: { currency: string; onAdd: (supplier: Beneficiary) => void }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const id = useId();
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onAdd(supplierFromForm(form, currency));
    setForm(EMPTY_FORM);
  };
  return (
    <form onSubmit={submit} aria-label="Agregar a mano" className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {FORM_FIELDS.map(({ field, label, placeholder }) => (
        <label key={field} htmlFor={`${id}-${field}`} className="flex flex-col gap-1 text-[13px] font-medium text-ink-2">
          {label}
          <Input
            id={`${id}-${field}`}
            required
            value={form[field]}
            placeholder={placeholder}
            onChange={(event) => setForm((current) => ({ ...current, [field]: event.target.value }))}
            className="h-10"
          />
        </label>
      ))}
      <Button type="submit" variant="outline" className="self-start sm:col-span-2">
        <Plus aria-hidden /> Añadir a la vista previa
      </Button>
    </form>
  );
}

function CsvImport({ onAdd }: { onAdd: (suppliers: Beneficiary[], warnings: string[]) => void }) {
  const importSuppliers = useImportSuppliers();
  const inputId = useId();
  return (
    <div className="flex flex-col gap-2">
      <label
        htmlFor={inputId}
        className="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-line-2 px-4 py-4 hover:border-brand focus-within:border-brand"
      >
        <FileUp aria-hidden className="size-6 shrink-0 text-brand" />
        <span>
          <b className="block font-semibold">Importar un CSV</b>
          <span className="text-[13px] text-ink-3">
            El mismo formato de «Usar con mi empresa»: nombre, identificación tributaria, banco y cuenta.
          </span>
        </span>
        <input
          id={inputId}
          type="file"
          accept=".csv,.xlsx,.pdf"
          className="sr-only"
          disabled={importSuppliers.isPending}
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (!file) return;
            importSuppliers.mutate({ file }, {
              onSuccess: (result) => onAdd(result.beneficiaries, result.warnings),
              onError: (error) => toast.error(messageOf(error)),
            });
          }}
        />
      </label>
      {importSuppliers.isPending ? <p className="text-[13px] text-ink-3">Leyendo el archivo…</p> : null}
    </div>
  );
}

function Preview({ policy, candidates, onClear }: { policy: Policy; candidates: Beneficiary[]; onClear: () => void }) {
  const apply = useAddSuppliers();
  const plan = planAdditions(policy, candidates);
  if (!candidates.length) return null;
  const count = plan.added.length;
  const save = () =>
    apply.mutateAsync(plan.added).then(
      (applied) => {
        toast.success(`${count === 1 ? "Se agregó 1 proveedor" : `Se agregaron ${count} proveedores`}. La política v${applied.version} quedó en el registro.`);
        onClear();
      },
      (error: unknown) => toast.error(messageOf(error)),
    );
  return (
    <section aria-label="Vista previa de los cambios" className="card-surface flex flex-col gap-3 p-5">
      <h2 className="font-semibold">Vista previa de los cambios</h2>
      <ul className="divide-y divide-line rounded-xl border border-line">
        {plan.added.map((b) => (
          <li key={b.id} className="flex items-start gap-2.5 px-3 py-2.5">
            <Plus aria-hidden className="mt-0.5 size-4 shrink-0 text-pay" />
            <span className="min-w-0">
              <b className="block font-medium">{b.name}</b>
              <span className="text-[12.5px] text-ink-3">
                Nuevo · {b.tax_id} · {b.bank_name} {b.account_number}
              </span>
            </span>
          </li>
        ))}
        {plan.skipped.map((s, index) => (
          <li key={`${s.name}-${index}`} className="flex items-start gap-2.5 px-3 py-2.5">
            <X aria-hidden className="mt-0.5 size-4 shrink-0 text-hold" />
            <span className="min-w-0">
              <b className="block font-medium">{s.name || "Fila sin nombre"}</b>
              <span className="text-[12.5px] text-hold">{s.reason}</span>
            </span>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-2">
        <Button variant="approve" disabled={!count || apply.isPending} onClick={() => void save()}>
          <Check aria-hidden /> {count === 1 ? "Agregar 1 proveedor" : `Agregar ${count} proveedores`}
        </Button>
        <Button variant="ghost" onClick={onClear}>
          Descartar
        </Button>
      </div>
      <p className="text-[12.5px] text-ink-3">
        Se aplica como una versión nueva de la política y queda en el registro encadenado. Los proveedores ya registrados
        no cambian.
      </p>
    </section>
  );
}

function Registered({ policy }: { policy: Policy }) {
  return (
    <section aria-label="Proveedores registrados" className="card-surface p-5">
      <h2 className="font-semibold">Registrados ({policy.beneficiaries.length})</h2>
      <p className="text-[12.5px] text-ink-3">Sólo se paga a quien está aquí, a su cuenta registrada.</p>
      <ul className="mt-2 divide-y divide-line">
        {policy.beneficiaries.map((b) => (
          <li key={b.id} className="py-2.5">
            <b className="block truncate text-[13.5px] font-semibold">{b.name}</b>
            <span className="text-xs text-ink-3">
              {b.tax_id} · {b.bank_name} {b.account_number}
              {b.allowed === false ? " · bloqueado" : ""}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Suppliers({ policy }: { policy: Policy }) {
  const [candidates, setCandidates] = useState<Beneficiary[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const add = (more: Beneficiary[], moreWarnings: string[] = []) => {
    setCandidates((current) => [...current, ...more]);
    setWarnings(moreWarnings);
  };
  const clear = () => {
    setCandidates([]);
    setWarnings([]);
  };
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div className="flex flex-col gap-4">
        <section aria-label="Agregar proveedores" className="card-surface flex flex-col gap-4 p-5">
          <h2 className="font-semibold">Agregar proveedores</h2>
          <CsvImport onAdd={add} />
          {warnings.map((warning) => (
            <p key={warning} className="flex gap-2 rounded-xl bg-esc-weak px-3.5 py-2.5 text-[13.5px]">
              <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-esc" />
              {warning}
            </p>
          ))}
          <ManualForm currency={policy.base_currency} onAdd={(supplier) => add([supplier])} />
        </section>
        <Preview policy={policy} candidates={candidates} onClear={clear} />
      </div>
      <Registered policy={policy} />
    </div>
  );
}

export function SuppliersPage() {
  const policy = usePolicy();
  return (
    <>
      <PageHeader
        title="Proveedores"
        subtitle="A quién le pagas. Agregar uno nuevo crea una versión de la política; las cuentas ya registradas no se cambian desde aquí."
      />
      <DemoNotice />
      {policy.error ? <ErrorState error={policy.error} onRetry={() => void policy.refetch()} /> : null}
      {!policy.data && !policy.error ? <LoadingBlock className="h-72" /> : null}
      {policy.data ? <Suppliers policy={policy.data} /> : null}
    </>
  );
}
