/**
 * What the jury reads on /jurado, mirrored in docs/JUDGE-GUIDE.md. Every figure comes from docs/BLINKA.md,
 * docs/MEASUREMENTS.md, docs/DATASET.md or the code (RateLimits, llm_daily_budget_usd); what was not measured says so.
 */
import { DEMO_URL, REPO_URL, repoFile } from "@/lib/site";

/** Lanes whose routes the guide already links while they travel to main; the e2e reports them instead of failing. */
export const PENDING_LANES = ["L21", "L23", "L26", "L27"] as const;
export type PendingLane = (typeof PENDING_LANES)[number];

export interface ProofLink {
  label: string;
  href: string;
  /** Set while the feature lives on a lane that has not reached main yet. */
  lane?: PendingLane;
  /** What the jury must do first for the link to show what it promises. */
  hint?: string;
}

export interface Claim {
  text: string;
  proofs: ProofLink[];
}

export interface Criterion {
  id: string;
  title: string;
  weight: number;
  question: string;
  claims: Claim[];
}

const ACTA_PAID = "/panel?acta=F-004";
const AFTER_BATCH = "Primero pulsa «Decidir las facturas» en el panel.";

export const CRITERIA: readonly Criterion[] = [
  {
    id: "impacto",
    title: "Impacto en el reto",
    weight: 30,
    question: "¿Qué tan bien resuelve el problema real que planteó la empresa?",
    claims: [
      {
        text:
          "Revisa cada cuenta por pagar, paga sola la que cabe en las reglas de la empresa, retiene lo indebido y espera a " +
          "una persona en lo demás. Con las 36 facturas de la empresa demo en producción: 17 pagadas solas, 5 retenidas, " +
          "14 para una persona y 0 pagos indebidos según el auditor.",
        proofs: [{ label: "Decidir el lote en el panel", href: "/panel" }],
      },
      {
        text:
          "Paga de verdad: lo aprobado sale como transferencia de Stripe en modo prueba y el acta la comprueba en vivo " +
          "contra Stripe, campo por campo.",
        proofs: [
          { label: "Ver un pago real en Stripe", href: ACTA_PAID, hint: AFTER_BATCH },
          { label: "Pagos del espacio", href: "/pagos" },
        ],
      },
      {
        text:
          "Cuando algo se sale de las reglas pide permiso con el porqué; si lo puede arreglar el proveedor, le manda un " +
          "enlace de corrección (/proveedor/c/…) y la corrección vuelve a pasar por las 15 reglas.",
        proofs: [{ label: "Pedir corrección", href: "/panel?acta=F-039", lane: "L23", hint: AFTER_BATCH }],
      },
      {
        text:
          "Cierra el ciclo: cuadra los pagos contra el extracto del banco y arma el paquete de cierre del mes.",
        proofs: [{ label: "Conciliación y cierre", href: "/conciliacion" }],
      },
    ],
  },
  {
    id: "innovacion",
    title: "Innovación",
    weight: 20,
    question: "¿Va más allá de lo obvio y usa la IA con intención?",
    claims: [
      {
        text:
          "El modelo sólo lee y cita; deciden 15 reglas en código y un auditor independiente recalcula cada pago por otro " +
          "camino. Un dato sin cita verificada cuenta como no leído.",
        proofs: [{ label: "Las 15 reglas", href: "/docs/reglas" }],
      },
      {
        text:
          "Doble lectura independiente: un segundo lector lee el mismo documento; si no coinciden en proveedor, monto, " +
          "moneda o cuenta, la factura no se paga sola y el acta muestra las dos lecturas.",
        proofs: [{ label: "Doble lectura en el acta", href: "/docs/seguridad", lane: "L21" }],
      },
      {
        text:
          "Reglas en tus palabras: la política se escribe en español, se compila a código y se simula contra lo recibido " +
          "antes de aplicarla. Aprende de las aprobaciones («Aprobar sólo esta vez», «Custodio sugiere») sin tocar las " +
          "reglas duras.",
        proofs: [{ label: "Reglas en tus palabras", href: "/reglas", lane: "L27" }],
      },
      {
        text:
          "La factura electrónica oficial (DIAN UBL 2.1 y CFDI 4.0) se lee sin IA: CUFE, dígito de verificación del NIT " +
          "y totales se comprueban por código.",
        proofs: [
          { label: "Descargar una factura DIAN de prueba", href: "/demo/facturas/dian-ruta-legal-valida.xml", lane: "L26" },
        ],
      },
    ],
  },
  {
    id: "tecnica",
    title: "Viabilidad técnica",
    weight: 20,
    question: "¿Funciona de verdad y el código lo respalda?",
    claims: [
      {
        text: "Intenta robarle: el reto público usa el mismo motor que paga, con el modelo real.",
        proofs: [
          { label: "Engáñalo", href: "/reto" },
          { label: "Arena: ataque contra defensa", href: "/arena" },
        ],
      },
      {
        text:
          "Cada decisión sale con un recibo firmado con Ed25519 y un guardián frente al riel: sin un recibo válido de esa " +
          "misma factura y monto, no se llama al riel.",
        proofs: [{ label: "Verifica un recibo alterado", href: "/verificar" }],
      },
      {
        text: "Registro encadenado con SHA-256: si alguien altera una decisión, la verificación dice dónde.",
        proofs: [{ label: "Registro", href: "/registro" }],
      },
      {
        text:
          "Medido, no prometido: lectura con el modelo real 36 de 36 en producción; prueba de estrés con 1.000 empresas, " +
          "25.139 facturas y 8.136 pagos re-auditados, 0 indebidos. Una corrida, datos sintéticos.",
        proofs: [{ label: "Mediciones y método", href: repoFile("docs/MEASUREMENTS.md") }],
      },
    ],
  },
  {
    id: "implementacion",
    title: "Viabilidad de implementación",
    weight: 20,
    question: "¿La empresa podría adoptarlo con sus restricciones reales?",
    claims: [
      {
        text:
          "Se configura con lo que la empresa ya tiene: /empezar arma los proveedores con su cuenta registrada desde una " +
          "lista, un contrato o facturas viejas, y las reglas desde un texto en español.",
        proofs: [{ label: "Configurar una empresa", href: "/empezar" }],
      },
      {
        text:
          "Encaja con Blinka sin esperar una API: archivo ISO 20022 pain.001 listo para subir, o como firewall por API y " +
          "MCP delante del agente que paga.",
        proofs: [
          { label: "Descargar pain.001", href: "/pagos", hint: AFTER_BATCH },
          { label: "Firewall por API y MCP", href: "/docs/firewall" },
        ],
      },
      {
        text:
          "Recibe facturas por donde ya llegan, incluido WhatsApp real (Cloud API de Meta, webhook firmado), y responde " +
          "con la decisión.",
        proofs: [{ label: "WhatsApp real", href: "/panel", hint: "La tarjeta aparece en el panel cuando el canal está activo." }],
      },
      {
        text: "Corre donde la empresa quiera: Vercel + Postgres o un solo docker compose up. Código abierto, MIT.",
        proofs: [{ label: "Autoalojar", href: "/docs/inicio-rapido#autoalojado" }],
      },
    ],
  },
  {
    id: "presentacion",
    title: "Presentación",
    weight: 10,
    question: "¿Se entiende y se puede comprobar?",
    claims: [
      {
        text: "Todo se comprueba en el producto en un clic, en este orden, en dos minutos.",
        proofs: [{ label: "Recorrido de 2 minutos", href: "#recorrido" }],
      },
      {
        text: "Lo honesto primero: qué es real, qué es simulado y qué no medimos.",
        proofs: [
          { label: "Real vs. simulado", href: "#real-vs-simulado" },
          { label: "Código en GitHub", href: REPO_URL },
        ],
      },
    ],
  },
];

export interface WalkStep {
  title: string;
  detail: string;
  href: string;
  action: string;
}

export const WALKTHROUGH: readonly WalkStep[] = [
  {
    title: "Decide el lote",
    detail: "En el panel, pulsa «Decidir las facturas»: cada una queda pagada, retenida o esperando a una persona, con su razón.",
    href: "/panel",
    action: "Abrir el panel",
  },
  {
    title: "Abre un pago real",
    detail: "El acta de F-004: las 15 reglas, la cita del documento y «Pago en Stripe» verificado en vivo.",
    href: ACTA_PAID,
    action: "Ver el acta",
  },
  {
    title: "Intenta engañarlo",
    detail: "Escribe una factura trampa en el reto: instrucción escondida, cuenta cambiada o cobro partido.",
    href: "/reto",
    action: "Ir al reto",
  },
  {
    title: "Cambia una regla",
    detail: "Escribe una regla en español, compílala y mira qué facturas cambiarían antes de aplicarla.",
    href: "/reglas",
    action: "Abrir reglas",
  },
  {
    title: "Verifica un recibo",
    detail: "Prueba con un recibo alterado: la firma no cuadra y dice qué campo cambió.",
    href: "/verificar",
    action: "Ir a verificar",
  },
];

export type Reality = "real" | "simulated" | "absent";

export interface RealityRow {
  part: string;
  status: Reality;
  detail: string;
}

export const REALITY_LABELS: Record<Reality, string> = {
  real: "Real",
  simulated: "Simulado",
  absent: "No se hace",
};

export const REAL_VS_SIMULATED: readonly RealityRow[] = [
  {
    part: "Lectura con Claude",
    status: "real",
    detail: "En producción con el modelo real; 36 de 36 facturas sintéticas bien leídas en una corrida.",
  },
  {
    part: "Stripe",
    status: "real",
    detail: "API real en modo prueba: dinero de prueba, transferencias reales leídas de vuelta. Las claves live se rechazan.",
  },
  {
    part: "WhatsApp",
    status: "real",
    detail: "Cloud API de Meta con webhook firmado (HMAC). Se activa con cuatro variables; sin ellas la tarjeta no aparece.",
  },
  {
    part: "Blinka",
    status: "simulated",
    detail: "Archivo pain.001 listo e instrucción armada por el adaptador payments/blinka.py; no se envía porque Blinka no tiene API pública.",
  },
  {
    part: "DIAN y SAT",
    status: "absent",
    detail: "No se consultan. El XML se valida localmente (forma del CUFE, NIT, totales); la firma digital no se verifica.",
  },
  {
    part: "Banco",
    status: "simulated",
    detail: "Sin conexión bancaria: la conciliación lee un extracto CSV o PDF que se sube; la demo trae uno ficticio.",
  },
  {
    part: "Lista OFAC",
    status: "real",
    detail: "Copia fechada de la lista SDN del Tesoro de EE. UU. (15 oct 2026) que viaja con el código; no se consulta en vivo.",
  },
  {
    part: "Empresa y proveedores",
    status: "simulated",
    detail: "La empresa demo y sus proveedores son ficticios; cada visitante recibe su propio espacio.",
  },
];

export interface AdoptionItem {
  title: string;
  points: string[];
  link?: ProofLink;
}

export const ADOPTION: readonly AdoptionItem[] = [
  {
    title: "Puesta en marcha",
    points: [
      "/empezar guía seis pasos: nombre, país y moneda, quién aprueba, proveedores desde documentos, reglas en español y la primera semana decidida.",
      "Tiempo de puesta en marcha con una empresa real: NO MEDIDO (no hemos cronometrado a un cliente).",
    ],
    link: { label: "Probar /empezar", href: "/empezar" },
  },
  {
    title: "Costo del modelo",
    points: [
      "Costo por factura: NO MEDIDO. El código estima el gasto de cada llamada y corta al llegar al tope diario (25 USD por despliegue y día, configurable).",
      "El segundo lector se estima en 1 a 2 centavos de USD por factura; estimación, NO MEDIDO.",
      "Sin modelo siguen funcionando las 15 reglas, el auditor, el registro, el firewall y la lectura de PDF con texto y de factura electrónica XML: costo de modelo cero.",
    ],
    link: { label: "Mediciones", href: repoFile("docs/MEASUREMENTS.md") },
  },
  {
    title: "Dónde corre",
    points: [
      `Hoy en Vercel (web y API en Python) con Postgres: ${DEMO_URL}.`,
      "Autohospedable: docker compose up con Postgres 16, o Railway, Fly.io y Vercel + Neon. Las migraciones corren solas.",
    ],
    link: { label: "Guía de autoalojado", href: repoFile("docs/SELF_HOSTING.md") },
  },
  {
    title: "Datos y privacidad",
    points: [
      "Se guarda en el Postgres de la empresa: el documento, lo leído con sus citas, cada decisión con su acta y el registro encadenado.",
      "El modelo ve el documento de la factura (y el texto de las reglas al compilarlas). No ve claves, no decide y no puede mover dinero.",
      "Hoy el número de cuenta se guarda tal cual porque es demo; en producción iría una huella y el número viviría en Blinka.",
    ],
  },
  {
    title: "Integración con Blinka",
    points: [
      "Archivo ISO 20022 pain.001.001.09 con los pagos aprobados, para subir a Blinka o a un banco.",
      "Adaptador payments/blinka.py: elige la red por moneda (ACH, wire, Bre-B, SPEI, Pix) y arma la instrucción con llave de idempotencia; la llamada real queda marcada en el código.",
      "Plan de dos semanas en docs/BLINKA.md: sandbox, modo sombra con tres clientes y luego modo firewall.",
    ],
    link: { label: "Custodio para Blinka", href: repoFile("docs/BLINKA.md") },
  },
  {
    title: "Límites y salvaguardas",
    points: [
      "Topes: 20 llamadas al modelo por minuto por IP y 30 por espacio; 40 transferencias de prueba por espacio y 2.000 por día; 5 intentos de pago por factura.",
      "Falla cerrada: sin modelo, sin segunda lectura o sin presupuesto, la factura escala; nunca se paga con una sola lectura dudosa.",
      "Guardián del pago: el riel sólo se llama con un recibo firmado que coincide en factura, monto, moneda y cuenta registrada.",
    ],
    link: { label: "Seguridad", href: "/docs/seguridad" },
  },
  {
    title: "Lo que falta para producción",
    points: [
      "Inicio de sesión, SSO y roles; hoy cada visitante recibe un espacio con una API key.",
      "Conexión bancaria real y la API de pagos de Blinka (endpoint, webhooks, sandbox).",
      "KYC/KYB, SOC 2 y claves por cliente en un almacén de secretos.",
      "Consultar DIAN y SAT y verificar la firma digital de la factura electrónica.",
      "Medir con facturas reales de un piloto: exactitud, escalamientos de más y costo por decisión.",
    ],
  },
];
