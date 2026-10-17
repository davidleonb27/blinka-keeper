"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const COPIED_FEEDBACK_MS = 1800;

/** Shows `code`; copies `copyText` when given, so a masked secret still copies as the real one. */
export function CodeBlock({ code, label, copyText = code }: { code: string; label: string; copyText?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(copyText);
    setCopied(true);
    setTimeout(() => setCopied(false), COPIED_FEEDBACK_MS);
  };
  return (
    <figure className="m-0 overflow-hidden rounded-xl border border-line bg-surface-2">
      <figcaption className="flex items-center justify-between gap-2 border-b border-line px-3 py-1.5 text-xs text-ink-3">
        {label}
        <Button variant="ghost" size="sm" onClick={() => void copy()} aria-label={`Copiar ${label}`}>
          {copied ? <Check aria-hidden className="text-pay" /> : <Copy aria-hidden />}
          <span aria-live="polite">{copied ? "Copiado" : "Copiar"}</span>
        </Button>
      </figcaption>
      <pre tabIndex={0} className="overflow-x-auto px-3.5 py-3 font-mono text-[12px] leading-relaxed">
        <code>{code}</code>
      </pre>
    </figure>
  );
}
