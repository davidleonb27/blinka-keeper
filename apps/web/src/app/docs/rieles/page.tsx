import type { Metadata } from "next";
import Link from "next/link";
import { CodeBlock } from "@/components/developers/code-block";
import { DocPage, DocTable } from "@/components/site/doc-page";
import { REPO_URL, repoFile } from "@/lib/site";

export const metadata: Metadata = { title: "Rieles de pago" };

const PORT = `class PaymentRail(Protocol):
    @property
    def name(self) -> str: ...

    def execute(self, order: PaymentOrder) -> PaymentReceipt: ...`;

const ORDER = `@dataclass(frozen=True)
class PaymentOrder:
    idempotency_key: str      # workspace:factura; repetirla nunca debe pagar dos veces
    workspace_id: str
    invoice_id: str
    beneficiary_id: str | None
    supplier_name: str
    amount_base: Decimal      # en USD, lo que envía el riel
    currency: str             # como vino en la factura
    amount: Decimal           # como vino en la factura
    acta_url: str`;

const RAILS: [string, string, string][] = [
  ["simulated", "por defecto", "No mueve dinero ni usa la red; el recibo dice que fue simulado."],
  ["stripe_test", "STRIPE_SECRET_KEY=sk_test_…", "Transferencias reales de Stripe en modo prueba a cuentas conectadas de prueba."],
  ["el de tu empresa", "tu implementación", "Por ejemplo Blinka (ACH, wire, Bre-B, SPEI, Pix), con sus beneficiarios ya verificados."],
];

export default function RailsPage() {
  return (
    <DocPage
      href="/docs/rieles"
      lead="Custodio decide; el riel paga. Un riel sólo ejecuta lo que el motor aprobó y el auditor confirmó: no lee facturas, no evalúa reglas y nunca decide."
    >
      <DocTable>
        <table>
          <caption>Rieles disponibles (CUSTODIO_PAYMENT_RAIL)</caption>
          <thead>
            <tr>
              <th scope="col">Riel</th>
              <th scope="col">Cómo se activa</th>
              <th scope="col">Qué hace</th>
            </tr>
          </thead>
          <tbody>
            {RAILS.map(([name, how, text]) => (
              <tr key={name}>
                <th scope="row">{name}</th>
                <td>{how}</td>
                <td>{text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DocTable>
      <p>
        Con <code>stripe_test</code> y una clave real (<code>sk_live_</code>) o inválida, Custodio la ignora y usa el riel
        simulado. Sólo el panel de la empresa ejecuta pagos: el firewall, MCP, el reto y el red team nunca. El recorrido
        completo, las guardias y los topes están en <a href={repoFile("docs/PAYMENTS.md")}>docs/PAYMENTS.md</a>.
      </p>

      <h2 id="escribir">Cómo escribir un riel nuevo</h2>
      <p>
        Un riel implementa un protocolo de dos miembros, en{" "}
        <a href={repoFile("apps/api/custodio/payments/port.py")}>custodio/payments/port.py</a>:
      </p>
      <CodeBlock label="custodio/payments/port.py" code={PORT} />
      <p>Recibe una orden ya aprobada y devuelve un recibo:</p>
      <CodeBlock label="La orden que recibe execute" code={ORDER} />
      <ol>
        <li>
          Crea <code>custodio/payments/mi_riel.py</code> con una clase que implemente <code>execute</code>: llama a la API
          de pagos con la <code>idempotency_key</code> de la orden y devuelve un <code>PaymentReceipt</code> con el estado
          (<code>executed</code> o <code>failed</code>), el id externo y un enlace para verlo.
        </li>
        <li>
          <strong>Idempotencia.</strong> Reintentar la misma orden nunca debe pagar dos veces. Si el proveedor guarda los
          errores por llave, deriva una llave por intento y busca, antes de enviar, si el pago ya salió.
        </li>
        <li>
          <strong>Errores sin secretos.</strong> Un error del proveedor se vuelve un recibo <code>failed</code> con un
          mensaje en español armado con el tipo y el código del error, nunca con su texto original ni con la clave. Nunca
          lances una excepción hacia la API.
        </li>
        <li>
          <strong>Elección.</strong> Agrega el nombre del riel y su construcción en{" "}
          <a href={repoFile("apps/api/custodio/payments/choice.py")}>choose_rail</a>, con su guardia de claves: un riel de
          prueba nunca debe aceptar credenciales reales.
        </li>
        <li>
          <strong>Tests sin red.</strong> Pon un transporte falso debajo del SDK real del proveedor, como hace el riel de
          Stripe, y prueba la idempotencia, los errores y los topes. Un test con la red real se marca <code>live</code>.
        </li>
      </ol>
      <p>
        Cambiar de riel no toca el motor, el auditor ni el registro. Antes de programarlo, abre un issue con la plantilla{" "}
        <a href={`${REPO_URL}/issues/new?template=payment-rail.yml`}>«Riel de pago nuevo»</a> y lee{" "}
        <Link href="/docs/contribuir">Contribuir</Link>.
      </p>
    </DocPage>
  );
}
