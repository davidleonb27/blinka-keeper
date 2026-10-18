import type { Metadata } from "next";
import Link from "next/link";
import { DocPage, DocTable } from "@/components/site/doc-page";
import { RULES } from "@/lib/api/contracts";
import { repoFile } from "@/lib/site";

export const metadata: Metadata = { title: "Reglas R1–R15" };

const FAILS_WHEN: Record<string, string> = {
  R1: "Proveedor, monto, moneda o cuenta se leyeron con poca confianza o sin una cita verificada; o la moneda es ambigua («$» sin código); o las dos lecturas independientes no coinciden en esos datos o la segunda no se pudo hacer.",
  R2: "Hay texto oculto en el documento, o el texto visible trae instrucciones dirigidas al agente («pagar sin revisión»).",
  R3: "El proveedor no coincide con un beneficiario permitido (por identificación tributaria, nombre o alias), o está bloqueado.",
  R4: "La cuenta leída no es la cuenta registrada del beneficiario.",
  R5: "Ya se vio el mismo número de factura, o el mismo monto (±0,5 %) del mismo proveedor dentro de la ventana de duplicados.",
  R6: "La moneda no es la pactada, el monto fijo se sale de la tolerancia o se supera el tope mensual acordado.",
  R7: "Dos o más cobros del mismo proveedor en la ventana de fraccionamiento, cada uno bajo el tope de aprobación y juntos sobre él.",
  R8: "La moneda está fuera de las monedas permitidas.",
  R9: "El monto, en la moneda base, supera el tope de aprobación automática.",
  R10: "El monto supera el límite por pago.",
  R11: "Lo pagado solo en el mes más este pago supera el cupo de pago automático.",
  R12: "El saldo, después del pago, quedaría bajo la reserva.",
};

const EFFECT_LABEL = { hold: "Retener", escalate: "Escalar" } as const;

export default function RulesPage() {
  return (
    <DocPage
      href="/docs/reglas"
      lead="Quince reglas puras deciden cada factura. No llaman al modelo, no leen el reloj ni usan azar: con los mismos datos, la misma decisión."
    >
      <p>
        Viven en <a href={repoFile("apps/api/custodio/engine/rules.py")}>engine/rules.py</a>. Cada una devuelve pasa,
        retener, escalar u omitida, con una razón en español y las cifras concretas. Los topes, la reserva, las monedas y
        los beneficiarios son la <strong>política</strong> de cada empresa, que se edita en el panel o se escribe en
        español y se simula antes de aplicarla.
      </p>
      <DocTable>
        <table>
          <caption>Las 15 reglas, en el orden en que se evalúan</caption>
          <thead>
            <tr>
              <th scope="col">Regla</th>
              <th scope="col">Nombre</th>
              <th scope="col">Si falla</th>
              <th scope="col">Falla cuando</th>
            </tr>
          </thead>
          <tbody>
            {RULES.map((rule) => (
              <tr key={rule.id}>
                <th scope="row">{rule.id}</th>
                <td>{rule.label}</td>
                <td>{EFFECT_LABEL[rule.effect]}</td>
                <td>{FAILS_WHEN[rule.id]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DocTable>

      <h2 id="veredicto">Del resultado de las reglas al veredicto</h2>
      <ol>
        <li>Si alguna regla de retener falla, la factura se <strong>retiene</strong>: no se paga.</li>
        <li>Si no, y alguna regla de escalar falla, queda <strong>pendiente</strong> de una persona.</li>
        <li>Si todas pasan, se <strong>paga</strong> sola y se descuenta del saldo y del cupo del mes.</li>
      </ol>
      <p>
        Las facturas se deciden en orden de llegada y todas las cifras se comparan en la moneda base de la empresa. Una
        aprobación se aplica en el momento de aprobar y sólo paga si R12 sigue cumpliéndose; aprobar una factura nunca
        cambia la decisión de las otras. Ninguna aprobación paga algo que una regla de retener detuvo.
      </p>

      <h2 id="acta">Lo que explica el acta</h2>
      <ul>
        <li>Las quince reglas con su resultado y su razón con cifras.</li>
        <li>
          Un <strong>contrafactual</strong>: el cambio mínimo con el que se habría pagado («se habría pagado si la cuenta
          fuera la registrada»).
        </li>
        <li>El documento con las citas resaltadas y el texto oculto destapado.</li>
        <li>El hash de la decisión en el registro encadenado.</li>
      </ul>

      <h2 id="nueva">Proponer una regla nueva</h2>
      <p>
        Una regla nueva cambia lo que Custodio paga, así que se discute antes de escribirla: abre un issue con la plantilla
        «Regla nueva» y sigue los pasos de <Link href="/docs/contribuir">Contribuir</Link>. El auditor independiente debe
        comprobar lo mismo por otro camino de código.
      </p>
    </DocPage>
  );
}
