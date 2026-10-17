# Revisión de L11 · Listo para Blinka (PR #11)

Rama: `lane/L11-blinka`. Revisión hecha por una sesión distinta de la que escribió el código, siguiendo
`docs/lanes/REVIEW.md`. En el repositorio no hay un brief `docs/lanes/L11-*.md`: revisé contra la descripción del PR,
`docs/lanes/reports/L11.md`, `docs/DESIGN.md` (§3, §10, §11 y §13) y `docs/PAYMENTS.md`.

## Veredicto: LISTO PARA MERGE

Con el rebase y los arreglos de abajo, ya empujados en esta rama. El hallazgo bloqueante (después de L8 la rama rompía la
compuerta) quedó corregido.

## Rebase

La rama salió de `d6b64a9` (merge de L9). Desde entonces `main` recibió L8 (21 commits, `d6fbeab`): la web toma sus
tipos del OpenAPI (`apps/web/src/lib/api/schema.gen.ts`) y `./scripts/check.sh` corre `npm run check:api`. Rebasé los
7 commits del carril sobre `origin/main` (`git rebase origin/main`, sin conflictos); conservan autor y mensaje, así que
cambian de hash (`6af6066` → `58e8ec4`, …, `a564d10` → `f3d0477`) y el push de la rama es forzado sólo por ese rebase.

## Compuerta

- **Inicial** (`a564d10`, tal como la entregó el carril, sobre `d6b64a9`): `./scripts/check.sh` → `== gate passed`.
  ruff `All checks passed!`, formato `161 files already formatted`, mypy `Success: no issues found in 92 source files`,
  pytest `797 passed, 22 skipped`; web: eslint sin avisos, vitest `Test Files 15 passed (15)`, `Tests 75 passed (75)`,
  `next build` «Compiled successfully».
- **Tras el rebase, antes de arreglar** (`f3d0477`): `npm run check:api` → «src/lib/api/schema.gen.ts no coincide con la
  API» y `tsc --noEmit` → `presentation.ts(28,14): error TS2741: Property 'blinka_simulated' is missing`. La compuerta
  fallaba.
- **Final** (`985263b` + este informe): `./scripts/check.sh` → `== gate passed`. ruff `All checks passed!`, formato
  `162 files already formatted`, mypy `Success: no issues found in 92 source files`, pytest `804 passed, 22 skipped`;
  web: `schema.gen.ts coincide con la API.`, eslint sin avisos, typecheck correcto, vitest `Test Files 17 passed (17)`,
  `Tests 89 passed (89)`, `next build` correcto. (Los conteos crecen respecto de la inicial por los tests de L8 que trae
  `main` y por 1 test nuevo de la API y 1 de la web de esta revisión.)
- **Postgres 16 local** (`CUSTODIO_TEST_POSTGRES_URL=postgresql://…/postgres uv run pytest -q tests/api`) →
  `122 passed, 2 skipped`. Migración en Postgres: `alembic upgrade head` crea `payment_executions.instruction` de tipo
  `json`, `downgrade 0003` la quita y un nuevo `upgrade head` la vuelve a crear.
- **Live** (`CUSTODIO_LIVE_TESTS=1 uv run pytest -q -m live`) → `19 failed, 3 skipped, 804 deselected`. Los 19 fallan
  con `TypeError: Could not resolve authentication method` porque en este entorno no hay `ANTHROPIC_API_KEY`; los 3
  saltados piden `STRIPE_SECRET_KEY`. Ninguno es de este carril. **NO MEDIDO.**

## Hallazgos

### 1. Bloqueante, arreglado — después de L8 la web no compilaba con el riel nuevo

- `apps/api/custodio/contracts.py` agrega `blinka_simulated` a `PaymentExecution.rail` y el campo `instruction`, pero
  `apps/web/src/lib/api/schema.gen.ts` (de L8) no los tenía, y `RAIL_LABEL: Record<PaymentRailName, string>`
  (`apps/web/src/lib/presentation.ts:28`) dejaba de cubrir todos los rieles. Al mergear, `check:api` y `tsc` fallaban.
- Arreglo `eefd449`: `npm run gen:api` (sólo cambian `payment_rail`, `rail` y el esquema `PaymentInstruction`) y la
  etiqueta «Blinka · simulado».

### 2. Texto de producto, arreglado — el acta de un pago por Blinka mostraba el monto en otra moneda y no la instrucción

- `apps/web/src/components/acta/payment-execution.tsx`: el bloque mostraba siempre `amount_base` como «USD» y, para
  `simulated`, «Quedó registrado sin riel real». Con `blinka_simulated` la moneda base no tiene que ser USD (el riel no
  exige base USD), así que un espacio en COP mostraba los pesos con la etiqueta USD; y la instrucción, que es el
  entregable del carril, no se veía en ninguna pantalla.
- Test rojo `fac4091` (`apps/web/src/components/acta/acta.test.tsx:127`): falló porque el bloque no traía
  «Blinka · simulado»/«Bre-B»/COP. Arreglo `66d75bb`: con instrucción, el encabezado usa su monto y moneda
  (`payment-execution.tsx:71`) y `InstructionSummary` (`payment-execution.tsx:20`) dice red, banco y los últimos 4
  dígitos de la cuenta (nunca el número completo en pantalla) y que no se envió ni se movió dinero. Etiquetas de red en
  `NETWORK_LABEL` (`apps/web/src/lib/presentation.ts:34`); tipos `PaymentInstruction` y `PaymentNetwork` en
  `apps/web/src/lib/api/contracts.ts`, derivados del esquema generado.

### 3. Seguridad (tasa), arreglado — un pago que Blinka rechaza se podía reintentar sin tope

- `apps/api/custodio/services/payment_service.py:81` (`_refusal`) devolvía `None` de entrada para los rieles de
  `MOVES_NO_MONEY`, así que tampoco tenían el tope de 5 intentos de L9. Con el riel simulado no importaba (nunca
  falla), pero `BlinkaRail` sí falla de forma determinista (moneda que Blinka no paga, beneficiario borrado): cada clic
  en «Reintentar pago» (`POST /decisions/{id}/execute`, sin límite de tasa) escribía otra ejecución y otro asiento en el
  registro, sin fin.
- Test rojo `5286644` (`apps/api/tests/api/test_payments_blinka.py:88`): falló con el tercer intento devolviendo otra
  vez «Blinka no paga en EUR…» en lugar de «máximo de 2 intentos».
- Arreglo `d633841` (`payment_service.py:90-95`): el tope de intentos vale para todos los rieles; los topes de
  transferencias y la base USD siguen sólo para los que mueven dinero. El riel simulado no cambia (un único intento).
  Documentado en `740b181` (`docs/PAYMENTS.md:130-134`).

### 4. Código limpio, arreglado — el «15 s» del mensaje repetía la constante

- `apps/api/custodio/payments/stripe_rail.py:52`: `FUNDS_NOT_AVAILABLE` escribía «15 s» a mano junto a
  `MAX_FUNDS_WAIT_SECONDS = 15.0`. Arreglo `985263b`: el mensaje sale de la constante (el texto no cambia; el test que
  busca «15 s» sigue pasando).

### Observaciones sin cambios

- **TDD**: en el historial los tres rojos van antes de su verde. Los comprobé en worktrees de los commits originales:
  `6af6066` → `14 failed` en `tests/payments`; `6cf78f7` → `3 errors` de colección; `8d9c71c` → `11 failed` en
  `tests/delivery`. El rojo de la espera falla por el `sleep` que el riel aún no aceptaba (`TypeError`), no por la
  conducta; el verde sí prueba la conducta (esperas `[0.5, 1.0]`, tope de 15 s, una sola transferencia).
- **Invariantes (§3)**: el riel sólo recibe decisiones pagadas que el auditor no vetó (sin cambios en
  `invoice_service`); `BlinkaRail` no decide nada: la red sale de moneda, monto y país, y los datos bancarios del
  beneficiario **registrado** (`payment_service._registered`), nunca de la factura, que R4 ya retiene si difiere. El
  motor y el auditor no cambian. Ningún texto del documento llega a la instrucción salvo lo que ya validó el motor.
- **Secretos**: `blinka_simulated` no usa clave; el comentario de la llamada real pide la clave por variable de
  entorno. La espera de Stripe no loguea montos ni claves.
- **Datos bancarios**: la instrucción guarda el número de cuenta completo en `payment_executions.instruction` y la API
  lo devuelve al dueño del espacio (como ya hace `GET /policy`). El narrador recibe el acta completa, pero el número ya
  estaba en el motivo de R4 de cada pago; no es una exposición nueva. `BLINKA.md` dice que en producción va una huella.
- **Contratos y propiedad de archivos**: `contracts.py`, `db/models.py`, la migración `0004`, `payment_service.py` y
  `DESIGN.md` §11 están fuera del carril. El informe del carril dice que la tarea autorizaba el campo opcional; no hay
  brief en el repo para confirmarlo. El cambio es aditivo (`instruction` opcional, actas viejas validan) y lo acepto.
  Mis cambios en `apps/web` también son fuera del carril, pero eran necesarios para que la compuerta pase tras L8.
- **§13**: los documentos nuevos no nombran Gemini ni Telegram.
- **Autoría**: los 14 commits de la rama (7 del carril, 7 de esta revisión) están a nombre de Juan David Leon, sin
  trailers ni menciones a IA.
- `docs/lanes/reports/L11.md` (cuerpo del PR del carril) dice en «Pendiente» que la web no conoce `blinka_simulated`
  ni muestra la instrucción: los hallazgos 1 y 2 lo resuelven. No reescribí ese informe.

## Qué NO pude verificar

- **La espera de fondos contra Stripe real: NO MEDIDO.** No hay `STRIPE_SECRET_KEY`; no sé cuánto tarda Stripe en
  liberar una recarga ni si 15 s alcanza para las 7 de 17 transferencias que fallaron en producción.
- **Duración de la función en Vercel con la espera: NO MEDIDO.** Hasta 15 s de espera más las llamadas a Stripe por
  petición; no revisé el límite del plan desplegado.
- **Tests con modelo: NO MEDIDO** (sin `ANTHROPIC_API_KEY`; ver la sección Compuerta). Este carril no cambia nada que
  llame al modelo.
- **La migración `0004` en Neon**: sí en Postgres 16 local, no en Neon.
- **La web con `blinka_simulated` en un navegador**: cubierta con vitest y `tsc`; no corrí `npm run e2e` ni la vi con
  el riel activado.
- El guion de 3:00 de `docs/PITCH.md` no se cronometró en voz alta.
