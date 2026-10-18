import { describe, expect, it } from "vitest";
import { invoiceInputOf, MAX_INVOICE_BYTES } from "./intake";

function fileOf(name: string, content: BlobPart = "x", type = ""): File {
  return new File([content], name, { type });
}

describe("invoiceInputOf", () => {
  it("sends PDFs and images as files", async () => {
    const pdf = fileOf("factura.pdf", "%PDF", "application/pdf");
    expect(await invoiceInputOf(pdf)).toEqual({ ok: true, input: { file: pdf } });
    const photo = fileOf("FOTO.JPG", "jpg", "image/jpeg");
    expect(await invoiceInputOf(photo)).toEqual({ ok: true, input: { file: photo } });
  });

  it("sends the electronic invoice XML as a file, so the API reads it by code", async () => {
    const xml = fileOf("FE-1042.xml", "<Invoice/>", "text/xml");
    expect(await invoiceInputOf(xml)).toEqual({ ok: true, input: { file: xml } });
  });

  it("sends emails and text files as text, which the API reads as the body of an email", async () => {
    expect(await invoiceInputOf(fileOf("correo.eml", "From: a@b.co\n\nFactura 12", "message/rfc822"))).toEqual({
      ok: true,
      input: { text: "From: a@b.co\n\nFactura 12" },
    });
    expect(await invoiceInputOf(fileOf("nota.txt", "Factura 13", "text/plain"))).toEqual({
      ok: true,
      input: { text: "Factura 13" },
    });
  });

  it("refuses, before sending, what the API would refuse", async () => {
    expect(await invoiceInputOf(fileOf("hoja.xlsx"))).toEqual({
      ok: false,
      message: "Sólo leemos PDF, PNG, JPEG, WEBP, XML (factura electrónica), .eml o .txt.",
    });
    expect(await invoiceInputOf(fileOf("grande.pdf", new Uint8Array(MAX_INVOICE_BYTES + 1)))).toEqual({
      ok: false,
      message: "El archivo supera el máximo de 4 MB.",
    });
    expect(await invoiceInputOf(fileOf("vacio.txt", "  "))).toEqual({ ok: false, message: "El archivo está vacío." });
  });
});
