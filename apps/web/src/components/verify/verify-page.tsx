"use client";

import { FileUp, KeyRound, ShieldCheck, ShieldX, Wand2 } from "lucide-react";
import { useId, useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { useApi } from "@/components/providers/api-provider";
import type { ReceiptCheck } from "@/lib/api/client";
import { messageOf } from "@/lib/api/errors";
import { useReceiptKey } from "@/lib/api/hooks";
import { VERDICT_LABELS } from "@/lib/receipts/labels";
import { verifyReceiptInBrowser, type BrowserCheck } from "@/lib/receipts/verify";
import { tamperAmount } from "./tamper";

const KEY_URL = "/api/v1/.well-known/custodio-receipt-key";
const NOT_JSON = "Inválido: el texto no es JSON. Pega el recibo completo, tal como lo descargaste.";

interface Verdict {
  valid: boolean;
  message: string;
  verdict: string | null;
  invoiceId: string | null;
}

interface Results {
  browser: Verdict | null;
  server: Verdict | null;
  serverError: string | null;
}

const EMPTY: Results = { browser: null, server: null, serverError: null };

function fromBrowser(check: BrowserCheck): Verdict {
  return { valid: check.valid, message: check.message, verdict: check.verdict, invoiceId: check.invoiceId };
}

function fromServer(check: ReceiptCheck): Verdict {
  return {
    valid: check.valid,
    message: check.message,
    verdict: check.verdict ?? null,
    invoiceId: check.invoice_id ?? null,
  };
}

function ResultCard({ title, result, error }: { title: string; result: Verdict | null; error?: string | null }) {
  if (!result && !error) return null;
  const valid = result?.valid ?? false;
  const Icon = valid ? ShieldCheck : ShieldX;
  return (
    <section
      aria-label={title}
      className={`rounded-xl border p-4 ${valid ? "border-pay/40 bg-pay-weak" : "border-hold/40 bg-hold-weak"}`}
    >
      <p className="eyebrow">{title}</p>
      <p className={`mt-1.5 flex gap-2 text-[15px] font-semibold ${valid ? "text-pay" : "text-hold"}`}>
        <Icon aria-hidden className="mt-0.5 size-4 shrink-0" />
        {result ? result.message : error}
      </p>
      {result?.valid && result.verdict ? (
        <p className="mt-1.5 text-[13px] text-ink-2">
          Factura <b className="text-ink">{result.invoiceId}</b> · decisión: <b className="text-ink">{VERDICT_LABELS[result.verdict]}</b>
        </p>
      ) : null}
    </section>
  );
}

export function VerifyPage() {
  const api = useApi();
  const key = useReceiptKey();
  const textId = useId();
  const [text, setText] = useState("");
  const [note, setNote] = useState<string | null>(null);
  const [results, setResults] = useState<Results>(EMPTY);
  const [checking, setChecking] = useState(false);

  const check = async (content: string) => {
    let parsed: unknown;
    try {
      parsed = JSON.parse(content);
    } catch {
      const invalid = { valid: false, message: NOT_JSON, verdict: null, invoiceId: null };
      setResults({ browser: invalid, server: null, serverError: null });
      return;
    }
    setChecking(true);
    const browser = key.data ? fromBrowser(verifyReceiptInBrowser(parsed, key.data)) : null;
    try {
      setResults({ browser, server: fromServer(await api.verifyReceipt(parsed)), serverError: null });
    } catch (error) {
      setResults({ browser, server: null, serverError: messageOf(error) });
    } finally {
      setChecking(false);
    }
  };

  const tryTampered = async () => {
    try {
      const { receipt, from, to } = tamperAmount(await api.getExampleReceipt());
      const content = JSON.stringify(receipt, null, 2);
      setText(content);
      setNote(`Tomamos un recibo de ejemplo firmado por Blinka Keeper y cambiamos el monto de ${from} a ${to}.`);
      await check(content);
    } catch (error) {
      setResults({ ...EMPTY, serverError: messageOf(error) });
    }
  };

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const content = await file.text();
    setText(content);
    setNote(`Recibo leído de ${file.name}.`);
    await check(content);
  };

  return (
    <article className="mx-auto max-w-3xl px-4 pt-10 pb-16">
      <p className="eyebrow text-brand">Recibos firmados</p>
      <h1 className="font-serif mt-2 text-[34px] leading-tight font-semibold tracking-[-0.015em] text-ink sm:text-[40px]">
        Verifica un recibo de Blinka Keeper
      </h1>
      <p className="mt-3 text-[17px] text-ink-2">
        Cada decisión de Blinka Keeper sale con un recibo firmado con Ed25519: la factura, lo que se leyó, las reglas, la
        decisión, el pago y su lugar en el registro. Pégalo o súbelo y lo comprobamos dos veces: aquí mismo, en tu
        navegador, sólo con la clave pública, y en el servidor de Blinka Keeper.
      </p>

      <p className="mt-5 flex flex-wrap items-center gap-2 text-[13px] text-ink-3">
        <KeyRound aria-hidden className="size-4" />
        {key.data ? (
          <>
            Clave pública <code className="font-mono text-ink-2">{key.data.key_id}</code> · Ed25519 ·{" "}
            <a href={KEY_URL} className="underline underline-offset-2 hover:text-ink">
              descargarla
            </a>
          </>
        ) : (
          "Cargando la clave pública…"
        )}
      </p>

      <label htmlFor={textId} className="mt-6 block text-[13px] font-semibold text-ink">
        Recibo (JSON)
      </label>
      <textarea
        id={textId}
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={10}
        spellCheck={false}
        placeholder='{"format": "custodio-receipt/1", "body": {…}, "signature": "…"}'
        className="mt-2 w-full rounded-xl border border-line-2 bg-surface-2 p-3 font-mono text-[12px] text-ink"
      />
      {note ? <p className="mt-2 text-[13px] text-ink-3">{note}</p> : null}

      <div className="mt-4 flex flex-wrap gap-2.5">
        <Button disabled={checking || !text.trim()} onClick={() => void check(text)}>
          <ShieldCheck aria-hidden /> Verificar
        </Button>
        <Button variant="outline" asChild>
          <label className="cursor-pointer">
            <FileUp aria-hidden /> Subir recibo
            <input type="file" accept="application/json,.json" className="sr-only" onChange={(event) => void upload(event)} />
          </label>
        </Button>
        <Button variant="outline" disabled={checking} onClick={() => void tryTampered()}>
          <Wand2 aria-hidden /> Probar con un recibo alterado
        </Button>
      </div>

      <div className="mt-6 grid gap-3">
        <ResultCard title="En tu navegador" result={results.browser} />
        <ResultCard title="En el servidor de Blinka Keeper" result={results.server} error={results.serverError} />
      </div>

      <section className="doc-prose mt-10">
        <h2>Sin Blinka Keeper de por medio</h2>
        <p>
          El paquete de cierre de mes trae cada recibo, la clave pública y <code>verificar_recibo.py</code>, que sólo
          usa la biblioteca estándar de Python: <code>python3 verificar_recibo.py recibo.json clave_publica.json</code>.
          Con <code>--exportar carpeta</code> deja lo necesario para comprobar la misma firma con OpenSSL:{" "}
          <code>openssl pkeyutl -verify -pubin -inkey clave.pem -rawin -in cuerpo.json -sigfile firma.bin</code>.
        </p>
      </section>
    </article>
  );
}
