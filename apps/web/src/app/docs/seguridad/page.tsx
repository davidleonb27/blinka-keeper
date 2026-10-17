import type { Metadata } from "next";
import { DocPage } from "@/components/site/doc-page";
import { repoFile } from "@/lib/site";

export const metadata: Metadata = { title: "Modelo de seguridad" };

const INVARIANTS = [
  "El motor es puro: sin I/O, sin reloj, sin azar, sin modelo. Mismo input, mismo output.",
  "Ningún pago ocurre si una regla de retener falla, ni deja el saldo bajo la reserva, ni siquiera con aprobación humana.",
  "El motor nunca lee las etiquetas del dataset (lo esperado y la trampa).",
  "Ningún texto de un documento cambia una regla ni autoriza nada; el texto dirigido al agente escala (R2).",
  "Un valor extraído sin una cita verificada por código cuenta como no leído (R1).",
  "El auditor recalcula cada pago por un camino de código distinto al del motor; si discrepa, gana el auditor y el pago no se hace.",
  "Toda escritura queda en el registro encadenado con SHA-256; verificarlo detecta cualquier alteración y dice dónde.",
  "Secretos sólo por variable de entorno; nunca en logs, errores, prompts ni respuestas de la API.",
];

export default function SecurityPage() {
  return (
    <DocPage
      href="/docs/seguridad"
      lead="Custodio asume que cada factura puede ser un ataque y que el modelo puede equivocarse o ser engañado. Por eso el modelo nunca decide."
    >
      <h2 id="invariantes">Invariantes</h2>
      <p>Cada una la hace cumplir un test que corre en cada commit, incluidos tests de propiedades sobre empresas aleatorias.</p>
      <ul>
        {INVARIANTS.map((invariant) => (
          <li key={invariant}>{invariant}</li>
        ))}
      </ul>

      <h2 id="lectura">Lectura con evidencia</h2>
      <p>
        El modelo devuelve cada dato con la <strong>cita exacta</strong> del documento. El código busca esa cita en el
        texto y comprueba que la respalde: un monto citado debe valer lo mismo, una fecha debe ser el mismo día, una cuenta
        debe tener los mismos dígitos. Sin esa verificación, el dato cuenta como no leído y R1 manda la factura a una
        persona.
      </p>
      <p>
        En un PDF, el texto oculto se detecta por código, no preguntándole al modelo: color igual al fondo, letra menor a 2
        puntos, fuera de la página, tapado por una figura o en los metadatos. Ese texto nunca llega al modelo como si fuera
        visible y R2 lo escala. Los PDF escaneados se envían al modelo como imágenes, nunca con su capa de texto, que es
        donde vive el texto oculto.
      </p>
      <p>
        Sin <code>ANTHROPIC_API_KEY</code>, el texto y los PDF con texto se leen por etiquetas (<code>Proveedor:</code>,{" "}
        <code>Monto:</code>, <code>Cuenta:</code>…). La primera línea que dice cada dato gana, y cada valor pasa por la misma
        verificación de citas.
      </p>

      <h2 id="auditor">Auditor independiente</h2>
      <p>
        Después de cada lote, el auditor recalcula cada pago desde los datos y la política, sin reutilizar el código del
        motor. Si encuentra un pago que no debía salir, el pago se detiene y el acta lo dice. Si el auditor objeta el lote
        completo, no sale ninguno de sus pagos.
      </p>

      <h2 id="registro">Registro encadenado</h2>
      <p>
        Cada recepción, decisión, aprobación, cambio de política y pago es un asiento cuyo hash es{" "}
        <code>sha256(hash_anterior + json_canónico(asiento))</code>; el primero parte de 64 ceros. Verificar la cadena
        recalcula todos los hashes y dice la primera posición alterada. En el panel, «alterar una copia» muestra cómo se
        rompe sin tocar el registro real.
      </p>

      <h2 id="pagos">Quién mueve el dinero</h2>
      <p>
        Un riel sólo ejecuta pagos que el motor aprobó y el auditor confirmó, y sólo desde el panel de la empresa. El
        firewall, MCP, el reto público y el red team nunca ejecutan pagos. Stripe sólo acepta claves de prueba.
      </p>

      <h2 id="reportar">Reportar una vulnerabilidad</h2>
      <p>
        Cualquier camino que lleve a pagar algo indebido está en el alcance. Repórtalo en privado según{" "}
        <a href={repoFile("SECURITY.md")}>SECURITY.md</a>, nunca en un issue público.
      </p>
    </DocPage>
  );
}
