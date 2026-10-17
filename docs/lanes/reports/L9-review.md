# Revisión de L9 · Riel de pago con Stripe en modo prueba (PR #9)

Rama: `lane/L9-stripe-rail`, sobre `origin/main` actual (sin rebase necesario). Revisión hecha por una sesión distinta de
la que escribió el código, siguiendo `docs/lanes/REVIEW.md`.

## Veredicto: LISTO PARA MERGE

Con los tres arreglos de abajo, ya empujados en esta rama. El único hallazgo bloqueante (una intención del firewall
aprobada en el panel salía por el riel) quedó corregido con su test rojo antes que el verde.

## Compuerta

- **Inicial** (`d0a3d1d`, tal como la entregó el carril): `./scripts/check.sh` → `== gate passed`. ruff
  `All checks passed!`, formato `157 files already formatted`, mypy `Success: no issues found in 91 source files`,
  pytest `757 passed, 22 skipped`; web: eslint sin avisos, typecheck correcto, vitest `Test Files 15 passed (15)`,
  `Tests 75 passed (75)`, `next build` correcto.
- **Final** (`6229111` + este informe): `./scripts/check.sh` → `== gate passed`. ruff `All checks passed!`, formato
  `157 files already formatted`, mypy `Success: no issues found in 91 source files`, pytest `759 passed, 22 skipped`
  (+2 tests nuevos de la API); web: eslint sin avisos, typecheck correcto, vitest `Test Files 15 passed (15)`,
  `Tests 75 passed (75)` (4 tests del acta reescritos, no agregados), `next build` correcto.
- **Postgres 16 local** (`CUSTODIO_TEST_POSTGRES_URL=postgresql://…/postgres uv run pytest -q tests/api`, con los
  arreglos) → `111 passed, 2 skipped`: incluye la migración `0003` y el `ON CONFLICT` de `stripe_accounts`.
- **Live**: `CUSTODIO_LIVE_TESTS=1 uv run pytest -m live tests/payments` → `1 skipped, 16 deselected`
  («needs a Stripe test-mode secret key»).

## Hallazgos

### 1. Bloqueante, arreglado — una intención del firewall aprobada en el panel la pagaba Custodio

- `apps/api/custodio/services/approval_service.py:45` llama a `invoice_service.decide(..., execute_payments=True)` para
  cualquier factura del espacio, y una intención del firewall que escala (p. ej. texto dirigido al agente, R2) queda
  `pending_approval` en el mismo espacio de visitante. Al aprobarla desde el acta, el riel recibía la orden.
- Contradice lo que el propio carril declara (`docs/PAYMENTS.md`, «Firewall y MCP: no… ese agente paga con su riel»;
  `/desarrolladores`: «El firewall responde; el pago lo hace el agente que pregunta») y, en la práctica, paga dos veces:
  el agente que preguntó consulta `get_decision`, ve `paid_human` y paga con su riel.
- Test rojo `0378241` (`apps/api/tests/api/test_payments_surfaces.py:90`): falló con
  `assert {'rail': 'simulated', 'status': 'simulated', …} is None`.
- Arreglo `09180c1` (`apps/api/custodio/services/invoice_service.py:118-130`): `decide` no pasa el pagador a las
  facturas cuyo origen es `InvoiceSource.INTENT`, aunque se aprueben. `retry` ya devolvía 409 sin ejecución previa, así
  que tampoco se pueden «reintentar». Doc en `e204c85` (`docs/PAYMENTS.md`, tabla y guardias).

### 2. Seguridad (tasa), arreglado — «Reintentar pago» sin tope llamaba a Stripe en cada clic

- `apps/api/custodio/api/routes/decisions.py:60` no tiene límite de tasa, y los topes de
  `payment_service._cap_reached` cuentan sólo ejecuciones `executed`. Un pago que Stripe rechaza de forma definitiva
  (p. ej. `transfers_not_allowed`) podía reintentarse sin fin: cada clic hacía hasta tres llamadas a Stripe sobre la
  cuenta de prueba compartida por todo el despliegue (y una `RateLimitError` ahí afecta a todos los visitantes).
- Test rojo `dc43029` (`apps/api/tests/api/test_payments_stripe.py:220` y el test de valores por defecto).
- Arreglo `4169d48`: `RateLimits.payment_attempts_per_invoice = 5` (`apps/api/custodio/services/context.py`) y
  `_refusal` (`apps/api/custodio/services/payment_service.py:81-88`) devuelve un recibo `failed` («Este pago ya usó el
  máximo de 5 intentos. No se transfirió dinero.») sin llamar al riel. El riel simulado no se ve afectado. Documentado
  en `docs/PAYMENTS.md` (Topes).

### 3. Texto de producto, arreglado — el acta decía «Pago ejecutado» y «enviado» cuando no salió nada

- `apps/web/src/components/acta/payment-execution.tsx:62,68`: el título del bloque era «Pago ejecutado» y la línea decía
  «enviado 1.200,00 USD» también para un pago `failed` («No salió: …») o `simulated` («no se movió dinero»). En un
  producto cuyo valor es no engañar, el acta no puede decir «enviado» de un pago que falló.
- Test rojo `acfbacd` (`apps/web/src/components/acta/acta.test.tsx`), arreglo `6229111`: título «Ejecución del pago» y
  «enviado» sólo si el estado es `executed` («monto» en los demás casos). `docs/lanes/reports/L9.md:48` todavía nombra
  el bloque «Pago ejecutado»: es el cuerpo del PR del carril y no lo reescribí; el nombre vigente es el de aquí.

### Revisado sin cambios

- **Invariantes (§3)**: el riel sólo recibe decisiones `paid_*` que el auditor no vetó
  (`invoice_service._record`, `decision.status in records.PAID and not audit_blocked`); los vetos pasan antes a `hold`
  (`_apply_stops`). El motor no cambia; el riel no decide. Rechazo humano nunca llega a Stripe (test). Los asientos
  `payment` siguen en el ledger encadenado y `assert_ledger_valid` pasa tras un reintento.
- **Idempotencia**: llave `workspace:factura` en el primer intento, `:intento-N` en reintentos, `transfer_group` por
  factura y búsqueda previa (`apps/api/custodio/payments/stripe_rail.py:91`) cubren la respuesta perdida y la reversión
  de la base de datos; restricción única `(workspace_id, invoice_id)`. Correcto.
- **Secretos**: `STRIPE_SECRET_KEY` sólo por entorno; claves `sk_live_`/`rk_live_` rechazadas sin loguearlas; los
  mensajes de error se arman sólo con tipo y código saneado (`_safe_code`). No encontré la clave en logs ni respuestas.
- **Superficies**: reto, red team y firewall no ejecutan (tests con facturas legítimas pagadas en papel); sandbox no es
  espacio de visitante (segunda guardia).
- **TDD**: en el historial del carril los tests rojos (`fc7437a`, `9725fed`, `d8a944b`) van antes que su verde;
  comprobé `fc7437a` y `9725fed` en un worktree: fallan (errores de colección por módulos aún inexistentes).
- **Autoría**: los 10 commits del carril y los 8 de esta revisión están a nombre de Juan David Leon, sin trailers ni
  menciones a IA.

### Observaciones no bloqueantes (no las cambié)

- `apps/web/src/lib/presentation.ts:33`: `RAIL_PITCH` dice «Hoy: Stripe en modo prueba» en la portada aunque el
  despliegue use el riel simulado (el valor por defecto mientras no se configure Vercel). La insignia del panel y
  `/desarrolladores` sí muestran el riel real. Sugiero configurar `CUSTODIO_PAYMENT_RAIL=stripe_test` antes de la demo
  o suavizar la frase.
- `apps/api/custodio/services/context.py:71` lee `STRIPE_SECRET_KEY` con `os.environ` en vez de `Settings`; funciona y
  mantiene el secreto fuera del objeto de configuración, pero es distinto de cómo se lee el resto.
- `payment_service.retry` no vuelve a correr el motor: reintenta la decisión ya tomada (el saldo ya la descuenta). Es
  coherente con «la ejecución no deshace la decisión», pero si la política cambió entre el fallo y el reintento, el pago
  sale con la decisión original. Con el tope de 5 intentos el margen es chico.
- `process_pending` ejecuta los pagos en serie dentro de la petición (hasta 3 llamadas a Stripe por factura nueva). Con
  el lote demo no debería acercarse al tiempo máximo de una función de Vercel, pero no lo medí.
- Propiedad de archivos: el carril tocó `contracts.py` (`PaymentExecution`, `Decision.execution`), `config.py`
  (`payment_rail`), `pyproject.toml` y `uv.lock` (`stripe==16.0.0`). El informe del carril dice que estaban
  autorizados, pero **no hay brief `docs/lanes/L9-*.md` en el repositorio**, así que no pude contrastarlo; los cambios
  son aditivos y con valores por defecto, sin romper consumidores existentes.

## Qué NO pude verificar

- **Stripe real: NO MEDIDO.** No hay `STRIPE_SECRET_KEY` en este entorno; el test live quedó `skipped`. Sigue sin
  comprobarse que la API `2026-09-30.endive` acepte la cuenta *Custom* con esos valores mágicos, que la recarga con
  `pm_card_bypassPending` deje saldo al instante y que el listado por `transfer_group` sea consistente justo después
  de crear la transferencia.
- **Tests con modelo: NO MEDIDO.** No hay `ANTHROPIC_API_KEY` en el entorno; este carril no agrega tests live de modelo.
- El brief del carril (no está en el repo): revisé contra `docs/DESIGN.md`, `docs/PAYMENTS.md` y el informe `L9.md`.
- La web contra la API real y la vista en un navegador: sólo tests de componentes y `next build`.
- Concurrencia real con dos procesos pagando la misma factura.
