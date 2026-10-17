import { EyeOff, FileText } from "lucide-react";
import type { ExtractedFieldName, ExtractedInvoice } from "@/lib/api/contracts";
import { SOURCE_LABEL } from "@/lib/presentation";
import { cn } from "@/lib/utils";
import { documentSegments } from "./document-segments";

export function OriginalDocument({
  extraction,
  activeField,
}: {
  extraction: ExtractedInvoice;
  activeField: ExtractedFieldName | null;
}) {
  return (
    <div>
      <p className="mb-2 flex items-center gap-2 text-[12.5px] text-ink-3">
        <FileText aria-hidden className="size-4" />
        {SOURCE_LABEL[extraction.source]} · leído por {extraction.reader}
      </p>
      <figure
        aria-label="Documento original"
        className="m-0 overflow-x-hidden rounded-xl border border-line bg-surface-2 px-4 py-3.5 font-mono text-[12.5px] leading-[1.75] break-words whitespace-pre-wrap"
      >
        {documentSegments(extraction).map((segment, index) =>
          segment.fields.length ? (
            <mark
              key={index}
              data-fields={segment.fields.join(" ")}
              className={cn(
                "rounded px-0.5 text-inherit shadow-[inset_0_-1.5px_0_var(--brand)] transition-colors",
                activeField && segment.fields.includes(activeField) ? "bg-brand text-on-brand" : "bg-brand-weak",
              )}
            >
              {segment.text}
            </mark>
          ) : (
            <span key={index}>{segment.text}</span>
          ),
        )}
      </figure>
      {extraction.hidden_findings.map((finding, index) => (
        <div key={index} className="mt-2.5 rounded-xl border border-dashed border-crit bg-crit-weak px-3.5 py-3">
          <p className="mb-1 flex items-center gap-2 text-[12.5px] font-semibold text-crit">
            <EyeOff aria-hidden className="size-4" />
            Texto oculto destapado
          </p>
          <p className="text-[12.5px] text-ink-2">{finding.detail}</p>
          <p className="mt-1.5 font-mono text-[12.5px] break-words">«{finding.text}»</p>
        </div>
      ))}
    </div>
  );
}
