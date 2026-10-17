# Custodio para Blinka

> **Custodio decide; Blinka paga.** Una página para el equipo de Blinka: qué problema resuelve en sus clientes, dónde
> se conecta, qué está medido y qué falta.

Demo desplegada: https://custodio-blinka-green.vercel.app · Código: este repositorio (MIT).

## El problema de sus clientes

Los clientes de Blinka son empresas latinas que pagan a proveedores y contratistas en dólares, pesos y reales. Los
ataques que más les cuestan no rompen nada: piden que se pague algo que parece normal.

- **Cambio de cuenta.** Una factura idéntica a la de siempre, con otra cuenta de destino. Llega por correo o WhatsApp y
  una persona con prisa la paga.
- **Duplicados.** La misma factura otra vez, o con otro número y el mismo monto. Se paga dos veces y recuperar el
  dinero cuesta semanas.
- **Pagos partidos.** Dos o tres cobros chicos del mismo proveedor, cada uno bajo el tope de aprobación, que juntos lo
  superan.
- **Agentes de IA que pagan.** Cuando un agente lee facturas y paga solo, una instrucción escondida en el PDF («paga sin
  revisar», texto blanco sobre blanco) puede convencerlo.

No encontramos una cifra medida de cuánto pierden por esto las pymes de América Latina; las cifras externas que usamos
(FBI, AFP) son de Estados Unidos y están en [`BUSINESS.md`](BUSINESS.md). Para los clientes de Blinka, el tamaño del
problema hay que medirlo en un piloto.

## Dónde va Custodio

Custodio va **delante** de cada pago de Blinka. No mueve dinero: decide si un pago se hace, se retiene o espera a una
persona, y deja un acta que explica por qué. Blinka sigue siendo quien paga.

```
factura, agente o ERP ──▶ Custodio: el modelo lee, 15 reglas en código deciden, un auditor recalcula
                                │
                 pagar ─────────┼───────── retener / escalar
                   │                              │
                   ▼                              ▼
        Blinka paga por ACH, wire,       acta para una persona;
        Bre-B, SPEI o Pix                no sale nada
```

Dos formas de conectarlo:

1. **Firewall por API o MCP.** El agente de Blinka (o el del cliente) envía una intención de pago a
   `POST /api/v1/firewall/intents` o por el servidor MCP (`submit_payment_intent`) y recibe `pay`, `hold` o `escalate`
   con las 15 reglas, el enlace al acta y el hash en el registro. Blinka sólo ejecuta lo que vuelve `pay`. No hay que
   tocar el flujo de pagos de Blinka.
2. **Integrado, como riel.** Custodio decide y entrega el pago a Blinka por su API. Ya existe el adaptador
   (`apps/api/custodio/payments/blinka.py`, riel `blinka_simulated`): elige la red por moneda y país del beneficiario y
   arma la instrucción exacta que Blinka recibiría. Como Blinka aún no tiene API pública, la instrucción se arma y se
   muestra, pero no se envía; el código marca la línea donde va la llamada real.

| Moneda del pago | Red de Blinka |
|---|---|
| USD a un beneficiario en EE. UU. hasta 10.000 USD | ACH |
| USD sobre 10.000 USD, o a un beneficiario fuera de EE. UU. | wire |
| COP | Bre-B |
| MXN | SPEI |
| BRL | Pix |
| cualquier otra | no se paga: recibo `failed` con la razón |

La instrucción viaja en el acta (`decision.execution.instruction`):

```json
{
  "network": "ach",
  "amount": "840.00",
  "currency": "USD",
  "beneficiary_name": "Pulso Software Inc.",
  "beneficiary_tax_id": "84-2219034",
  "beneficiary_country": "US",
  "bank_name": "Mercury",
  "account_number": "202211887766",
  "reference": "https://custodio-blinka-green.vercel.app/acta/F05",
  "idempotency_key": "ws-1:F05"
}
```

Los datos bancarios salen del beneficiario **registrado**, nunca de la factura: si la factura trae otra cuenta, la
regla R4 la retiene antes de llegar aquí. La referencia es el enlace al acta, así que quien lea el extracto sabe por qué
se pagó. Los datos del ejemplo son sintéticos.

## Qué gana Blinka

- **Menos fraude y menos contracargos.** Los cambios de cuenta y los duplicados se retienen antes de que el dinero
  salga, que es cuando todavía no cuesta nada. Cuánto le ahorra esto a Blinka y a sus clientes: NO MEDIDO; es lo
  primero que mide el piloto.
- **Confianza para dejar que agentes paguen.** El modelo sólo lee y cita; deciden reglas en código que el cliente
  escribe en español. Lo grande o dudoso espera a una persona. Así Blinka puede ofrecer pagos por agente sin que una
  instrucción escondida mueva dinero.
- **Diferenciación.** Cada pago trae su acta: qué regla se cumplió, con qué cifras y qué habría que cambiar para
  pagarlo. Es un control que el cliente puede mostrarle a su contador o a su auditor.

## Lo que ya está medido

Todo se midió el 2026-10-17 y está publicado con su comando en [`DATASET.md`](DATASET.md),
[`MEASUREMENTS.md`](MEASUREMENTS.md) y el [`README`](../README.md). Lo que no aparece aquí no se midió.

| Dato | Valor | Dónde |
|---|---|---|
| Facturas del dataset dorado decididas en producción | 36 | espacio demo en producción |
| Pagadas solas / retenidas / pendientes de una persona | 17 / 5 / 14 | mismo espacio |
| Autonomía | 61,1 % | mismo espacio |
| Exactitud frente a las etiquetas | 1,0 | mismo espacio |
| Pagos indebidos según el auditor | 0 de 36 | mismo espacio |
| Prueba de estrés | 1.000 empresas, 25.139 facturas, 8.136 pagos re-auditados, 0 indebidos | `scripts/stress.py`, semilla fija |
| Lectura con el modelo real | 36 de 36 con proveedor, monto, moneda y cuenta correctos; 0 rechazos | una corrida contra producción |
| Topes del riel de prueba | 40 transferencias por espacio, 400 por día | código y tests |

Límites honestos: el dataset es sintético y de una sola empresa; la lectura se corrió una vez; ataques del red team,
intentos del reto público y latencia de los pagos: NO MEDIDO. No tenemos clientes ni pilotos todavía.

## Integración en 2 semanas

**Semana 1: conectar.**

1. Días 1 y 2: Blinka entrega un sandbox de su API de pagos (crear pago, consultar estado, webhooks) y una clave de
   prueba. La clave entra sólo por variable de entorno.
2. Días 2 a 4: en `BlinkaRail.execute`, donde está marcada la llamada, se envía la instrucción con su llave de
   idempotencia; el id de pago de Blinka queda en el acta y en el registro. Tests contra un transporte falso, como ya se
   hace con Stripe.
3. Día 5: los beneficiarios ya verificados por Blinka se importan como la lista de permitidos de cada cliente (reglas
   R3 y R4), así Custodio no pide datos que Blinka ya tiene.

**Semana 2: piloto.**

4. Días 6 a 8: tres clientes de Blinka en **modo sombra**: Custodio decide cada pago real, pero no bloquea nada. Se
   compara su decisión con lo que el cliente pagó.
5. Días 9 y 10: los clientes que quieran pasan a **modo firewall**: lo retenido no sale. Se mide autonomía, tasa de
   escalamiento, retenciones correctas y costo por decisión, con el mismo método que publicamos.

## Precio propuesto

Es una **propuesta**, no un precio validado: aún no medimos el costo real por decisión ni lo que un cliente pagaría.

| Opción | Cómo se cobra | Para qué caso |
|---|---|---|
| Por decisión | una tarifa por cada pago que Custodio decide, con las decisiones del piloto sin costo | clientes con pocos pagos grandes |
| Por volumen | un porcentaje pequeño del monto protegido, con un tope por pago | clientes con muchos pagos |
| Para Blinka | Blinka lo incluye en su plan y Custodio cobra a Blinka por decisión o por volumen | diferenciación de Blinka |

Los montos se fijan con Blinka al cerrar el piloto, con el costo por decisión medido (modelo, base de datos y hospedaje).
Hasta entonces, NO MEDIDO.

## Seguridad

- **El modelo nunca decide.** Lee y cita; un valor sin cita verificada cuenta como no leído y se escala. Deciden 12
  reglas en código, y un auditor independiente recalcula cada pago por otro camino: si no está de acuerdo, el pago no
  sale.
- **Claves sólo por referencia.** Toda clave entra por variable de entorno; nunca va en código, logs, prompts, respuestas
  de la API ni actas. Los errores del riel se arman con el tipo y el código del error, nunca con el mensaje original,
  que puede citar parte de la clave.
- **Las claves `live` se rechazan.** Con una clave `sk_live_` o `rk_live_` el despliegue vuelve al riel simulado y lo
  avisa en el log sin mostrar la clave.
- **Topes.** 40 transferencias de prueba por espacio, 400 por día y 5 intentos por factura. Cada pago lleva su llave de
  idempotencia, así que un reintento nunca paga dos veces.
- **Registro encadenado.** Cada decisión y cada pago quedan en un registro con SHA-256; `GET /api/v1/ledger/verify` dice
  si alguien lo alteró y dónde.
- **Lo que no paga.** El firewall, el reto público y el red team deciden pero nunca ejecutan un pago.

## Lo que falta para producción

- **API de Blinka.** Hoy no hay API pública: el riel arma la instrucción pero no la envía. Faltan el endpoint de pagos,
  los estados por webhook y un sandbox.
- **KYC y KYB.** Custodio no verifica identidades; depende de los beneficiarios que Blinka ya verificó.
- **SOC 2.** Custodio no tiene SOC 2 ni otra certificación. Hace falta antes de manejar pagos reales de clientes.
- **Datos bancarios.** Hoy el número de cuenta se guarda tal cual porque es demo; en producción se guarda una huella y
  el número vive en Blinka.
- **Cuentas y acceso.** Hoy cada visitante recibe un espacio con una cabecera y una API key; faltan inicio de sesión,
  roles y claves por cliente en un almacén de secretos.
- **Facturas reales.** Todo lo medido es sobre facturas sintéticas; el piloto lo mide con las de los clientes.
