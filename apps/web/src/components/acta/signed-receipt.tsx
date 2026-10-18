"use client";

import { BadgeCheck, Download } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useApi } from "@/components/providers/api-provider";
import { messageOf } from "@/lib/api/errors";
import { useReceiptKey } from "@/lib/api/hooks";
import { saveFile } from "@/lib/download";

export const VERIFY_PATH = "/verificar";

/** The seal of a decision signed with Ed25519, and the receipt anyone can check without access to Custodio. */
export function SignedReceipt({ invoiceId }: { invoiceId: string }) {
  const api = useApi();
  const key = useReceiptKey();
  const [downloading, setDownloading] = useState(false);

  const download = async () => {
    setDownloading(true);
    try {
      const receipt = await api.getReceipt(invoiceId);
      const json = `${JSON.stringify(receipt, null, 2)}\n`;
      saveFile(new Blob([json], { type: "application/json" }), `recibo-${invoiceId}.json`);
    } catch (error) {
      toast.error(messageOf(error));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <section aria-label="Recibo firmado" className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-ink-3">
      <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-weak px-2.5 py-1 font-medium text-brand">
        <BadgeCheck aria-hidden className="size-3.5" />
        {key.data ? (
          <>
            Firmado · clave <code className="font-mono">{key.data.key_id}</code>
          </>
        ) : (
          "Firmado con Ed25519"
        )}
      </span>
      <Button variant="outline" size="sm" disabled={downloading} onClick={() => void download()}>
        <Download aria-hidden /> Descargar recibo firmado
      </Button>
      <Link href={VERIFY_PATH} className="underline underline-offset-2 hover:text-ink">
        Verificar un recibo
      </Link>
    </section>
  );
}
