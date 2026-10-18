"use client";

import { MessageCircle, Smartphone } from "lucide-react";
import { toast } from "sonner";
import { QrCode } from "@/components/challenge/qr-code";
import { Button } from "@/components/ui/button";
import type { WhatsAppLinkCode } from "@/lib/api/client";
import { messageOf } from "@/lib/api/errors";
import { useCreateWhatsAppCode, useWhatsAppStatus } from "@/lib/api/hooks";
import { formatDateTime } from "@/lib/format";

/** Invoices can arrive as a photo or PDF sent on WhatsApp; a phone is linked with a one-time code. Hidden when the
 * server has no WhatsApp number configured. */
export function WhatsAppCard() {
  const status = useWhatsAppStatus();
  const create = useCreateWhatsAppCode();
  if (!status.data?.enabled || !status.data.display_number) return null;
  const { phones, display_number: number } = status.data;
  const linked = phones.length > 0;
  const requestCode = () => create.mutate(undefined, { onError: (error) => toast.error(messageOf(error)) });
  return (
    <section aria-label="Canal de WhatsApp" className="card-surface flex flex-col gap-4 p-5">
      <div className="flex min-w-0 items-start gap-3">
        <MessageCircle aria-hidden className="size-6 shrink-0 text-brand" />
        <div className="min-w-0 flex-1">
          <h2 className="text-[15px] font-semibold text-ink">Recibe facturas por WhatsApp</h2>
          <p className="mt-1 text-ink-2">
            {linked
              ? `Envía la foto o el PDF de cada factura al +${number}. Custodio la decide con tus reglas y te responde ahí mismo.`
              : "Liga tu celular con un código de un solo uso y envía las facturas en foto o PDF."}{" "}
            Las aprobaciones se hacen sólo aquí, en la app.
          </p>
          {linked ? (
            <ul aria-label="Teléfonos ligados" className="mt-2 flex flex-wrap gap-2">
              {phones.map((phone) => (
                <li key={phone.masked} className="flex items-center gap-1.5 rounded-full bg-surface-2 px-2.5 py-1 text-[13px] text-ink-2">
                  <Smartphone aria-hidden className="size-3.5" />
                  <span className="tabular">{phone.masked}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <Button variant={linked ? "outline" : "default"} onClick={requestCode} disabled={create.isPending} className="shrink-0">
          {create.isPending ? "Generando…" : linked ? "Ligar otro teléfono" : "Ligar mi teléfono"}
        </Button>
      </div>
      {create.data ? <LinkCode code={create.data} /> : null}
    </section>
  );
}

function LinkCode({ code }: { code: WhatsAppLinkCode }) {
  return (
    <div className="flex flex-col items-start gap-4 rounded-xl bg-surface-2 p-4 sm:flex-row sm:items-center">
      <QrCode value={code.link_url} className="w-36 shrink-0" />
      <div className="min-w-0">
        <p className="text-ink-2">Escanea el código con tu celular o abre el enlace: WhatsApp trae listo el mensaje; sólo envíalo.</p>
        <p className="mt-2 font-mono text-2xl font-semibold tracking-[0.2em] text-ink" aria-label="Código de un solo uso">
          {code.code}
        </p>
        <p className="mt-1 text-[13px] text-ink-3">
          Sirve una vez y vence {formatDateTime(code.expires_at)}.{" "}
          <a href={code.link_url} target="_blank" rel="noreferrer" className="font-medium text-brand underline-offset-2 hover:underline">
            Abrir WhatsApp
          </a>
        </p>
      </div>
    </div>
  );
}
