import type { InvoiceInput } from "@/lib/api/client";

/** The API's limit (MAX_DOCUMENT_BYTES): checked here so a large file fails at once, without the upload. */
export const MAX_INVOICE_BYTES = 4 * 1024 * 1024;
const DOCUMENT_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "webp", "xml"];
// The API reads emails and text as the text of an invoice; it would refuse an .eml sent as a file.
const TEXT_EXTENSIONS = ["eml", "txt"];
export const ACCEPTED_INVOICES = [...DOCUMENT_EXTENSIONS, ...TEXT_EXTENSIONS].map((ext) => `.${ext}`).join(",");

export type PreparedInvoice = { ok: true; input: InvoiceInput } | { ok: false; message: string };

function extensionOf(name: string): string {
  return name.split(".").pop()?.toLowerCase() ?? "";
}

export async function invoiceInputOf(file: File): Promise<PreparedInvoice> {
  const extension = extensionOf(file.name);
  const isText = TEXT_EXTENSIONS.includes(extension);
  if (!isText && !DOCUMENT_EXTENSIONS.includes(extension)) {
    return { ok: false, message: "Sólo leemos PDF, PNG, JPEG, WEBP, XML (factura electrónica), .eml o .txt." };
  }
  if (file.size > MAX_INVOICE_BYTES) return { ok: false, message: "El archivo supera el máximo de 4 MB." };
  if (!isText) return { ok: true, input: { file } };
  const text = await file.text();
  return text.trim() ? { ok: true, input: { text } } : { ok: false, message: "El archivo está vacío." };
}
