"use client";

import { CheckCircle2, CircleAlert, FileUp, LoaderCircle, Scale, Upload } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import type { InvoiceInput } from "@/lib/api/client";
import { messageOf } from "@/lib/api/errors";
import { useProcessInvoices, useUploadInvoice, useWorkspaceSummary } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";
import { ACCEPTED_INVOICES, invoiceInputOf, type PreparedInvoice } from "./intake";

type RowState = "waiting" | "sending" | "received" | "failed";

interface Row {
  key: number;
  name: string;
  state: RowState;
  message?: string;
}

const PASTED_NAME = "Texto pegado";

function RowIcon({ state }: { state: RowState }) {
  if (state === "received") return <CheckCircle2 aria-hidden className="size-4 shrink-0 text-pay" />;
  if (state === "failed") return <CircleAlert aria-hidden className="size-4 shrink-0 text-hold" />;
  return <LoaderCircle aria-hidden className={cn("size-4 shrink-0 text-ink-3", state === "sending" && "animate-spin")} />;
}

const STATE_LABEL: Record<RowState, string> = {
  waiting: "En cola",
  sending: "Enviando…",
  received: "Recibida",
  failed: "No se recibió",
};

function Progress({ rows }: { rows: Row[] }) {
  if (!rows.length) return null;
  return (
    <ul aria-label="Avance de la subida" className="flex flex-col divide-y divide-line rounded-xl border border-line">
      {rows.map((row) => (
        <li key={row.key} className="flex items-start gap-2.5 px-3 py-2.5">
          <span className="pt-0.5">
            <RowIcon state={row.state} />
          </span>
          <span className="min-w-0 flex-1">
            <b className="block truncate font-medium">{row.name}</b>
            <span className={cn("block text-[12.5px]", row.state === "failed" ? "text-hold" : "text-ink-3")}>
              {row.message ?? STATE_LABEL[row.state]}
            </span>
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Receives the company's own invoices one by one, then hands the batch to the rules with a single click. */
function UploadForm({ onDecided }: { onDecided: () => void }) {
  const upload = useUploadInvoice();
  const process = useProcessInvoices();
  const pending = useWorkspaceSummary().data?.pending_invoices ?? 0;
  const [rows, setRows] = useState<Row[]>([]);
  const [text, setText] = useState("");
  const [dragging, setDragging] = useState(false);
  const queue = useRef(Promise.resolve());
  const nextKey = useRef(0);
  const inputId = useId();
  const textId = useId();

  const update = (key: number, change: Partial<Row>) =>
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...change } : row)));

  async function send(key: number, prepare: () => Promise<PreparedInvoice>) {
    update(key, { state: "sending" });
    const prepared = await prepare();
    if (!prepared.ok) return update(key, { state: "failed", message: prepared.message });
    try {
      await upload.mutateAsync(prepared.input);
      update(key, { state: "received" });
    } catch (error) {
      update(key, { state: "failed", message: messageOf(error) });
    }
  }

  // One at a time, in the order they were added: the API counts model calls per minute.
  function enqueue(entries: { name: string; prepare: () => Promise<PreparedInvoice> }[]) {
    const added = entries.map((entry) => ({ ...entry, key: nextKey.current++ }));
    setRows((current) => [...current, ...added.map(({ key, name }) => ({ key, name, state: "waiting" as const }))]);
    for (const { key, prepare } of added) queue.current = queue.current.then(() => send(key, prepare));
  }

  const addFiles = (files: FileList | null) =>
    enqueue([...(files ?? [])].map((file) => ({ name: file.name, prepare: () => invoiceInputOf(file) })));

  function addText() {
    const input: InvoiceInput = { text };
    enqueue([{ name: PASTED_NAME, prepare: () => Promise.resolve({ ok: true, input }) }]);
    setText("");
  }

  function drop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    addFiles(event.dataTransfer.files);
  }

  const busy = rows.some((row) => row.state === "waiting" || row.state === "sending");
  const received = rows.filter((row) => row.state === "received").length;
  const toDecide = Math.max(pending, received);
  const decide = () =>
    process.mutateAsync().then(
      ({ batch }) => {
        toast.success(`Custodio decidió ${batch.metrics.total} ${batch.metrics.total === 1 ? "factura" : "facturas"}.`);
        onDecided();
      },
      (error: unknown) => toast.error(messageOf(error)),
    );

  return (
    <div className="flex flex-col gap-4">
      <label
        htmlFor={inputId}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={drop}
        className={cn(
          "flex cursor-pointer flex-col items-center gap-1.5 rounded-xl border border-dashed border-line-2 px-4 py-6 text-center focus-within:border-brand hover:border-brand",
          dragging && "border-brand bg-brand-weak",
        )}
      >
        <FileUp aria-hidden className="size-6 text-brand" />
        <span className="font-semibold">Arrastra las facturas aquí o elígelas</span>
        <span className="text-[13px] text-ink-2">PDF, imagen, .eml o .txt, hasta 4 MB cada una.</span>
        <input
          id={inputId}
          type="file"
          multiple
          accept={ACCEPTED_INVOICES}
          className="sr-only"
          onChange={(event) => {
            addFiles(event.target.files);
            event.target.value = "";
          }}
        />
      </label>
      <div className="flex flex-col gap-2">
        <label htmlFor={textId} className="text-[13px] font-medium text-ink-2">
          O pega el texto de un correo con la factura
        </label>
        <textarea
          id={textId}
          rows={5}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="De: facturacion@proveedor.co…"
          className="w-full resize-y rounded-xl border border-line-2 bg-surface-2 px-3.5 py-3 font-mono text-[12.5px] leading-relaxed"
        />
        <Button variant="outline" className="self-start" disabled={!text.trim()} onClick={addText}>
          <Upload aria-hidden /> Enviar el texto
        </Button>
      </div>
      <Progress rows={rows} />
      {toDecide > 0 && !busy ? (
        <Button size="lg" onClick={() => void decide()} disabled={process.isPending}>
          <Scale aria-hidden /> Decidir {toDecide} {toDecide === 1 ? "factura" : "facturas"}
        </Button>
      ) : null}
    </div>
  );
}

export function UploadInvoicesButton({ size = "default" }: { size?: "default" | "sm" | "lg" }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button size={size} onClick={() => setOpen(true)}>
        <Upload aria-hidden /> Subir facturas
      </Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent
          side="right"
          className="gap-4 overflow-y-auto border-line-2 bg-surface px-5 pt-5 pb-6 data-[side=right]:w-full data-[side=right]:sm:max-w-[520px] sm:px-6"
        >
          <div className="pr-8">
            <SheetTitle className="font-serif text-2xl font-semibold">Subir facturas</SheetTitle>
            <SheetDescription className="mt-1 text-ink-2">
              Custodio las lee y las deja listas; ninguna se paga hasta que decidas el lote con tus reglas.
            </SheetDescription>
          </div>
          <UploadForm onDecided={() => setOpen(false)} />
        </SheetContent>
      </Sheet>
    </>
  );
}
