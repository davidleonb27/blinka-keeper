import type { Metadata } from "next";
import { DocPage, DocTable } from "@/components/site/doc-page";
import { repoFile } from "@/lib/site";

export const metadata: Metadata = { title: "Configuración" };

interface Variable {
  name: string;
  fallback: string;
  text: string;
}

const VARIABLES: readonly Variable[] = [
  {
    name: "ANTHROPIC_API_KEY",
    fallback: "sin definir",
    text: "Clave de Claude. Opcional: sin ella, lo que necesita al modelo responde 503 con el código model_not_configured y no decide nada.",
  },
  {
    name: "DATABASE_URL",
    fallback: "SQLite local",
    text: "Postgres (en Neon, la cadena postgresql:// que te da). En docker compose ya apunta al Postgres del compose.",
  },
  {
    name: "CUSTODIO_PAYMENT_RAIL",
    fallback: "simulated",
    text: "Riel que ejecuta lo aprobado: simulated (no mueve dinero), stripe_test (Stripe en modo prueba) o blinka_simulated (arma la instrucción para Blinka sin enviarla).",
  },
  {
    name: "STRIPE_SECRET_KEY",
    fallback: "sin definir",
    text: "Sólo claves sk_test_. Con una clave real o inválida, Custodio la ignora y usa el riel simulado.",
  },
  {
    name: "CUSTODIO_RECEIPT_SIGNING_KEY",
    fallback: "derivada de DATABASE_URL",
    text: "Clave Ed25519 que firma el recibo de cada decisión (PEM PKCS#8, o la semilla de 32 bytes en base64 o hex). Sin ella se deriva con HKDF de DATABASE_URL: la misma en cada arranque, nunca una nueva.",
  },
  {
    name: "CUSTODIO_LLM_DAILY_BUDGET_USD",
    fallback: "25",
    text: "Tope de gasto en el modelo por día UTC para todo el despliegue. Al llegar, el modelo deja de llamarse; las reglas siguen.",
  },
  {
    name: "CUSTODIO_PUBLIC_BASE_URL",
    fallback: "vacío",
    text: "URL pública de la web, sin barra final. Arma el enlace al acta (acta_url) que devuelve el firewall.",
  },
  {
    name: "API_INTERNAL_URL",
    fallback: "http://api:8000 en el compose",
    text: "Dónde reenvía la web /api/v1 fuera de Vercel. Next.js lo fija al construir la web.",
  },
  {
    name: "POSTGRES_PASSWORD",
    fallback: "custodio",
    text: "Contraseña del Postgres que levanta docker compose. Cámbiala en un servidor.",
  },
  {
    name: "CUSTODIO_MODEL_FAST, CUSTODIO_MODEL_SMART, CUSTODIO_MODEL_CHEAP",
    fallback: "Sonnet, Opus y Haiku",
    text: "Qué modelo usa cada tarea: lectura y narración; reglas en español, perfil y red team; triaje del reto público.",
  },
];

const WITHOUT_MODEL = [
  ["Motor de 15 reglas y auditor independiente", "funciona"],
  ["Registro encadenado y su verificación", "funciona"],
  ["Firewall por API y MCP", "funciona: la intención se lee por etiquetas"],
  ["Facturas en texto y PDF con texto", "funciona: se leen las líneas «Campo: valor»; lo que ninguna dice queda sin leer y R1 lo escala"],
  ["Imágenes y PDF escaneados", "responde «requiere ANTHROPIC_API_KEY»"],
  ["Reglas escritas en español, perfil de empresa, importar proveedores", "responde «requiere ANTHROPIC_API_KEY»"],
  ["Red team y narración del acta", "el red team avisa que requiere la clave; el acta sale sin narración"],
] as const;

export default function ConfigurationPage() {
  return (
    <DocPage
      href="/docs/configuracion"
      lead="Todo se configura con variables de entorno y todas son opcionales: sin ninguna, Custodio arranca con la empresa demo, el riel simulado y sin modelo."
    >
      <p>
        Copia <a href={repoFile(".env.example")}>.env.example</a> a <code>.env</code>; docker compose lo lee solo. Los
        secretos viven sólo en el entorno: nunca en el repositorio, los logs, las respuestas de la API ni los errores.
      </p>
      <DocTable>
        <table>
          <caption>Variables de entorno</caption>
          <thead>
            <tr>
              <th scope="col">Variable</th>
              <th scope="col">Por defecto</th>
              <th scope="col">Qué hace</th>
            </tr>
          </thead>
          <tbody>
            {VARIABLES.map((variable) => (
              <tr key={variable.name}>
                <th scope="row">{variable.name}</th>
                <td>{variable.fallback}</td>
                <td>{variable.text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DocTable>

      <h2 id="sin-modelo">Sin ANTHROPIC_API_KEY</h2>
      <p>
        Custodio está hecho para que el modelo nunca decida, así que lo esencial funciona sin él. El endpoint{" "}
        <code>GET /api/v1/health</code> dice si hay clave (<code>anthropic</code>) y qué riel está activo.
      </p>
      <DocTable>
        <table>
          <caption>Qué funciona sin modelo</caption>
          <thead>
            <tr>
              <th scope="col">Función</th>
              <th scope="col">Sin clave</th>
            </tr>
          </thead>
          <tbody>
            {WITHOUT_MODEL.map(([feature, status]) => (
              <tr key={feature}>
                <td>{feature}</td>
                <td>{status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DocTable>
      <p>Respuesta de una función que necesita al modelo:</p>
      <pre tabIndex={0} className="overflow-x-auto rounded-xl border border-line bg-surface-2 p-3 font-mono text-[12.5px]">
        {`HTTP/1.1 503
{"detail": "Esta función requiere ANTHROPIC_API_KEY y este servidor no la tiene. …", "code": "model_not_configured"}`}
      </pre>
    </DocPage>
  );
}
