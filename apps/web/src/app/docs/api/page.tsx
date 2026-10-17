import type { Metadata } from "next";
import Link from "next/link";
import { DocPage, DocTable } from "@/components/site/doc-page";

export const metadata: Metadata = { title: "Referencia de la API" };

const ROUTES: [string, string][] = [
  ["GET /health", "Estado, versión, si hay modelo configurado y el riel de pago activo."],
  ["POST /workspaces", "Crea un espacio (demo o vacío) y devuelve su id y su API key, una sola vez."],
  ["GET /workspaces/current", "Empresa, saldo y métricas del espacio."],
  ["GET /policy · PUT /policy", "Lee o aplica la política; cada cambio queda en el registro."],
  ["POST /policy/compile", "Reglas escritas en español → propuesta de política simulada contra el historial (requiere modelo)."],
  ["POST /invoices", "Sube un PDF, una imagen o texto y lo lee."],
  ["POST /invoices/process", "Decide lo pendiente: motor, auditor y registro."],
  ["GET /decisions · GET /decisions/{id}", "Lista de decisiones y acta completa."],
  ["POST /decisions/{id}/approve · /reject", "Aprobación o rechazo de una persona."],
  ["GET /ledger · GET /ledger/verify", "Registro encadenado y su verificación."],
  ["POST /firewall/intents", "Intención de pago de otro agente → decisión con acta."],
  ["/mcp", "Servidor MCP con submit_payment_intent, get_decision y get_policy."],
];

export default function ApiPage() {
  return (
    <DocPage
      href="/docs/api"
      lead="La API REST vive bajo /api/v1 y publica su esquema OpenAPI. La referencia interactiva la genera la propia API, así que siempre coincide con el código."
    >
      <p>
        <a href="/api/v1/docs">Abrir la referencia interactiva</a> · <a href="/api/v1/openapi.json">Descargar openapi.json</a>
      </p>
      <h2 id="identidad">Identidad</h2>
      <p>
        El panel identifica el espacio con la cabecera <code>X-Custodio-Workspace</code>. El firewall y MCP usan{" "}
        <code>Authorization: Bearer &lt;api key&gt;</code>. Ver <Link href="/docs/firewall">Firewall por API</Link>.
      </p>
      <h2 id="rutas">Rutas principales</h2>
      <DocTable>
        <table>
          <caption>Rutas bajo /api/v1</caption>
          <thead>
            <tr>
              <th scope="col">Ruta</th>
              <th scope="col">Qué hace</th>
            </tr>
          </thead>
          <tbody>
            {ROUTES.map(([route, text]) => (
              <tr key={route}>
                <th scope="row">{route}</th>
                <td>{text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DocTable>
      <h2 id="errores">Errores</h2>
      <p>
        Toda respuesta de error es JSON con <code>detail</code> (en español, sin secretos) y <code>code</code> (estable,
        para programas). Un fallo nunca deja un pago a medias: la unidad de trabajo se revierte completa. Lo que necesita
        al modelo y no lo tiene responde <code>503</code> con <code>model_not_configured</code>.
      </p>
    </DocPage>
  );
}
