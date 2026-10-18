"use client";

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { DecisionListItem } from "@/lib/api/client";
import { saveFile } from "@/lib/download";
import { decisionsCsv } from "./decisions-csv";

// The byte-order mark makes Excel open the file as UTF-8, accents included.
const BOM = "﻿";

/** Downloads the invoices on screen, with the filter and search applied, as a CSV built in the browser. */
export function ExportCsv({ items }: { items: DecisionListItem[] }) {
  const save = () =>
    saveFile(new Blob([BOM, decisionsCsv(items)], { type: "text/csv;charset=utf-8" }), "blinka-keeper-facturas.csv");
  return (
    <Button variant="outline" size="sm" onClick={save} disabled={!items.length}>
      <Download aria-hidden /> Exportar CSV
    </Button>
  );
}
