import type { Metadata } from "next";
import Link from "next/link";
import { DocPage } from "@/components/site/doc-page";
import { LICENSE_NAME, REPO_URL } from "@/lib/site";

export const metadata: Metadata = { title: "Introducción" };

export default function IntroductionPage() {
  return (
    <DocPage
      href="/docs"
      lead="Custodio es un agente de cuentas por pagar de código abierto: revisa las facturas de una empresa y paga sólo lo que cabe en las reglas que la empresa definió."
    >
      <p>
        Retiene lo que es claramente indebido (una cuenta distinta a la registrada, un cobro repetido) y le pregunta a una
        persona todo lo demás. Cada decisión queda en un acta que se lee en un minuto y en un registro encadenado que no
        se puede alterar sin que se note.
      </p>

      <h2>El principio</h2>
      <p>
        <strong>El modelo lee, el código decide, la persona autoriza.</strong> Un agente que lee facturas y paga es el
        blanco ideal del fraude de pagos: basta una instrucción escondida en un PDF para convencerlo. Por eso en Custodio
        el modelo sólo lee y cita de dónde sacó cada dato; quien decide es código determinista que se puede leer, probar
        y auditar.
      </p>
      <ol>
        <li>
          <strong>Lee.</strong> Claude extrae proveedor, monto, moneda y cuenta, cada uno con la cita exacta del
          documento. El código verifica cada cita; lo que no se verifica cuenta como no leído.
        </li>
        <li>
          <strong>Decide.</strong> Quince reglas puras (<Link href="/docs/reglas">R1–R15</Link>) dicen pagar, retener o
          escalar. Un auditor independiente recalcula cada pago por otro camino de código.
        </li>
        <li>
          <strong>Explica.</strong> Cada decisión trae las quince reglas con sus cifras, un contrafactual («se habría
          pagado si…») y su posición en el registro encadenado.
        </li>
        <li>
          <strong>Pide permiso.</strong> Lo dudoso espera a una persona, que aprueba o rechaza desde el acta.
        </li>
      </ol>

      <h2>Qué puedes hacer con Custodio</h2>
      <ul>
        <li>Revisar las facturas de tu empresa desde el panel web, con reglas escritas en español y simuladas antes de aplicarlas.</li>
        <li>
          Poner un <Link href="/docs/firewall">firewall de pagos</Link> delante de tu ERP o de tu agente: le envías una
          intención de pago por API o por <Link href="/docs/mcp">MCP</Link> y te dice si pagar.
        </li>
        <li>
          Ejecutar lo aprobado por un <Link href="/docs/rieles">riel de pago</Link>: simulado, Stripe en modo prueba o el
          riel de tu empresa.
        </li>
        <li>Intentar engañarlo en «Róbale a Custodio» o ver a un atacante con Claude probar tus reglas en la arena.</li>
      </ul>

      <h2>Dos formas de usarlo</h2>
      <p>
        <strong>La demo</strong> no pide registro: cada visitante recibe su propio espacio con una empresa ficticia y
        una semana de facturas con trampas. <strong>Autoalojado</strong>, corre en tu infraestructura con un solo
        comando. Las dos están en el <Link href="/docs/inicio-rapido">inicio rápido</Link>.
      </p>

      <h2>Licencia</h2>
      <p>
        Custodio se publica bajo licencia {LICENSE_NAME}, a nombre del equipo DreamMakers (Adriano Joao Souza Reyna, Juan
        David Leon y Leober Ramos). El código, los tests y las mediciones están en{" "}
        <a href={REPO_URL}>GitHub</a>.
      </p>
    </DocPage>
  );
}
