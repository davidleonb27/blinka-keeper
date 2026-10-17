import type { Metadata } from "next";
import Link from "next/link";
import { CodeBlock } from "@/components/developers/code-block";
import { DocPage } from "@/components/site/doc-page";
import { DEMO_URL, REPO_URL, VERCEL_DEPLOY_URL, repoFile } from "@/lib/site";

export const metadata: Metadata = { title: "Inicio rápido" };

const COMPOSE = `git clone ${REPO_URL}.git
cd custodio-blinka
cp .env.example .env        # opcional: todas las variables tienen un valor por defecto
docker compose up --build`;

const SMOKE_TEST = `curl http://localhost:8000/api/v1/health
# {"status":"ok","version":"0.1.0","anthropic":false,"payment_rail":"simulated"}

# Crea un espacio con la empresa demo y guarda su API key
KEY=$(curl -s -X POST http://localhost:3000/api/v1/workspaces \\
  -H 'Content-Type: application/json' -d '{}' \\
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["api_key"])')

# Pide una decisión al firewall
curl -s -X POST http://localhost:8000/api/v1/firewall/intents \\
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \\
  -d '{"agent": "mi-agente", "beneficiary_name": "Pulso Software Inc.", "bank_name": "Mercury",
       "account_number": "2214-1180", "amount": 840, "currency": "USD", "invoice_number": "PS-90001"}'`;

const LOCAL = `cd apps/api && uv sync && uv run uvicorn main:app --reload      # API en http://127.0.0.1:8000
cd apps/web && npm ci && API_INTERNAL_URL=http://127.0.0.1:8000 npm run dev   # web en http://localhost:3000`;

export default function QuickstartPage() {
  return (
    <DocPage href="/docs/inicio-rapido" lead="Prueba Custodio en la demo en 30 segundos, o córrelo en tu infraestructura con un comando.">
      <h2 id="demo">En la demo</h2>
      <ol>
        <li>
          Abre <a href={DEMO_URL}>{DEMO_URL.replace("https://", "")}</a> y pulsa <strong>«Probar la demo»</strong>. Recibes
          tu propio espacio, sin registro.
        </li>
        <li>En el panel, decide las facturas recibidas: verás lo pagado, lo retenido y lo pendiente, cada uno con su razón.</li>
        <li>Abre una fila para ver el acta con las quince reglas, y aprueba o rechaza lo pendiente.</li>
        <li>
          En <Link href="/desarrolladores">Desarrolladores</Link> está tu API key para el firewall y la configuración MCP.
        </li>
      </ol>

      <h2 id="empresa">Usar con mi empresa</h2>
      <p>
        Para tus propias facturas, pulsa <strong>«Usar con mi empresa»</strong> en el inicio, en el menú de la app o en el
        pie de página. Te lleva a <Link href="/empezar">/empezar</Link> y crea un espacio nuevo, vacío y en modo real: la
        demo no se mezcla con él.
      </p>
      <ol>
        <li>Perfil: el nombre de la empresa y su sitio; Custodio propone el país, la moneda y el saldo, y tú los corriges.</li>
        <li>Quién aprueba lo que se sale de las reglas.</li>
        <li>Tus reglas en tus palabras; ves los topes que entendió antes de seguir.</li>
        <li>
          Proveedores: un CSV con <code>nombre,identificación tributaria,banco,cuenta</code>. Sólo a estas cuentas se
          puede pagar.
        </li>
        <li>Una primera semana simulada con tus reglas (no se guarda ni se paga) y, al final, el panel.</li>
      </ol>
      <p>
        El panel empieza vacío. Pulsa <strong>«Subir facturas»</strong>: arrastra o elige varios PDF, imágenes, correos{" "}
        <code>.eml</code> o <code>.txt</code> (hasta 4 MB cada uno), o pega el texto de un correo. Cada archivo muestra
        si se recibió o por qué no; luego <strong>«Decidir N facturas»</strong> las pasa por las reglas. Tu sistema puede
        enviarlas también a <code>POST /api/v1/invoices</code> (campo <code>file</code> o <code>text</code>) y decidirlas
        con <code>POST /api/v1/invoices/process</code>.
      </p>
      <p>
        Custodio paga por su cuenta sólo a proveedores registrados, a su cuenta registrada. Para sumar uno después,
        entra a <Link href="/proveedores">Proveedores</Link> (también desde el diálogo de subida y desde el acta de una
        factura de un proveedor desconocido): importa un CSV con el mismo formato o escríbelo a mano, revisa la vista
        previa y aplícala. Queda como una versión nueva de la política en el registro. Los proveedores ya registrados no
        se cambian desde ahí: un cambio de cuenta llega en una factura y se verifica fuera de banda (R15).
      </p>
      <p>
        <strong>«Exportar CSV»</strong>, en la lista de facturas, descarga lo que ves (con el filtro y la búsqueda) con
        proveedor, número, monto, moneda, estado, regla decisiva, fecha e id de transferencia. Los pagos salen por el riel
        que tenga configurado tu instalación; sin configuración es el simulado y no se mueve dinero (ver{" "}
        <Link href="/docs/rieles">Rieles de pago</Link>).
      </p>

      <h2 id="autoalojado">Autoalojado en un comando</h2>
      <p>Requisitos: Docker con Compose v2. Levanta Postgres 16, la API y la web:</p>
      <CodeBlock label="Terminal" code={COMPOSE} />
      <ul>
        <li>
          Web en <code>http://localhost:3000</code>, API en <code>http://localhost:8000/api/v1</code> y su referencia en{" "}
          <code>/api/v1/docs</code>.
        </li>
        <li>
          La API espera a que Postgres esté sano y aplica las migraciones antes de recibir tráfico. Los datos quedan en el
          volumen <code>custodio-data</code>: <code>docker compose down</code> los conserva y{" "}
          <code>docker compose down -v</code> los borra.
        </li>
        <li>
          Sin <code>ANTHROPIC_API_KEY</code> funcionan las reglas, el auditor, el registro, el firewall y la lectura de
          texto y PDF con texto. Lo que necesita al modelo responde «requiere ANTHROPIC_API_KEY». Detalle en{" "}
          <Link href="/docs/configuracion">Configuración</Link>.
        </li>
      </ul>
      <h3>Comprueba que responde</h3>
      <CodeBlock label="Prueba de humo" code={SMOKE_TEST} />

      <h2 id="nube">En la nube</h2>
      <ul>
        <li>
          <strong>Vercel + Neon:</strong> <a href={VERCEL_DEPLOY_URL}>despliega con un botón</a>. Clona el repositorio,
          crea la base de datos en Neon y publica la web y la API como servicios de un proyecto.
        </li>
        <li>
          <strong>Un VPS:</strong> el mismo <code>docker compose up -d --build</code>, con HTTPS delante del puerto 3000
          (por ejemplo, Caddy). La web reenvía <code>/api/v1</code> a la API por la red interna.
        </li>
        <li>
          <strong>Railway y Fly.io:</strong> los mismos Dockerfiles; los pasos están en{" "}
          <a href={repoFile("docs/SELF_HOSTING.md")}>docs/SELF_HOSTING.md</a>.
        </li>
      </ul>

      <h2 id="local">Para desarrollar</h2>
      <p>Requisitos: Python 3.12 con uv y Node.js 24.</p>
      <CodeBlock label="Dos terminales" code={LOCAL} />
      <p>
        La compuerta única es <code>./scripts/check.sh</code>; más en <Link href="/docs/contribuir">Contribuir</Link>.
      </p>
    </DocPage>
  );
}
