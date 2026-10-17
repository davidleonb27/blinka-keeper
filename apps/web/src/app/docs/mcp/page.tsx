import type { Metadata } from "next";
import Link from "next/link";
import { CodeBlock } from "@/components/developers/code-block";
import { DocPage, DocTable } from "@/components/site/doc-page";

export const metadata: Metadata = { title: "MCP" };

const CLAUDE_DESKTOP = JSON.stringify(
  {
    mcpServers: {
      custodio: {
        command: "npx",
        args: ["-y", "mcp-remote", "https://tu-dominio/api/v1/mcp", "--header", "Authorization:${AUTH_HEADER}"],
        env: { AUTH_HEADER: "Bearer <tu api key>" },
      },
    },
  },
  null,
  2,
);

const CLAUDE_CODE = `claude mcp add --transport http custodio https://tu-dominio/api/v1/mcp \\
  --header "Authorization: Bearer $CUSTODIO_API_KEY"`;

const TOOLS: [string, string][] = [
  ["submit_payment_intent", "Envía una intención de pago (los mismos campos que el firewall) y recibe la decisión con su acta."],
  ["get_decision", "Lee el acta de una decisión de este espacio por el id de la factura."],
  ["get_policy", "Lee la política vigente: topes, reserva, monedas y beneficiarios permitidos."],
];

export default function McpPage() {
  return (
    <DocPage
      href="/docs/mcp"
      lead="Custodio es también un servidor MCP: cualquier agente compatible, como Claude, le pregunta antes de pagar."
    >
      <p>
        El servidor está en <code>/api/v1/mcp</code> (HTTP transmisible, sin estado, respuestas JSON) y se autentica con la
        API key del espacio como <code>Authorization: Bearer</code>. Usa los mismos servicios y límites que el{" "}
        <Link href="/docs/firewall">firewall por API</Link>, así que una intención recibe la misma decisión por las dos
        puertas.
      </p>

      <h2 id="herramientas">Herramientas</h2>
      <DocTable>
        <table>
          <caption>Herramientas del servidor MCP</caption>
          <thead>
            <tr>
              <th scope="col">Herramienta</th>
              <th scope="col">Qué hace</th>
            </tr>
          </thead>
          <tbody>
            {TOOLS.map(([name, text]) => (
              <tr key={name}>
                <th scope="row">{name}</th>
                <td>{text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DocTable>
      <p>
        Las instrucciones del servidor le piden al agente enviar la intención antes de pagar y no pagar nunca algo que
        Custodio retuvo o escaló.
      </p>

      <h2 id="claude-desktop">Claude Desktop</h2>
      <p>
        En <code>claude_desktop_config.json</code>, con el puente <code>mcp-remote</code>:
      </p>
      <CodeBlock label="claude_desktop_config.json" code={CLAUDE_DESKTOP} />

      <h2 id="claude-code">Claude Code</h2>
      <CodeBlock label="Terminal" code={CLAUDE_CODE} />

      <p>
        Reemplaza <code>tu-dominio</code> por la URL de tu instancia (en local, <code>http://localhost:8000</code>). Tu API
        key está en <Link href="/desarrolladores">Desarrolladores</Link>.
      </p>
    </DocPage>
  );
}
