import type { Metadata } from "next";
import Link from "next/link";
import { CodeBlock } from "@/components/developers/code-block";
import { DocPage, DocTable } from "@/components/site/doc-page";

export const metadata: Metadata = { title: "Firewall por API" };

const REQUEST = `curl -X POST "$CUSTODIO_URL/api/v1/firewall/intents" \\
  -H "Authorization: Bearer $CUSTODIO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent": "erp-bot",
    "beneficiary_name": "Pulso Software Inc.",
    "beneficiary_tax_id": "84-2219034",
    "bank_name": "Mercury",
    "account_number": "2214-1180",
    "amount": 840,
    "currency": "USD",
    "invoice_number": "PS-90001",
    "description": "Licencias de software"
  }'`;

const RESPONSE = `{
  "decision": {
    "invoice_id": "INV-A152B2C4C65D",
    "agent_verdict": "pay",
    "status": "paid_auto",
    "explanation": "Se paga: cumple las 15 reglas…",
    "counterfactual": null,
    "rules": [ /* las quince reglas, en orden, con su razón */ ]
  },
  "ledger_hash": "fc3d4706f54c89ba…",
  "acta_url": "https://tu-dominio/acta/INV-A152B2C4C65D"
}`;

const FIELDS: [string, string, string][] = [
  ["agent", "sí", "Quién pide el pago, por ejemplo erp-bot o claude-desktop."],
  ["beneficiary_name", "sí", "Nombre del proveedor."],
  ["account_number", "sí", "Cuenta a la que se pagaría; R4 la compara con la registrada."],
  ["amount", "sí", "Monto, como número."],
  ["currency", "sí", "Código ISO 4217, por ejemplo USD o COP."],
  ["invoice_number", "sí", "Número de la factura; R5 lo usa para detectar duplicados."],
  ["beneficiary_tax_id", "no", "Identificación tributaria (NIT, RFC, CNPJ…)."],
  ["bank_name", "no", "Banco de la cuenta."],
  ["issue_date", "no", "Fecha de emisión, AAAA-MM-DD."],
  ["description", "no", "Concepto."],
  ["document_text", "no", "Texto del documento original; también se revisa en busca de instrucciones escondidas."],
];

export default function FirewallPage() {
  return (
    <DocPage
      href="/docs/firewall"
      lead="Antes de pagar, tu ERP o tu agente le pregunta a Custodio. Recibe pagar, retener o escalar, con el acta y el hash en el registro."
    >
      <p>
        Una intención de pago recorre el mismo camino que una factura subida al panel: se lee, se decide con las reglas y
        el historial de la empresa, la revisa el auditor y queda en el registro. Por eso la decisión es la misma entre
        por donde entre.
      </p>

      <h2 id="autenticacion">Autenticación</h2>
      <p>
        Cada espacio de trabajo tiene una API key, que se muestra una vez al crearlo (<code>POST /api/v1/workspaces</code>)
        y en la página <Link href="/desarrolladores">Desarrolladores</Link> del navegador que lo creó. Se envía como{" "}
        <code>Authorization: Bearer &lt;api key&gt;</code>. El servidor sólo guarda su SHA-256.
      </p>

      <h2 id="peticion">Petición</h2>
      <CodeBlock label="POST /api/v1/firewall/intents" code={REQUEST} />
      <DocTable>
        <table>
          <caption>Campos de la intención de pago</caption>
          <thead>
            <tr>
              <th scope="col">Campo</th>
              <th scope="col">Obligatorio</th>
              <th scope="col">Qué es</th>
            </tr>
          </thead>
          <tbody>
            {FIELDS.map(([name, required, text]) => (
              <tr key={name}>
                <th scope="row">{name}</th>
                <td>{required}</td>
                <td>{text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DocTable>

      <h2 id="respuesta">Respuesta</h2>
      <CodeBlock label="200 OK" code={RESPONSE} />
      <ul>
        <li>
          <code>agent_verdict</code>: <code>pay</code> (puedes pagar), <code>hold</code> (no pagues: es claramente
          indebido) o <code>escalate</code> (no pagues todavía: una persona debe revisarlo en el acta).
        </li>
        <li>
          <code>rules</code>: las quince reglas con su resultado y su razón; <code>counterfactual</code> dice qué faltó.
        </li>
        <li>
          <code>ledger_hash</code>: el hash de la decisión en el registro encadenado; <code>acta_url</code>, el acta para
          una persona.
        </li>
      </ul>

      <h2 id="quien-paga">Quién paga</h2>
      <p>
        El firewall decide; <strong>no ejecuta el pago</strong>, ni siquiera si una persona aprueba la intención en el
        panel. Paga el agente que preguntó, con su propio riel, y sólo si la respuesta fue <code>pay</code>.
      </p>

      <h2 id="errores">Errores y límites</h2>
      <p>
        Todo error responde JSON con <code>detail</code> en español y un <code>code</code> estable:{" "}
        <code>invalid_api_key</code> (401), <code>invalid_request</code> (422), <code>rate_limited</code> (429, con{" "}
        <code>Retry-After</code>). Las peticiones tienen límites por IP y por espacio.
      </p>
    </DocPage>
  );
}
