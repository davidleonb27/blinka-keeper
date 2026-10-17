"use client";

import { UploadInvoicesButton } from "@/components/intake/upload-dialog";
import type { DecisionListItem } from "@/lib/api/client";
import { ExportCsv } from "./export-csv";

/** What a finance team does with the list besides reading it: add invoices and take them to a spreadsheet. */
export function ListActions({ items }: { items: DecisionListItem[] }) {
  return (
    <div className="flex items-center gap-2 sm:ml-auto">
      <UploadInvoicesButton size="sm" />
      <ExportCsv items={items} />
    </div>
  );
}
