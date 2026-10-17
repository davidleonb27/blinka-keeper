# Custodio

**El agente de cuentas por pagar que no se deja engañar.**
*El modelo lee, el código decide, la persona autoriza.*

Custodio revisa las facturas de una empresa y paga sólo lo que cabe en las reglas que la empresa definió. Retiene lo
que es claramente indebido (una cuenta distinta a la registrada, un cobro repetido) y le pregunta a una persona todo lo
demás. Cada decisión queda en un acta que se lee en un minuto y en un registro encadenado que no se puede alterar sin
que se note.

<!-- Captura: docs/img/demo.gif (ver docs/img/LEEME.md) -->
> *Aquí va el GIF de la demo (`docs/img/demo.gif`), pendiente de grabar sobre la versión desplegada.*

## Pruébalo en 30 segundos

1. Abre **{{DEMO_URL}}** y pulsa **«Probar con una empresa demo»**. No hay registro: recibes tu propio espacio.
2. En el panel verás una semana de facturas ya decidida: pagado, retenido y pendiente, cada una con su razón.
3. Abre cualquier fila para ver el acta con las 12 reglas. Prueba «Róbale a Custodio» e intenta que pague algo indebido.

Es dinero de mentira: no hay pasarelas ni cuentas reales. Aquí se prueba la decisión, no el movimiento de fondos.

## Por qué existe

El fraude de pagos a proveedores suele ser una factura normal con un dato cambiado: la cuenta bancaria, el número o el
monto. En Estados Unidos, el FBI recibió 24.768 denuncias de compromiso de correo empresarial (BEC) en 2025, con
pérdidas reportadas de US$ 3.046.598.558
([Informe IC3 2025](https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf)). El 74 % de las organizaciones
encuestadas por la AFP dijo haberlo sufrido ese año
([AFP, abril de 2026](https://www.financialprofessionals.org/about/learn-more/press-releases/Details/over-75-percent-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags)).
No encontramos una cifra comparable y medida para pymes de América Latina; el detalle está en
[`docs/BUSINESS.md`](docs/BUSINESS.md).

Un agente de IA que lee facturas y paga es el objetivo ideal de ese fraude: una instrucción escondida en el PDF puede
convencerlo. Por eso en Custodio el modelo sólo lee y cita; quien decide es código determinista.

## Cómo cumple el reto

| Criterio de Blinka | Cómo lo cumple Custodio |
|---|---|
| **Autonomía** | 12 reglas deterministas pagan o retienen solas lo que está claro; sólo lo ambiguo va a una persona. |
| **Seguridad** (un pago indebido descalifica) | El modelo nunca decide. Un auditor independiente recalcula cada pago por otro camino de código y, si discrepa, gana el auditor. Hay red team y un reto público. |
| **Explicabilidad** | Cada decisión trae las 12 reglas con sus cifras, un contrafactual («se habría pagado si…») y un registro con hashes verificable. |

## Métricas

Sólo se publican cifras medidas. Mientras el coordinador no las mida sobre la versión desplegada, dicen NO MEDIDO.

| Métrica | Valor | Cómo se mide |
|---|---|---|
| Autonomía | NO MEDIDO | (pagadas solas + retenidas) / total, sobre el dataset |
| Exactitud sobre el dataset etiquetado | NO MEDIDO | decisión del motor frente a `expected` |
| Pagos indebidos según el auditor | NO MEDIDO | `improper_payments`; debe ser 0 |
| Ataques probados del red team | NO MEDIDO | rondas de Claude contra las reglas |
| Intentos del reto público | NO MEDIDO | contador en vivo de «Róbale a Custodio» |
| Decisiones con acta | NO MEDIDO | actas / decisiones |
| Cadena de hashes verificable | NO MEDIDO | `GET /api/v1/ledger/verify` |

## Lo que lo hace distinto

1. **Firewall de pagos para cualquier agente.** Otro agente (de Blinka, de Claude, de un ERP) envía una intención de pago
   por API o MCP y recibe pagar, retener o escalar, con su acta.
2. **Claude contra Claude.** Un atacante con Claude Opus escribe facturas fraudulentas contra las reglas de la empresa,
   lee por qué lo bloquearon y cambia de técnica. El defensor no cambia: las reglas son código.
3. **«Róbale a Custodio».** Página pública donde cualquiera intenta que pague algo indebido. Contador en vivo de
   intentos y de pagos indebidos. Cada ataque atrapado se vuelve un caso de prueba.
4. **Reglas en español, compiladas y simuladas.** «Nada sobre 3.000 USD sin que lo apruebe Ana» se compila a la
   política, se muestra el cambio y se simula contra el historial antes de aplicarlo. Lo que no se entiende se pregunta.
5. **Onboarding de una pregunta por pantalla.** Con el nombre y el sitio web, Claude propone el perfil de la empresa y
   unas reglas iniciales; se importan los proveedores y se simula la primera semana.
6. **Prueba, no promesa.** Tests de propiedades con empresas y lotes aleatorios en cada commit, una prueba de estrés
   reproducible de 1.000 empresas (`docs/DATASET.md`) y un botón «alterar el registro» que muestra dónde se rompe la
   cadena.
7. **Aprobar en un clic.** Lo dudoso queda pendiente en el acta web, donde la persona aprueba o rechaza.

## Arquitectura

```mermaid
flowchart LR
    F[Factura PDF, imagen o texto] --> L[Lectura: el modelo cita, el código verifica]
    L --> M[Motor: 12 reglas puras]
    M -->|pagar| A[Auditor independiente]
    M -->|retener| R[Registro encadenado]
    M -->|escalar| P[Persona: acta en la web]
    A --> R
    P --> M
```

Detalle y recorrido completo de una factura en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Las decisiones de diseño
están en [`docs/DESIGN.md`](docs/DESIGN.md).

## Correrlo en local

Requisitos: Python 3.12 con [uv](https://docs.astral.sh/uv/) y, para la web, Node.js.

```bash
./scripts/check.sh                                   # compuerta única: lint, tipos, tests (api y web)
cd apps/api && uv run uvicorn main:app --reload      # API en http://127.0.0.1:8000/api/v1
curl http://127.0.0.1:8000/api/v1/health
cd apps/web && npm install && npm run dev            # web en http://localhost:3000
```

Variables de entorno (sólo por entorno, nunca en el repo): `ANTHROPIC_API_KEY` y `DATABASE_URL`. La lista completa está en `docs/DESIGN.md` §11. Los tests con modelo se omiten salvo que se corran con `CUSTODIO_LIVE_TESTS=1`.

## Firewall y MCP para otros agentes

Cada espacio tiene una API key (pantalla «Desarrolladores»). Con ella, cualquier agente pide una decisión:

```bash
curl -X POST "$CUSTODIO_URL/api/v1/firewall/intents" \
  -H "Authorization: Bearer $CUSTODIO_API_KEY" -H "Content-Type: application/json" \
  -d '{"agent": "mi-agente", "beneficiary_name": "Proveedor Uno S.A.S.", "account_number": "000123456",
       "amount": 4200, "currency": "USD", "invoice_number": "F-1001"}'
```

La respuesta trae `decision` (con `agent_verdict`: `pay`, `hold` o `escalate`, y las 12 reglas), `ledger_hash` y
`acta_url`.

Para Claude Desktop u otro cliente MCP, apunta al servidor `…/api/v1/mcp`. Herramientas: `submit_payment_intent`,
`get_decision` y `get_policy`. Las dos entradas pasan por las mismas reglas que una factura subida a mano.

## Dataset

Empresa demo y facturas con trampa etiquetadas, publicadas y reproducibles: [`docs/DATASET.md`](docs/DATASET.md).

## Equipo

**DreamMakers**: Adriano Joao Souza Reyna, Juan David Leon y Leober Ramos. Hackathon 30X, Reto Blinka.

## Licencia

[MIT](LICENSE).

## English summary

Custodio is an accounts-payable agent that cannot be tricked into paying. A model reads each invoice and must quote
the text behind every value; deterministic code (12 pure rules) decides pay, hold or escalate; a person authorizes what
is ambiguous. An independent auditor recomputes every payment through a different code path and overrides the engine if
they disagree. Every decision ships with a plain-language record and a SHA-256 hash chain that shows where it was
altered. Other agents can use Custodio as a payment firewall through an API or an MCP server, and anyone can try to
break it on the public "Róbale a Custodio" challenge. Try it: **{{DEMO_URL}}**. Figures are published only when
measured; until then they read NO MEDIDO ("not measured"). Built by team DreamMakers for the 30X hackathon, Blinka
challenge. MIT licensed.
