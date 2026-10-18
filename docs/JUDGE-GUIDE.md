# Guía para el jurado · Judge guide

Versión web, con cada prueba a un clic: **https://blinka-keeper.vercel.app/jurado**. Esta página tiene el mismo
contenido (fuente: `apps/web/src/components/judge/judge-content.ts`). Sin registro y sin dinero real.

*Web version, every proof one click away: **https://blinka-keeper.vercel.app/jurado**. English below.*

---

## Español

**El reto Blinka:** un agente que revise las cuentas por pagar, decida cuáles pagar dentro de las reglas de la empresa y
pida permiso a una persona cuando algo se sale.

### Recorrido de 2 minutos

1. **Decide el lote.** En [/panel](https://blinka-keeper.vercel.app/panel), pulsa «Decidir las facturas»: cada una queda
   pagada, retenida o esperando a una persona, con su razón.
2. **Abre un pago real.** [El acta de F-004](https://blinka-keeper.vercel.app/panel?acta=F-004): las 15 reglas, la cita
   del documento y «Pago en Stripe» verificado en vivo.
3. **Intenta engañarlo.** En [/reto](https://blinka-keeper.vercel.app/reto), escribe una factura trampa: instrucción
   escondida, cuenta cambiada o cobro partido.
4. **Cambia una regla.** En [/reglas](https://blinka-keeper.vercel.app/reglas), escribe una regla en español,
   compílala y mira qué facturas cambiarían antes de aplicarla.
5. **Verifica un recibo.** En [/verificar](https://blinka-keeper.vercel.app/verificar), prueba con un recibo alterado: la
   firma no cuadra y dice qué campo cambió.

### Impacto en el reto · 30 %

| Afirmación | Pruébalo |
|---|---|
| Revisa cada cuenta por pagar, paga sola la que cabe en las reglas, retiene lo indebido y espera a una persona en lo demás. Con las 36 facturas de la empresa demo en producción: 17 pagadas solas, 5 retenidas, 14 para una persona y 0 pagos indebidos según el auditor. | [Decidir el lote en el panel](https://blinka-keeper.vercel.app/panel) |
| Paga de verdad: lo aprobado sale como transferencia de Stripe en modo prueba y el acta la comprueba en vivo contra Stripe, campo por campo. | [Ver un pago real en Stripe](https://blinka-keeper.vercel.app/panel?acta=F-004) (tras decidir el lote) · [Pagos](https://blinka-keeper.vercel.app/pagos) |
| Cuando algo se sale de las reglas pide permiso con el porqué; si lo puede arreglar el proveedor, le manda un enlace de corrección (`/proveedor/c/…`) y la corrección vuelve a pasar por las 15 reglas. | [Pedir corrección](https://blinka-keeper.vercel.app/panel?acta=F-039) |
| Cierra el ciclo: cuadra los pagos contra el extracto del banco y arma el paquete de cierre del mes. | [Conciliación y cierre](https://blinka-keeper.vercel.app/conciliacion) |

### Innovación · 20 %

| Afirmación | Pruébalo |
|---|---|
| El modelo sólo lee y cita; deciden 15 reglas en código y un auditor independiente recalcula cada pago por otro camino. Un dato sin cita verificada cuenta como no leído. | [Las 15 reglas](https://blinka-keeper.vercel.app/docs/reglas) |
| Doble lectura independiente: un segundo lector lee el mismo documento; si no coinciden en proveedor, monto, moneda o cuenta, no se paga sola y el acta muestra las dos lecturas. | [Doble lectura](https://blinka-keeper.vercel.app/docs/seguridad) |
| Reglas en tus palabras: la política se escribe en español, se compila a código y se simula antes de aplicarla. Aprende de las aprobaciones («Aprobar sólo esta vez», «Blinka Keeper sugiere») sin tocar las reglas duras. | [Reglas en tus palabras](https://blinka-keeper.vercel.app/reglas) |
| La factura electrónica oficial (DIAN UBL 2.1 y CFDI 4.0) se lee sin IA: CUFE, dígito de verificación del NIT y totales se comprueban por código. | [Factura DIAN de prueba](https://blinka-keeper.vercel.app/demo/facturas/dian-ruta-legal-valida.xml) |

### Viabilidad técnica · 20 %

| Afirmación | Pruébalo |
|---|---|
| Intenta robarle: el reto público usa el mismo motor que paga, con el modelo real. | [Engáñalo](https://blinka-keeper.vercel.app/reto) · [Arena](https://blinka-keeper.vercel.app/arena) |
| Cada decisión sale con un recibo firmado con Ed25519 y un guardián frente al riel: sin un recibo válido de esa misma factura y monto, no se llama al riel. | [Verifica un recibo alterado](https://blinka-keeper.vercel.app/verificar) |
| Registro encadenado con SHA-256: si alguien altera una decisión, la verificación dice dónde. | [Registro](https://blinka-keeper.vercel.app/registro) |
| Medido, no prometido: lectura con el modelo real 36 de 36 en producción; prueba de estrés con 1.000 empresas, 25.139 facturas y 8.136 pagos re-auditados, 0 indebidos. Una corrida, datos sintéticos. | [MEASUREMENTS.md](MEASUREMENTS.md) |

### Viabilidad de implementación · 20 %

| Afirmación | Pruébalo |
|---|---|
| Se configura con lo que la empresa ya tiene: `/empezar` arma los proveedores con su cuenta registrada desde una lista, un contrato o facturas viejas, y las reglas desde un texto en español. | [Configurar una empresa](https://blinka-keeper.vercel.app/empezar) |
| Encaja con Blinka sin esperar una API: archivo ISO 20022 pain.001 listo para subir, o como firewall por API y MCP delante del agente que paga. | [Descargar pain.001](https://blinka-keeper.vercel.app/pagos) · [Firewall](https://blinka-keeper.vercel.app/docs/firewall) |
| Recibe facturas por donde ya llegan, incluido WhatsApp real (Cloud API de Meta, webhook firmado), y responde con la decisión. | [WhatsApp real](https://blinka-keeper.vercel.app/panel) (la tarjeta aparece cuando el canal está activo) |
| Corre donde la empresa quiera: Vercel + Postgres o un solo `docker compose up`. Código abierto, MIT. | [Autoalojar](SELF_HOSTING.md) |

### Presentación · 10 %

| Afirmación | Pruébalo |
|---|---|
| Todo se comprueba en el producto en un clic, en este orden, en dos minutos. | [Recorrido](https://blinka-keeper.vercel.app/jurado#recorrido) |
| Lo honesto primero: qué es real, qué es simulado y qué no medimos. | [Real vs. simulado](#real-vs-simulado) |

### Cómo lo adopta una empresa

- **Puesta en marcha.** `/empezar` guía seis pasos: nombre, país y moneda, quién aprueba, proveedores desde documentos,
  reglas en español y la primera semana decidida. Tiempo con una empresa real: **NO MEDIDO**.
- **Costo del modelo.** Costo por factura: **NO MEDIDO**. El código estima el gasto de cada llamada y corta al llegar al
  tope diario (`llm_daily_budget_usd`, 25 USD por despliegue y día). El segundo lector se estima en 1 a 2 centavos de USD
  por factura (estimación de L21, NO MEDIDO). Sin modelo siguen funcionando las reglas, el auditor, el registro, el
  firewall y la lectura de PDF con texto y de factura electrónica XML.
- **Dónde corre.** Vercel (web y API en Python) con Postgres; autohospedable con Docker Compose, Railway, Fly.io o
  Vercel + Neon ([SELF_HOSTING.md](SELF_HOSTING.md)).
- **Datos y privacidad.** En el Postgres de la empresa: el documento, lo leído con sus citas, cada decisión con su acta
  y el registro encadenado. El modelo ve el documento (y el texto de las reglas al compilarlas); no ve claves, no
  decide, no mueve dinero. Hoy el número de cuenta se guarda tal cual (demo); en producción iría una huella.
- **Integración con Blinka.** Archivo pain.001.001.09; adaptador `apps/api/custodio/payments/blinka.py` (ACH, wire,
  Bre-B, SPEI, Pix, con llave de idempotencia; la llamada real queda marcada); plan de dos semanas en
  [BLINKA.md](BLINKA.md).
- **Límites y salvaguardas.** 20 llamadas al modelo por minuto por IP y 30 por espacio; 40 transferencias de prueba
  por espacio y 2.000 por día; 5 intentos de pago por factura (`RateLimits`). Falla cerrada: sin modelo, sin segunda
  lectura o sin presupuesto, la factura escala. Guardián del pago: el riel sólo se llama con un recibo firmado que
  coincide.
- **Lo que falta para producción.** Inicio de sesión, SSO y roles; conexión bancaria real y API de pagos de Blinka;
  KYC/KYB, SOC 2 y almacén de secretos por cliente; consultar DIAN/SAT y verificar la firma digital; medir con facturas
  reales de un piloto (exactitud, escalamientos de más, costo por decisión).

### Real vs. simulado

| Parte | Estado | Qué significa |
|---|---|---|
| Lectura con Claude | Real | En producción con el modelo real; 36 de 36 facturas sintéticas bien leídas en una corrida. |
| Stripe | Real | API real en modo prueba: dinero de prueba, transferencias reales leídas de vuelta. Las claves live se rechazan. |
| WhatsApp | Real | Cloud API de Meta con webhook firmado (HMAC). Se activa con cuatro variables; sin ellas la tarjeta no aparece. |
| Blinka | Simulado | Archivo pain.001 listo e instrucción armada por `payments/blinka.py`; no se envía porque Blinka no tiene API pública. |
| DIAN y SAT | No se hace | No se consultan. El XML se valida localmente (forma del CUFE, NIT, totales); la firma digital no se verifica. |
| Banco | Simulado | Sin conexión bancaria: la conciliación lee un extracto CSV o PDF que se sube; la demo trae uno ficticio. |
| Lista OFAC | Real | Copia fechada de la lista SDN del Tesoro de EE. UU. (15 oct 2026) que viaja con el código; no se consulta en vivo. |
| Empresa y proveedores | Simulado | Ficticios; cada visitante recibe su propio espacio. |

---

## English

**The Blinka challenge:** an agent that reviews a company's accounts payable, decides which to pay within the rules the
company sets, and asks a person for permission when something falls outside them.

### Two-minute walkthrough

1. **Decide the batch.** On [/panel](https://blinka-keeper.vercel.app/panel), press «Decidir las facturas»: each invoice
   ends up paid, held or waiting for a person, with its reason.
2. **Open a real payment.** [F-004's record](https://blinka-keeper.vercel.app/panel?acta=F-004): the 15 rules, the
   quote from the document and «Pago en Stripe», checked live against Stripe.
3. **Try to fool it.** On [/reto](https://blinka-keeper.vercel.app/reto), write a trick invoice: hidden instruction,
   changed account or split charge.
4. **Change a rule.** On [/reglas](https://blinka-keeper.vercel.app/reglas), write a rule in Spanish, compile it and see
   which invoices would change before applying it.
5. **Verify a receipt.** On [/verificar](https://blinka-keeper.vercel.app/verificar), try a tampered receipt: the
   signature fails and names the changed field.

### Rubric, mapped

- **Impact on the challenge (30 %).** Reviews every payable, pays on its own what fits the rules, holds what is improper
  and asks a person about the rest (36 demo invoices in production: 17 auto-paid, 5 held, 14 to a person, 0 improper
  payments per the auditor). Real Stripe test-mode transfers checked live in the record; supplier correction links;
  bank reconciliation and month-end close.
- **Innovation (20 %).** The model only reads and quotes; 15 rules in code decide and an independent auditor recomputes
  each payment. Independent double reading; rules written in plain Spanish, compiled and simulated; learning from
  approvals («approve only this once», «Blinka Keeper suggests») without touching hard rules; DIAN/CFDI e-invoices read with
  no AI.
- **Technical feasibility (20 %).** Public red-team challenge on the same engine; Ed25519-signed receipts and a guard
  in front of the payment rail; SHA-256 hash-chained ledger; measured: 36/36 real-model reading in production, stress
  test of 1,000 companies / 25,139 invoices / 8,136 re-audited payments with 0 improper (one run, synthetic data).
- **Implementation feasibility (20 %).** Guided setup at `/empezar` from documents the company already has (setup time
  with a real company: NOT MEASURED); ISO 20022 pain.001 file for Blinka today and an API/MCP firewall; real WhatsApp
  Cloud API intake; runs on Vercel + Postgres or `docker compose up`, MIT. Model cost per invoice: NOT MEASURED (daily
  spend cap of 25 USD per deployment). Missing for production: login/SSO and roles, real bank connection and Blinka's
  payments API, KYC/KYB, SOC 2, DIAN/SAT lookups, a pilot with real invoices.
- **Presentation (10 %).** Every claim one click from its proof at `/jurado`; honest real-vs-simulated table.

### Real vs. simulated

| Part | Status | Meaning |
|---|---|---|
| Reading with Claude | Real | Production, real model; 36 of 36 synthetic invoices read correctly in one run. |
| Stripe | Real | Real API in test mode: test money, real transfers read back. Live keys are refused. |
| WhatsApp | Real | Meta Cloud API with an HMAC-signed webhook; turned on by four variables, otherwise the card is hidden. |
| Blinka | Simulated | pain.001 file ready and instruction built by `payments/blinka.py`; not sent, Blinka has no public API. |
| DIAN and SAT | Not done | Not queried. The XML is validated locally (CUFE shape, NIT check digit, totals); the digital signature is not verified. |
| Bank | Simulated | No bank connection: reconciliation reads an uploaded CSV or PDF statement; the demo ships a fictitious one. |
| OFAC list | Real | Dated copy of the US Treasury SDN list (15 Oct 2026) shipped with the code; not queried live. |
| Company and suppliers | Simulated | Fictitious; each visitor gets their own workspace. |
