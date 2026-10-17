"use client";

import { Activity, Eye, EyeOff, KeyRound, Plug, Workflow } from "lucide-react";
import { useState, useSyncExternalStore } from "react";
import { useApiMode } from "@/components/providers/api-provider";
import { PageHeader } from "@/components/shell/page-header";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/errors";
import { useHealth } from "@/lib/api/hooks";
import { API_BASE } from "@/lib/api/live-client";
import { RAIL_LABEL, RAIL_PITCH } from "@/lib/presentation";
import { browserWorkspaceStore } from "@/lib/api/workspace";
import { CodeBlock } from "./code-block";

const EXAMPLE_KEY = "ck_demo_7f3a91c2e4b0";
const KEY_PREVIEW = 8;
const noop = () => () => {};

function useOrigin(): string {
  return useSyncExternalStore(noop, () => window.location.origin, () => "");
}

function useApiKey(): string | null {
  return useSyncExternalStore(noop, () => browserWorkspaceStore.readApiKey(), () => null);
}

function firewallExample(base: string, key: string): string {
  return `curl -X POST ${base}/firewall/intents \\
  -H "Authorization: Bearer ${key}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent": "erp-bot",
    "beneficiary_name": "Andes Code SAS",
    "beneficiary_tax_id": "901.482.337-1",
    "bank_name": "Banco Popular",
    "account_number": "9902",
    "amount": 4800,
    "currency": "USD",
    "invoice_number": "AC-2026-11",
    "description": "Equipo de desarrollo, noviembre"
  }'`;
}

const RESPONSE_EXAMPLE = `{
  "decision": {
    "invoice_id": "INT-0042",
    "agent_verdict": "hold",
    "status": "hold",
    "explanation": "Se retiene: no se paga. La cuenta pedida no es la registrada…",
    "rules": [ /* las quince reglas, en orden */ ]
  },
  "ledger_hash": "9f2c4e1ab7d03f55…",
  "acta_url": "/acta/INT-0042"
}`;

function mcpConfig(base: string, key: string): string {
  return JSON.stringify(
    {
      mcpServers: {
        custodio: {
          command: "npx",
          args: ["-y", "mcp-remote", `${base}/mcp`, "--header", `Authorization: Bearer ${key}`],
        },
      },
    },
    null,
    2,
  );
}

const MCP_TOOLS: [string, string][] = [
  ["submit_payment_intent", "Envía una intención de pago y recibe pagar, retener o escalar, con el acta."],
  ["get_decision", "Trae el acta completa de una decisión por su id."],
  ["get_policy", "Lee las reglas vigentes de la empresa."],
];

function ApiStatus() {
  const health = useHealth();
  if (health.error) return <p className="text-[13px] text-crit">API sin respuesta: {messageOf(health.error)}</p>;
  if (!health.data) return <p className="text-[13px] text-ink-3">Consultando la API…</p>;
  const { status, version, anthropic, payment_rail } = health.data;
  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-ink-2">
      <span className="inline-flex items-center gap-1.5 font-semibold text-pay">
        <Activity aria-hidden className="size-4" /> {status === "ok" ? "API en línea" : `API: ${status}`}
      </span>
      <span>versión {version}</span>
      <span>{anthropic ? "Lectura con modelo configurada" : "Lectura con modelo sin configurar"}</span>
      <span>Riel de pago: {RAIL_LABEL[payment_rail]}</span>
    </p>
  );
}

export function DevelopersPage() {
  const mode = useApiMode();
  const origin = useOrigin();
  const storedKey = useApiKey();
  const [revealed, setRevealed] = useState(false);
  const key = storedKey ?? EXAMPLE_KEY;
  const base = `${origin}${API_BASE}`;
  const shownKey = revealed ? key : `${key.slice(0, KEY_PREVIEW)}${"•".repeat(12)}`;

  return (
    <>
      <PageHeader
        title="Desarrolladores"
        subtitle="Custodio es un firewall de pagos: cualquier agente, de tu ERP o de Claude, envía una intención de pago y recibe la misma decisión que una factura subida, con su acta."
      />
      <p className="-mt-2 mb-4 max-w-[70ch] text-[13.5px] text-ink-2">{RAIL_PITCH}</p>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <section className="card-surface flex flex-col gap-3 p-5 xl:col-span-2" aria-labelledby="key-title">
          <h2 id="key-title" className="flex items-center gap-2 font-semibold">
            <KeyRound aria-hidden className="size-4 text-brand" /> Tu API key
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <code className="min-w-0 rounded-lg border border-line bg-surface-2 px-3 py-2 font-mono text-[13px] break-all">{shownKey}</code>
            <Button variant="outline" size="sm" onClick={() => setRevealed((v) => !v)} aria-pressed={revealed}>
              {revealed ? <EyeOff aria-hidden /> : <Eye aria-hidden />} {revealed ? "Ocultar" : "Mostrar"}
            </Button>
          </div>
          <ApiStatus />
          <p className="text-[12.5px] text-ink-3">
            {storedKey
              ? "Es de tu espacio de trabajo y sólo vive en este navegador. Trátala como una contraseña."
              : mode === "mock"
                ? "Llave de ejemplo: en modo de datos de ejemplo no hay un espacio real detrás."
                : "No encontramos la llave de este espacio en este navegador. Abre el panel una vez para crear tu espacio y su llave."}
          </p>
        </section>
        <section className="card-surface flex min-w-0 flex-col gap-3 p-5" aria-labelledby="firewall-title">
          <h2 id="firewall-title" className="flex items-center gap-2 font-semibold">
            <Workflow aria-hidden className="size-4 text-brand" /> Firewall de pagos
          </h2>
          <p className="text-[13.5px] text-ink-2">
            Mismas quince reglas, mismo auditor y mismo registro que una factura subida. El texto del documento nunca autoriza nada.
            El firewall responde; el pago lo hace el agente que pregunta, con su propio riel.
          </p>
          <CodeBlock label="Petición" code={firewallExample(base, shownKey)} copyText={firewallExample(base, key)} />
          <CodeBlock label="Respuesta" code={RESPONSE_EXAMPLE} />
        </section>
        <section className="card-surface flex min-w-0 flex-col gap-3 p-5" aria-labelledby="mcp-title">
          <h2 id="mcp-title" className="flex items-center gap-2 font-semibold">
            <Plug aria-hidden className="size-4 text-brand" /> Servidor MCP para Claude Desktop
          </h2>
          <p className="text-[13.5px] text-ink-2">
            Agrega esto a <code className="font-mono text-[12.5px]">claude_desktop_config.json</code> y reinicia Claude Desktop.
          </p>
          <CodeBlock label="claude_desktop_config.json" code={mcpConfig(base, shownKey)} copyText={mcpConfig(base, key)} />
          <ul className="flex flex-col gap-2">
            {MCP_TOOLS.map(([name, description]) => (
              <li key={name} className="rounded-xl border border-line px-3 py-2.5">
                <code className="font-mono text-[12.5px] font-semibold text-brand">{name}</code>
                <p className="text-[13px] text-ink-2">{description}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}
