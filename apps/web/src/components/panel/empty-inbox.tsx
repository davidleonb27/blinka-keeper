import { Inbox } from "lucide-react";
import { UploadInvoicesButton } from "@/components/intake/upload-dialog";

/** A real company's workspace before its first invoice: the upload is the one thing to do. */
export function EmptyInbox() {
  return (
    <section aria-labelledby="sin-facturas" className="card-surface flex flex-col items-center gap-4 px-6 py-14 text-center">
      <Inbox aria-hidden className="size-9 text-brand" strokeWidth={1.5} />
      <div className="max-w-[52ch]">
        <h2 id="sin-facturas" className="headline text-2xl">
          Aún no hay facturas: súbelas o reenvíalas
        </h2>
        <p className="mt-2 text-ink-2">
          Sube los PDF o las fotos de tus facturas, o reenvíalas: guarda el correo como .eml o pega su texto. Tu sistema
          también puede enviarlas a <code>POST /api/v1/invoices</code>. Nada se paga hasta que decidas el lote.
        </p>
      </div>
      <UploadInvoicesButton size="lg" />
    </section>
  );
}
