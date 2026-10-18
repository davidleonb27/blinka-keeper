"use client";

import { Copy, MessageSquareWarning, ShieldBan, Undo2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { StatusPill } from "@/components/status-pill";
import { Button } from "@/components/ui/button";
import type { CorrectionIssued, CorrectionOffer, CorrectionRequest } from "@/lib/api/client";
import { messageOf } from "@/lib/api/errors";
import { useCorrectionOffer, useRequestCorrection } from "@/lib/api/hooks";
import { formatDate, formatDateTime } from "@/lib/format";
import { REQUEST_STATUS_LABEL, WHATSAPP_LABEL } from "./labels";

async function copy(text: string, what: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(`${what} copiado.`);
  } catch {
    toast.error(`No pudimos copiar ${what.toLowerCase()}; selecciónalo y cópialo a mano.`);
  }
}

function Issues({ offer }: { offer: CorrectionOffer }) {
  return (
    <ul aria-label="Qué corregiría el proveedor" className="flex flex-col gap-2">
      {offer.issues.map((issue) => (
        <li key={issue.kind} className="rounded-xl bg-surface-2 px-3.5 py-2.5 text-[14px]">
          {issue.problem} <span className="text-ink-2">Se espera: {issue.expected}.</span>
        </li>
      ))}
    </ul>
  );
}

function NotNegotiated({ offer }: { offer: CorrectionOffer }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl bg-crit-weak px-3.5 py-3 text-[14px]">
      <p className="flex items-center gap-2 font-semibold">
        <ShieldBan aria-hidden className="size-4 text-crit" /> No se negocia con el proveedor
      </p>
      <ul className="flex list-disc flex-col gap-1 pl-5">
        {offer.blockers.map((blocker) => (
          <li key={blocker.kind}>{blocker.reason}</li>
        ))}
      </ul>
    </div>
  );
}

function Issued({ issued }: { issued: CorrectionIssued }) {
  return (
    <div className="flex flex-col gap-2.5">
      <label className="flex flex-col gap-1.5 text-[12.5px] text-ink-3">
        Mensaje para el proveedor (el enlace se muestra sólo esta vez)
        <textarea
          readOnly
          value={issued.message}
          rows={9}
          className="rounded-xl border border-line-2 bg-surface-2 px-3 py-2 font-mono text-[12.5px] text-ink"
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={() => void copy(issued.message, "Mensaje")}>
          <Copy aria-hidden /> Copiar mensaje
        </Button>
        <Button variant="outline" size="sm" onClick={() => void copy(issued.link, "Enlace")}>
          <Copy aria-hidden /> Copiar enlace
        </Button>
      </div>
      <p className="text-[12.5px] text-ink-3">{WHATSAPP_LABEL[issued.whatsapp]}</p>
    </div>
  );
}

function History({ requests }: { requests: CorrectionRequest[] }) {
  return (
    <ol aria-label="Rondas de corrección" className="flex flex-col gap-2 text-[13px]">
      {requests.map((request) => (
        <li key={request.id} className="flex flex-col gap-1 border-l-2 border-line-2 pl-3">
          <span>
            <b className="font-semibold">Ronda {request.round}</b> · {REQUEST_STATUS_LABEL[request.status]} · pedida el{" "}
            {formatDateTime(request.created_at)}
            {request.status === "open" ? ` · vence el ${formatDate(request.expires_at)}` : ""}
          </span>
          {request.corrected_invoice_id ? (
            <span className="flex flex-wrap items-center gap-2">
              <Link href={{ query: { acta: request.corrected_invoice_id } }} scroll={false} className="underline">
                Acta de la corrección {request.corrected_invoice_id}
              </Link>
              {request.outcome ? <StatusPill status={request.outcome} /> : null}
            </span>
          ) : null}
          {request.alert ? <span className="font-semibold text-crit">{request.alert}</span> : null}
        </li>
      ))}
    </ol>
  );
}

/** The acta's «Corrección con el proveedor»: what the supplier could fix, or why it is not negotiated. */
export function CorrectionPanel({ invoiceId, cameByWhatsApp }: { invoiceId: string; cameByWhatsApp: boolean }) {
  const offer = useCorrectionOffer(invoiceId);
  const request = useRequestCorrection(invoiceId);
  const [issued, setIssued] = useState<CorrectionIssued | null>(null);
  const [whatsapp, setWhatsapp] = useState(cameByWhatsApp);
  const data = offer.data;
  if (!data || (!data.offered && !data.blockers.length && !data.history.length)) return null;

  const ask = () =>
    request.mutate(
      { whatsapp },
      {
        onSuccess: (result) => {
          setIssued(result);
          void offer.refetch();
        },
        onError: (error) => toast.error(messageOf(error)),
      },
    );
  const waiting = data.open_request !== null && issued === null;

  return (
    <section aria-labelledby={`correccion-${invoiceId}`} className="flex flex-col gap-3">
      <h3 id={`correccion-${invoiceId}`} className="eyebrow">
        Corrección con el proveedor
      </h3>
      {data.blockers.length ? <NotNegotiated offer={data} /> : null}
      {data.offered ? <Issues offer={data} /> : null}
      {data.offered && data.still_for_a_person.length ? (
        <p className="text-[12.5px] text-ink-3">
          Aunque se corrija, una persona aprobará el pago por: {data.still_for_a_person.join(", ")}.
        </p>
      ) : null}
      {waiting ? (
        <p className="flex items-center gap-2 rounded-xl bg-esc-weak px-3.5 py-2.5 text-[14px] font-semibold">
          <MessageSquareWarning aria-hidden className="size-4 text-esc" /> Esperando corrección del proveedor
        </p>
      ) : null}
      {issued ? <Issued issued={issued} /> : null}
      {data.offered ? (
        <div className="flex flex-wrap items-center gap-3">
          {cameByWhatsApp ? (
            <label className="flex items-center gap-2 text-[13px] text-ink-2">
              <input type="checkbox" checked={whatsapp} onChange={(event) => setWhatsapp(event.target.checked)} />
              Enviar también por WhatsApp
            </label>
          ) : null}
          <Button variant="outline" size="sm" disabled={request.isPending} onClick={ask}>
            <Undo2 aria-hidden /> {waiting || issued ? "Generar un enlace nuevo" : "Pedir corrección al proveedor"}
          </Button>
          <span className="text-[12px] text-ink-3">
            Ronda {data.next_round} de {data.max_rounds}. Un enlace nuevo anula el anterior.
          </span>
        </div>
      ) : data.reason && !data.blockers.length ? (
        <p className="text-[13px] text-ink-3">{data.reason}</p>
      ) : null}
      {data.history.length ? <History requests={data.history} /> : null}
    </section>
  );
}
