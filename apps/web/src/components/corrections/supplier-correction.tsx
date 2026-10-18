"use client";

import { CircleCheck, FileUp, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { ErrorState, LoadingBlock } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CorrectableField, SupplierCorrectionView, SupplierReceipt } from "@/lib/api/client";
import { messageOf } from "@/lib/api/errors";
import { useSubmitSupplierCorrection, useSupplierCorrection } from "@/lib/api/hooks";
import { formatDate, formatMoney } from "@/lib/format";
import { FIELD_LABEL } from "./labels";

type Submit = ReturnType<typeof useSubmitSupplierCorrection>;

function UploadForm({ view, submit }: { view: SupplierCorrectionView; submit: Submit }) {
  const [file, setFile] = useState<File | null>(null);
  const send = (event: FormEvent) => {
    event.preventDefault();
    if (file) submit.mutate({ file });
  };
  return (
    <form onSubmit={send} className="card-surface flex flex-col gap-3 p-5">
      <h2 className="font-semibold">Enviar la factura corregida</h2>
      <label className="flex flex-col gap-1.5 text-[13px] text-ink-2">
        PDF o foto nítida (máximo 4 MB)
        <Input
          type="file"
          accept={view.accepted_media_types.join(",")}
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          className="h-11 py-2"
        />
      </label>
      <Button type="submit" disabled={!file || submit.isPending} className="self-start">
        <FileUp aria-hidden /> Enviar factura corregida
      </Button>
    </form>
  );
}

function ConfirmForm({ view, submit }: { view: SupplierCorrectionView; submit: Submit }) {
  const [values, setValues] = useState<Partial<Record<CorrectableField, string>>>({});
  const complete = view.fields.every((name) => (values[name] ?? "").trim());
  const send = (event: FormEvent) => {
    event.preventDefault();
    if (complete) submit.mutate({ values });
  };
  return (
    <form onSubmit={send} className="card-surface flex flex-col gap-3 p-5">
      <h2 className="font-semibold">O confirmar el dato</h2>
      <p className="text-[13px] text-ink-3">Sólo los datos que se piden; la cuenta no se puede cambiar por aquí.</p>
      {view.fields.map((name) => (
        <label key={name} className="flex flex-col gap-1.5 text-[13px] text-ink-2">
          {FIELD_LABEL[name]}
          <Input
            value={values[name] ?? ""}
            maxLength={30}
            onChange={(event) => setValues((current) => ({ ...current, [name]: event.target.value }))}
            className="h-10"
          />
        </label>
      ))}
      <Button type="submit" variant="outline" disabled={!complete || submit.isPending} className="self-start">
        Confirmar
      </Button>
    </form>
  );
}

function Received({ receipt }: { receipt: SupplierReceipt }) {
  return (
    <div role="status" className="card-surface flex flex-col gap-2 p-5">
      <p className="flex items-center gap-2 font-semibold">
        <CircleCheck aria-hidden className="size-5 text-pay" /> Corrección enviada
      </p>
      <p className="text-ink-2">{receipt.message}</p>
    </div>
  );
}

function Request({ view }: { view: SupplierCorrectionView }) {
  const invoice = view.reference ? `la factura ${view.reference}` : "su factura";
  const amount = view.amount !== null && view.currency ? ` por ${formatMoney(view.amount, view.currency)}` : "";
  return (
    <section className="card-surface flex flex-col gap-3 p-5">
      <p className="eyebrow">
        Ronda {view.round} de {view.max_rounds} · vence el {formatDate(view.expires_at)}
      </p>
      <h1 className="font-serif text-2xl leading-tight font-semibold">
        {view.company_name} necesita una corrección de {invoice}
        {amount}
      </h1>
      <p className="text-ink-2">Hola, {view.supplier_name}. Esto es lo que hay que corregir:</p>
      <ul className="flex flex-col gap-2">
        {view.issues.map((issue) => (
          <li key={issue.problem} className="rounded-xl bg-surface-2 px-3.5 py-2.5 text-[14px]">
            {issue.problem} <span className="text-ink-2">Se espera: {issue.expected}.</span>
          </li>
        ))}
      </ul>
      <p className="flex gap-2 text-[13px] text-ink-3">
        <ShieldCheck aria-hidden className="mt-0.5 size-4 shrink-0" />
        Sólo se paga a la cuenta registrada. Si la factura corregida trae otra cuenta, no se paga: los cambios de cuenta
        se verifican por otro canal.
      </p>
    </section>
  );
}

/** The supplier's page: one invoice, what to fix, and a way to send the fix. Nothing else of the company. */
export function SupplierCorrection({ token }: { token: string }) {
  const view = useSupplierCorrection(token);
  const submit = useSubmitSupplierCorrection(token);
  if (view.error) return <ErrorState error={view.error} />;
  if (!view.data) return <LoadingBlock label="Cargando la solicitud…" />;
  if (submit.data) return <Received receipt={submit.data} />;
  return (
    <div className="flex flex-col gap-4">
      <Request view={view.data} />
      <UploadForm view={view.data} submit={submit} />
      {view.data.confirmable ? <ConfirmForm view={view.data} submit={submit} /> : null}
      {submit.error ? (
        <p role="alert" className="rounded-xl bg-crit-weak px-3.5 py-3 text-[14px]">
          {messageOf(submit.error)}
        </p>
      ) : null}
    </div>
  );
}
