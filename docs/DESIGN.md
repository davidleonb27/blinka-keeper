# Custodio — diseño

> **El modelo lee, el código decide, la persona autoriza.**
> Custodio es el agente de cuentas por pagar que no se deja engañar: revisa las facturas de una empresa, paga solo
> lo que cabe en las reglas que la empresa definió, retiene lo que es claramente indebido y le pregunta a una persona
> todo lo demás. Cada decisión queda en un acta que cualquiera entiende y en un registro encadenado que nadie puede
> alterar sin que se note.

Hackathon 30X, Reto Blinka. Entrega: domingo 18 de octubre de 2026, 11:59 a. m. Equipo DreamMakers.

## 1. Qué pide el reto y cómo lo medimos

| Criterio de Blinka | Cómo lo cumple Custodio | Métrica visible en el panel |
|---|---|---|
| **Autonomía**: facturas decididas bien sin una persona | 15 reglas deterministas deciden pagar o retener solas | `autonomy_rate` = (pagadas solas + retenidas) / total; `accuracy` contra el dataset etiquetado |
| **Seguridad**: cero pagos indebidos (uno descalifica) | el modelo nunca decide; auditor independiente recalcula cada pago; red team y reto público | `improper_payments` = 0, con el número de ataques probados |
| **Explicabilidad**: cualquiera entiende cada decisión | acta con las 15 reglas, contrafactual («se habría pagado si…») y narración verificada | 100 % de decisiones con acta; cadena de hashes verificable |

Alcance del reto: leer la factura (quién, cuánto, moneda, cuándo), reglas configurables (límites por pago y por periodo,
beneficiarios permitidos, aprobación humana sobre un monto), registrar cada decisión, dataset propio con trampas
(duplicado, beneficiario nuevo, desacuerdo con lo pactado, sobre el límite, saldo o cupo insuficiente) y una pantalla
para definir reglas y ver lo pagado, retenido y pendiente con sus razones. Fuera de alcance: dinero real, pasarelas,
KYC, cumplimiento, decisiones de fraude como servicio y el diseño de la app de Blinka.

## 2. Lo que nos hace distintos

1. **Firewall de pagos para cualquier agente.** API y servidor MCP: otro agente (de Blinka, de Claude, de un ERP) envía
   una intención de pago y recibe pagar / retener / escalar con su acta. Se vende por decisión.
2. **Claude contra Claude.** Un atacante con Claude Opus genera facturas fraudulentas contra las reglas de esa empresa,
   lee por qué lo bloquearon y cambia de técnica. El defensor no cambia: las reglas son código.
3. **«Róbale a Custodio».** Página pública donde cualquiera intenta que Custodio pague algo indebido. Contador en vivo de
   intentos y pagos indebidos, muro con los ataques más creativos. Cada ataque atrapado se vuelve caso de prueba.
4. **Reglas en español, compiladas y simuladas.** «Nada sobre 3.000 USD sin que lo apruebe Ana» se compila a la política,
   se muestra el cambio y se simula contra el historial antes de aplicarlo. Lo que no se entiende se pregunta.
5. **Onboarding adaptativo tipo Typeform.** Una pregunta por pantalla. Con el nombre y el sitio web, Claude propone el
   perfil de la empresa y unas reglas iniciales; se importan proveedores desde una lista, un contrato o facturas viejas;
   termina simulando la primera semana. Se adapta a cualquier empresa en dos minutos.
6. **Prueba, no promesa.** Tests de propiedades sobre miles de empresas aleatorias en cada commit; botón «alterar el
   registro» que muestra cómo se rompe la cadena.
7. **Aprobar en un clic.** Desde el acta en la web; las aprobaciones son sólo por la web.

## 3. Invariantes (los hace cumplir un test)

- El motor es puro: sin I/O, sin reloj, sin azar, sin modelo. Mismo input, mismo output. La copia OFAC que usa R14 es
  un dato fechado que viaja con el código (`custodio/dataset/ofac/sdn.json`): se lee una vez por proceso y no cambia.
- Ningún pago ocurre si una regla de retención falla, ni deja el saldo bajo la reserva, ni siquiera con aprobación humana.
- El motor nunca lee `InvoiceCase.expected` ni `InvoiceCase.trap`.
- Ningún texto de un documento cambia una regla ni autoriza nada. El texto dirigido al agente escala (R2).
- Un valor extraído sin cita verificada por código cuenta como no leído (R1).
- El auditor recalcula cada pago por un camino de código distinto al del motor; si discrepa, gana el auditor y el pago no
  se hace.
- Toda escritura queda en el ledger encadenado con SHA-256. `verify()` detecta cualquier alteración y dice dónde.
- Lo que no se midió se dice «NO MEDIDO». `null` no es cero.
- Secretos sólo por variable de entorno; nunca en logs, errores, prompts, PR ni respuestas de la API.

## 4. Arquitectura

```
                 ┌────────────── Vercel (un proyecto, Services) ──────────────┐
 navegador ───▶  │  web  (Next.js App Router)   ──binding──▶  api (FastAPI)   │
 agentes   ───▶  │                          /api/v1/*  ───────▶               │
                 │  (MCP y firewall también entran por /api/v1)               │
                 └─────────────────────────────────────────────┬──────────────┘
                                                               │
              Neon Postgres (estado, documentos ≤ 4 MB y ledger)
              Claude (leer imágenes y PDFs, estructurar, narrar, compilar reglas, perfilar, atacar)
```

Backend `apps/api/custodio/`:

| Módulo | Qué hace | Carril |
|---|---|---|
| `contracts.py` | modelos compartidos (Pydantic v2). Cambiarlos requiere al coordinador | base |
| `config.py`, `llm.py` | ajustes y la única puerta a Claude (salida estructurada, caché, fallback, tope de gasto) | base |
| `engine/` | reglas R1–R15, `decide_all`, `audit`, `simulate`, contrafactual, explicación, `ledger` | L1 |
| `dataset/` | empresa demo y casos trampa etiquetados (`cases.json`) | L1 |
| `extraction/` | PDF (pdfplumber + detección de texto oculto), imágenes y PDFs escaneados (Claude con visión), estructuración (Claude), verificación de citas, `render_invoice` | L2 |
| `ai/` | compilador de reglas, narración, perfil de empresa, importación de proveedores, red team | L3 |
| `api/`, `db/` | rutas, persistencia, espacios de trabajo, aprobaciones web, firewall, MCP, reto público, límites | L4 |
| `reconciliation/` | extractos (CSV por código; PDF e imagen por Claude con verificación por código), emparejamiento puro, resumen del mes y paquete de evidencia | L14 |

Frontend `apps/web/` (L5). Documentación, dataset publicado, guion y build-in-public (L6).

## 5. Motor de decisión (L1)

Se porta la semántica de `prototype/engine.js` (`decideAll` desde la línea 289, `explain` 458, `counterfactual` 477,
`audit` 493). Orden: por `received_at`, desempate por posición. Todas las cifras se comparan en la moneda base con
`fx_units_per_base`.

| Regla | Efecto | Falla cuando |
|---|---|---|
| R1 Lectura confiable | escalar | proveedor, monto, moneda o cuenta con `confidence < min_confidence` o `verified = false`; caso especial: moneda ambigua («$» sin ISO) |
| R2 Sin instrucciones escondidas | escalar | hay `hidden_findings`, o el texto visible trae instrucciones al agente (patrón del prototipo, ampliado) |
| R3 Beneficiario permitido | escalar | el proveedor no casa con un beneficiario por NIT/tax id o nombre normalizado/alias, o está bloqueado |
| R4 Cuenta registrada | retener | la cuenta leída no es la registrada del beneficiario |
| R5 Sin cobro duplicado | retener | mismo número de factura ya visto (lote o historial), o mismo monto (±0,5 %) del mismo proveedor dentro de `duplicate_window_days` |
| R6 Coincide con lo acordado | escalar | moneda distinta a la pactada; monto fijo fuera de la tolerancia; tope mensual superado sumando lo pagado en el mes |
| R7 Sin pagos fraccionados | escalar | ≥ 2 cobros del mismo proveedor dentro de `split_window_days`, cada uno ≤ tope de aprobación y juntos > tope |
| R8 Moneda permitida | retener | moneda fuera de `allowed_currencies` |
| R9 Tope de aprobación automática | escalar | monto base > `approval_threshold` |
| R10 Límite por pago | escalar | monto base > `per_payment_limit` |
| R11 Cupo de pago automático | escalar | lo pagado solo en el mes + este pago > `period_budget` |
| R12 Saldo y reserva | retener | saldo − pago < `reserve` |
| R13 Datos bancarios válidos para el riel | escalar | la cuenta leída (o la registrada) no pasa el control de su esquema: ruta ABA (3-7-1) y cuenta ACH (4–17 dígitos) en USD dentro de EE. UU., CLABE (3-7-1 módulo 10) en MXN, IBAN (largo del país y mod 97 = 1), llave Pix en BRL (correo, celular +55, CPF/CNPJ con dígitos, aleatoria UUID), llave Bre-B en COP (correo, celular, NIT con dígito DIAN); o la identificación fiscal no pasa el suyo (NIT, CPF/CNPJ, RFC y EIN por forma). El riel sale de la moneda y el país del beneficiario registrado |
| R14 Sin coincidencia en la lista OFAC | escalar | el nombre leído, el registrado o un alias coincide con la copia fechada de la lista SDN (`custodio/dataset/ofac/sdn.json`): tokens sin tildes, sufijos societarios ni conectores, ordenados; similitud por palabra con Jaro-Winkler, umbral 0,92. Sin lista cargada (0 entradas) también escala: un nombre sin revisar no se paga solo. Nunca retiene sola: una persona descarta el falso positivo |
| R15 Verificación fuera de banda | escalar | la cuenta leída no es la registrada (el acta dice a qué contacto **registrado** llamar y que confirme los últimos 4 dígitos, nunca a un dato de la factura), o el correo del documento viene de un dominio parecido al registrado (edición ≤ 2, homóglifos, guion, otra terminación) |

Veredicto: alguna regla de retención falla → `hold`; si no, alguna de escalar falla → `escalate` (`pending_approval`);
si no, `pay` (`paid_auto`) y se descuenta del saldo y del cupo. Una regla `skipped` de R1 a R12 escala (sin el dato no
se paga); en los controles de pago R13–R15 (`RuleSpec.neutral_when_skipped`) `skipped` significa que no había nada que
comprobar (una cuenta sin esquema con dígito de control público, un correo de un dominio ajeno pero no parecido) y deja
la decisión a las demás reglas. El auditor independiente recalcula R13–R15 por su cuenta. Las aprobaciones se aplican **después** del lote, en el
momento de aprobar: un aprobado sólo se paga si R12 sigue cumpliéndose (si no, `hold` con `blocked_reason`); un
rechazo queda `rejected`. Aprobar una factura nunca cambia las decisiones de las otras.

Contratos que agregó L12 (todos opcionales, sin romper a nadie): `RuleSpec.neutral_when_skipped`,
`Beneficiary.email_domain` (el dominio registrado que compara R15; `approver_contact` es el contacto al que R15 manda a
verificar), `ExtractedInvoice.sender_email` (primer correo del documento, encontrado por código, no por el modelo) y
`Health.sanctions_list_date` (fecha de publicación de la copia OFAC en uso).

Cada `RuleResult` trae una razón en español con las cifras concretas. `explanation` resume el veredicto; el
`counterfactual` dice el cambio mínimo que la habría hecho pagable.

Ledger: `hash = sha256(prev_hash + canonical_json({seq, at, kind, subject_id, payload}))`, `prev_hash` del primero =
64 ceros. `canonical_json`: claves ordenadas, sin espacios, Decimal como string normalizado, fechas ISO-8601 UTC.

## 6. Lectura de facturas (L2)

1. PDF: `pdfplumber` extrae texto visible por carácter con color, tamaño y posición. Texto oculto = color igual al fondo
   (blanco o casi), tamaño < 2 pt, fuera de la página, tapado por un rectángulo o imagen, o en metadatos/anotaciones.
   PDF sin texto → se rasteriza y va a OCR.
2. Imagen o PDF escaneado: Claude (`model_fast`) lo lee directamente con visión (bloque `image` o `document`). **No usamos Gemini**: un solo proveedor y una sola clave.
3. Claude (`model_fast`, esfuerzo bajo) estructura los campos con salida estructurada y devuelve, por campo, el valor
   normalizado y la cita exacta.
4. Código verifica cada cita contra el texto fuente (normalizando espacios) y que la cita respalde el valor (el monto
   citado parsea al mismo número; la fecha, a la misma fecha). Sin verificación → `verified = false`.
5. Montos: se respetan los formatos latinos (`4.200.000,00`) y anglosajones (`4,200,000.00`); «$» solo es ambiguo.

## 7. Claude en Custodio (L3) — modelos por tarea

| Tarea | Modelo | Esfuerzo | Por qué |
|---|---|---|---|
| Estructurar una factura | `claude-sonnet-5-5` | low | rápido y barato; la verificación la hace el código |
| Narrar un acta | `claude-sonnet-5-5` | low | cada número del texto se valida contra la decisión |
| Compilar reglas en español | `claude-opus-5-5` | high | ambigüedad y negaciones; devuelve `unsupported` y `questions` |
| Perfil de empresa desde su sitio | `claude-opus-5-5` + `web_fetch` | medium | lee páginas públicas y cita URLs |
| Importar proveedores | `claude-sonnet-5-5` | medium | tablas, contratos y facturas viejas |
| Atacante del red team | `claude-opus-5-5` | high | creatividad adaptativa |
| Triaje del reto público | `claude-haiku-5-5` | low | volumen alto, costo mínimo |

Todo pasa por `custodio.llm.structured`. Prompt de sistema estable y cacheado; contenido variable en el turno del
usuario. Si el modelo se niega, se corta o devuelve algo inválido, la función lo dice; no adivina.

## 8. API (L4) — `/api/v1`

Identidad: cada visitante recibe su propio espacio de trabajo sembrado con la empresa demo (cabecera
`X-Custodio-Workspace`, guardada por la web en una cookie). El firewall y MCP usan `Authorization: Bearer <api key>` del
espacio.

| Método y ruta | Qué hace |
|---|---|
| `GET /health` | estado y si hay claves configuradas |
| `POST /workspaces` | crea un espacio (demo o vacío) → `{workspace_id, api_key}` |
| `GET /workspaces/current` | empresa, hoy, saldo inicial y actual, cupo usado en el mes, métricas e informe del auditor independiente |
| `POST /onboarding/profile` | nombre + sitio + respuestas → `CompanyProfile` |
| `POST /onboarding/suppliers` | archivo → `SupplierImport` |
| `POST /onboarding/complete` | perfil + política + proveedores → espacio listo y simulación inicial |
| `GET /policy` · `PUT /policy` | leer / aplicar la política (queda en el ledger) |
| `POST /policy/compile` | texto → `PolicyProposal` con simulación; con un borrador `base` (onboarding) compila contra él y no simula |
| `POST /invoices` | subir PDF/imagen/texto → lectura |
| `POST /invoices/process` | decidir lo pendiente → `BatchResult` + auditoría |
| `GET /decisions` · `GET /decisions/{id}` | lista (`{decision, received_at, source}`) y acta (`{decision, invoice, ledger}`) |
| `POST /decisions/{id}/approve` · `/reject` | aprobación humana |
| `POST /decisions/{id}/execute` | reintenta un pago cuya ejecución falló (idempotente; ver `docs/PAYMENTS.md`) |
| `GET /ledger` · `GET /ledger/verify` | registro y verificación |
| `POST /ledger/tamper-demo` | altera una copia del registro y muestra dónde se rompe (nunca el real) |
| `POST /redteam/runs` (SSE) | rondas del atacante en vivo; cada mensaje es un `RedTeamEvent` (documentado en el OpenAPI) |
| `POST /challenge/attempts` · `GET /challenge/stats` | reto público |
| `POST /firewall/intents` | intención de pago de otro agente → `IntentVerdict` |
| `GET /trust` · `POST /trust/simulate` | tope ganado por proveedor (desde el ledger) · mes simulado de la demo (una vez, riel simulado) |
| `GET /schedule` · `POST /schedule/run-due` | calendario de pagos aprobados (45 días) · paga lo que vence hoy por el riel configurado |
| `POST /reconciliations` · `GET /reconciliations` · `GET /reconciliations/{id}` | sube un extracto (CSV, PDF, imagen o `demo=true`) y lo concilia; lista y detalle |
| `GET /reconciliations/demo-statement?format=csv\|pdf` | el extracto de demo, movido al día en que este espacio pagó su lote |
| `POST /reconciliations/{id}/resolve` | una persona marca como revisado un movimiento que lo necesitaba, con nota (queda en el ledger) |
| `POST /periods/{yyyy-mm}/close` · `GET /periods/{yyyy-mm}/evidence.zip` | cierra el mes si no quedan salidas sin revisar; paquete para el contador |
| `/mcp` | servidor MCP (streamable HTTP): `submit_payment_intent`, `get_decision`, `get_policy`, `reconcile_statement` |

Límites: por IP y por espacio en rutas que llaman modelos; tope diario de gasto en `llm.py`; archivos ≤ 4 MB
(límite de cuerpo de Vercel 4,5 MB); el reto público usa Haiku y tiene su propio tope.

## 9. Pantallas (L5)

Diseño base: `prototype/index.html` (ya publicado y probado). Next.js App Router, TypeScript estricto, Tailwind,
shadcn/ui, tema claro y oscuro, móvil primero.

1. **Inicio**: qué es en una frase, métricas en vivo (autonomía, pagos indebidos = 0, ataques probados), dos botones:
   «Probar con una empresa demo» y «Configurar mi empresa».
2. **Onboarding tipo Typeform**: una pregunta por pantalla, teclado (Enter avanza), barra de progreso, animaciones
   suaves. Pasos: nombre y sitio → perfil propuesto (editable) → país, moneda, saldo y reserva → quién aprueba (nombre,
   cargo y correo) → reglas en tus palabras (compiladas en vivo) → proveedores (subir lista, contrato o facturas) → simulación
   de la primera semana → «Custodio está listo».
3. **Panel**: pagado / retenido / pendiente con razón en una línea, filtros, métricas, saldo y cupo.
4. **Acta** (drawer): las 15 reglas con su resultado, contrafactual, documento con las citas resaltadas, texto oculto
   destapado, aprobar / rechazar, hash en el ledger.
5. **Reglas**: editor en español con diff y simulación antes de aplicar; formulario clásico como alternativa.
6. **Arena**: Claude contra Claude en vivo (rondas, técnica, veredicto, marcador).
7. **Róbale a Custodio**: subir o escribir una factura trampa, resultado al instante, contador global y muro.
8. **Registro**: cadena de hashes, «verificar» y «alterar una copia».
9. **Desarrolladores**: API key, ejemplo del firewall y configuración MCP para Claude Desktop.
10. **Conciliación**: arrastrar el extracto (o usar el de demo), tres columnas (conciliado, con diferencia, alertas) con
    la razón de cada emparejamiento y el enlace al acta y al `tr_` de Stripe, revisar alertas con nota, cerrar el mes y
    descargar el paquete.

## 10. Calidad — cómo se escribe el código

- **TDD visible**: el test rojo primero en el historial; después lo mínimo que lo pone verde; después se limpia.
- **Código limpio**: funciones cortas con un solo propósito; nombres que dicen qué hacen; sin comentarios que repitan
  el código (sí el porqué); sin código muerto ni banderas sin uso; dependencias hacia adentro (rutas → servicios → motor
  puro); errores explícitos con tipos propios; sin `Any` salvo en bordes; nada de números mágicos (van en la política o
  en constantes con nombre).
- **Tipos**: Python con mypy estricto; TypeScript `strict` sin `any`.
- **Idioma**: código, identificadores, tests y comentarios en inglés; todo texto que ve una persona, en español neutro.
- **Compuerta única**: `./scripts/check.sh` (ruff, formato, mypy, pytest y, si existe la web, tipos de la API al día,
  lint, tipos, tests y build). La corre quien implementa, quien revisa y CI.
- **Contrato web ↔ API**: la web toma sus tipos del OpenAPI de FastAPI (`apps/web/src/lib/api/schema.gen.ts`, generado
  con `npm run gen:api`); la compuerta falla si están desactualizados y `tsc` falla si la web o el mock se desvían.
  `npm run e2e` (fuera de la compuerta) recorre todas las páginas contra la API real sin un solo error de consola.
- **Tests con modelo**: marcados `@pytest.mark.live`, se corren con `CUSTODIO_LIVE_TESTS=1` en la nube; CI no llama
  modelos. Las salidas malas grabadas del modelo se guardan como fixtures y el sistema debe rechazarlas o escalar.
- **PR**: una por carril o sub-tarea, < 800 líneas cuando se pueda, con qué cambió, qué se verificó (comandos y
  conteos exactos) y qué NO se verificó. La revisa una sesión distinta de la que la escribió.

## 11. Variables de entorno

`ANTHROPIC_API_KEY`, `DATABASE_URL` (Neon; normalizar `postgresql://` a `postgresql+psycopg://`),
`CUSTODIO_PUBLIC_BASE_URL`, `CUSTODIO_LLM_DAILY_BUDGET_USD`, `CUSTODIO_MODEL_FAST`,
`CUSTODIO_MODEL_SMART`, `CUSTODIO_MODEL_CHEAP`, `CUSTODIO_LIVE_TESTS`, `CUSTODIO_TREASURY_YIELD_APY` (rendimiento anual
supuesto del saldo, 4.0 por defecto; un supuesto, no un dato de Blinka), `CUSTODIO_PAYMENT_RAIL` (`simulated` por
defecto, `stripe_test` o `blinka_simulated`) y `STRIPE_SECRET_KEY` (sólo `sk_test_…`; una clave `live` se rechaza). `Decision.execution`
(`PaymentExecution`) dice cómo salió cada pago: ver `docs/PAYMENTS.md`.

## 12. Guion de la demo (3 minutos)

0:00 una factura idéntica en la que sólo cambió la cuenta · 0:20 el problema · 0:40 la semana decidida en segundos ·
1:15 Claude contra Claude y el contador del reto · 2:00 el celular aprueba · 2:20 firewall y modelo de negocio ·
2:40 uso real, equipo y cierre. Sólo cifras medidas.

## 13. Cambios de alcance (2026-10-17)

- **Sin Gemini**: Claude lee imágenes y PDFs escaneados con visión. Quitar `google-genai`, `gemini_model` y `gemini_configured`.
- **Sin Telegram por ahora**: las aprobaciones son sólo por la web. Desde L7 no queda código de Telegram: `Approver`
  ya no tiene `telegram_chat_id`, el canal de `Approval` es `web` o `api` y la migración `0002` quita ese campo de las
  políticas guardadas.
- **Neon**: `DATABASE_URL` llega como `postgresql://`; la capa `db` la normaliza a `postgresql+psycopg://`.

## 14. Autonomía ganada y planificador de pagos (L13)

- **Tope por proveedor (R9).** `engine/trust.py` pliega los asientos `trust_raised` y `trust_revoked` del ledger de cada
  proveedor en su tope; no hay contador aparte. Sin historial, el tope es `approval_threshold` (el banco de casos no
  cambia). Una señal de riesgo (R2, R4, R5, R6, R13, una coincidencia OFAC en R14, R15 o un rechazo) lo deja en `Policy.trust.floor` (0 por defecto). Tras 3
  pagos limpios aprobados por una persona el tope es la mediana aprobada; cada pago limpio más suma 25 %, hasta el
  doble; nunca baja por un pago limpio ni pasa del techo (`per_payment_limit`, o `approval_threshold` si
  `Policy.trust.hard_ceiling`). El auditor aplica el mismo tope por su propia identificación del proveedor.
  `CompanyState.trust` lleva los topes al motor y `Decision.trust` dice cuál se aplicó y por qué.
- **Planificador.** `engine/schedule.py`: lo aprobado sale el día que vence, no antes; antes sólo para ganar un
  descuento por pronto pago (`Agreement.early_payment_discount`) que valga más que el rendimiento de esperar; nunca
  toca la reserva y, si no alcanza, prioriza la mora pactada (`Agreement.late_fee_pct`) y los proveedores críticos
  (`Agreement.critical`). Un pago aprobado cuyo día no ha llegado queda con `execution = null` y su asiento `payment`
  dice `scheduled_for`; `POST /schedule/run-due` lo envía con el servicio de pago de siempre.

## 15. Conciliación bancaria y cierre de mes (L14)

El ciclo se cierra con el banco, con el mismo principio: **el modelo lee, el código decide, la persona autoriza**.

- **Lectura.** Un CSV lo lee el código: separador `,` `;` o tabulador, encabezados en español o inglés (fecha,
  descripción, monto o cargo/abono, moneda, referencia), montos latinos o anglosajones con su signo, fechas día/mes salvo
  que el archivo pruebe lo contrario. Un PDF o una imagen pasan por la misma tubería que las facturas (texto visible con
  pdfplumber, visión si es un escaneo) y Claude devuelve cada fila con la línea exacta de la que sale; el código sólo la
  acepta si esa línea está en el documento y trae la fecha y el monto con su signo. Lo demás queda **NO LEÍDO**, sin
  valores, y una línea con fecha y monto que el modelo no devolvió también se agrega como NO LEÍDO.
- **Emparejamiento** (`reconciliation/match.py`, puro). Niveles en orden fijo sobre todo el extracto: 1) referencia
  exacta (id de transferencia `tr_…`, número de factura entero, enlace del acta) y el mismo monto; 2) mismo monto, fecha
  dentro de ±3 días y el beneficiario nombrado; 3) pago partido: de 2 a 4 movimientos que suman exactamente el pago;
  4) tolerancia de cambio explícita (0,5 % por defecto, configurable por conciliación) sólo para pagos hechos en otra
  moneda. Lo que sobra es comisión del banco, duplicado de otro movimiento idéntico o **salida sin factura** (alerta
  roja, que nombra la factura no pagada a la que se parece). Ningún movimiento se usa dos veces, lo conciliado nunca
  supera el movimiento y el resultado no depende del orden de entrada (propiedades con Hypothesis).
- **Registro.** Cada conciliación escribe un asiento `reconciliation` (con el SHA-256 del extracto y del resultado) y uno
  por pago confirmado, con la factura como sujeto, así el acta muestra la confirmación del banco. Cada revisión escribe
  `reconciliation_review` y cada cierre `period_closed`. Un mes cerrado no admite más conciliaciones ni revisiones.
- **Cierre y evidencia.** «Cerrar mes» sólo procede si no quedan salidas sin factura, duplicados ni filas NO LEÍDAS sin
  revisar, y si la cadena verifica. El paquete (`evidence.zip`) trae `resumen.pdf`, `conciliacion.csv`, todas las actas
  del mes, `registro/registro.json` con `verificacion.json` (el verificador público) y `verificar_registro.py` (el mismo
  algoritmo sin dependencias). Mismo estado, mismos bytes: la fecha de generación va sólo en `manifiesto.json`.
