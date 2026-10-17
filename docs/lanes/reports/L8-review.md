# Revisión de L8 (PR #10, `lane/L8-integration`)

**Veredicto: LISTO PARA MERGE.** No hay hallazgos bloqueantes. Encontré un defecto menor en el onboarding y lo arreglé
con test rojo primero. Después, por aviso del dueño, rebaseé la rama sobre `origin/main` en `d6b64a9` (merge de L9,
riel de Stripe), resolví los conflictos conservando todo lo de L9 y adapté sus piezas a las formas tipadas de L8. Revisó
una sesión distinta de la que escribió el código.

No existe `docs/lanes/L8-*.md` en el repositorio (ni en `main` ni en el historial). Juzgué el alcance contra
`docs/lanes/reports/L8.md`, `docs/DESIGN.md` (incluida §13) y `docs/lanes/COMMON.md`.

## Compuerta

`./scripts/check.sh`, siempre sobre el árbol limpio.

| Corrida | ruff | formato | mypy | pytest | web | resultado |
|---|---|---|---|---|---|---|
| Inicial (`9f4a4bf`, sobre `23255f1`) | `All checks passed!` | `143 files already formatted` | `Success: no issues found in 84 source files` | `729 passed, 21 skipped` | `check:api` «schema.gen.ts coincide con la API.», eslint y `tsc` limpios, vitest `14 passed (14)` archivos / `75 passed (75)` tests, `next build` correcto | `== gate passed` (EXIT 0) |
| Tras mi arreglo (`49ff730`, sobre `23255f1`) | `All checks passed!` | `143 files already formatted` | `Success: no issues found in 84 source files` | `729 passed, 21 skipped` | `check:api` coincide, eslint y `tsc` limpios, vitest `15 passed (15)` / `77 passed (77)`, `next build` correcto | `== gate passed` (EXIT 0) |
| **Final, rebaseada (`0d4215b`, sobre `d6b64a9`)** | `All checks passed!` | `158 files already formatted` | `Success: no issues found in 91 source files` | `765 passed, 22 skipped` | `check:api` «schema.gen.ts coincide con la API.», eslint y `tsc` limpios, vitest `17 passed (17)` / `88 passed (88)`, `next build` correcto | `== gate passed` (EXIT 0) |

Los conteos de la corrida final suben por L9 (sus tests de API, su test `live` de Stripe, que se omite, y sus tests de
la web) y por mis 2 tests de `hooks.test.tsx`. Los 22 omitidos son los `live`.

En la corrida final, vitest imprime «Not implemented: HTMLCanvasElement.prototype.getContext» desde
`components/brand/guilloche.tsx`: lo provoca el `app/page.test.tsx` que agregó L9 al renderizar la portada en jsdom.
No falla ningún test y no es de L8; lo dejo anotado.

Nota de método: una primera corrida mía salió EXIT 1 porque escribí mi test nuevo mientras la compuerta corría y
vitest lo tomó. La descarté y repetí la inicial con el árbol limpio; la tabla sólo trae corridas limpias.

## Rebase sobre L9

`git rebase origin/main` reescribió los 16 commits (los 13 del carril y los 3 de esta revisión). Conflictos y cómo
los resolví:

| Commit (nuevo) | Archivo | Resolución |
|---|---|---|
| `3cd1362` api: give the web the summary… | `apps/api/custodio/api/routes/decisions.py` | Las dos importaciones: `InvoiceSource` (L8) y `payment_service` (L9). La ruta `POST /decisions/{id}/execute` de L9 queda intacta. |
| `54c53d6` web: generate the API types… | `apps/web/src/lib/api/contracts.ts` | Los alias del esquema de L8, más `PaymentExecution = Schemas["PaymentExecution"]`; `PaymentRailName` y `ExecutionStatus` salen de sus campos `rail` y `status`, ya no escritos a mano. **`schema.gen.ts` regenerado** con `npm run gen:api` desde el OpenAPI de main + L8: trae `/decisions/{invoice_id}/execute`, `Health.payment_rail` y `PaymentExecution`. |
| `54c53d6` | `apps/web/src/lib/api/live-client.test.ts` | Los tests de los dos lados (el de L9 para `execute` y los cuatro de L8). |
| `1e39b01` web: derive every request… | `client.ts` | La versión tipada por ruta de L8; `Health` ya incluye `payment_rail` desde el esquema, así que el `Pick` + intersección de L9 sobra. `executePayment` queda en la interfaz. |
| `1e39b01` | `live-client.ts` | Las llamadas tipadas de L8, más `executePayment` como `call("post", "/api/v1/decisions/{invoice_id}/execute", { params })`: la ruta y su respuesta salen del esquema. |
| `1e39b01` | `mock/dataset.ts`, `mock/mock-client.ts` | El mock tipado de L8, más lo de L9: `simulatedExecution` en `freshDemo` y en el pago aprobado (recuperé `const at` en `settle`), `executePayment` y `payment_rail: "simulated"` en `health`. Los dos tests de L9 del mock suponían el demo ya decidido; con L8 el mock arranca sin decidir, así que ahora llaman `processedDemo()` (fixup dentro del mismo commit). |
| `d4f5f6f` web: read the acta… | `acta.test.tsx`, `mock-client.ts` | Las importaciones de los dos lados (`PaymentExecution` y `actaOf`). Los tests de L9 del bloque de pago pasan sobre el `Acta` tipado de L8. |

Se mezclaron solos: `acta.tsx` (el bloque `PaymentExecutionBlock` sobre `ActaData`), `acta-drawer.tsx`,
`dashboard.tsx` (la insignia `RailBadge` de L9 y el aviso `ReceivedInvoices` de L8, ambos presentes), `hooks.ts`
(`useRetryPayment` de L9 y el onboarding de L8) y `docs/DESIGN.md` (la tabla de rutas lleva las dos filas).

Comprobé después del rebase: `npm run check:api` coincide, `tsc` y eslint limpios, y ningún archivo quedó con marcas
de conflicto.

## Lo que comprobé por mi cuenta

- **e2e** (`cd apps/web && npm run e2e`, con el Chromium del entorno):
  - Antes del rebase, sobre `49ff730`: `2 passed (43.6s)`.
  - Después del rebase, sobre `0d4215b`: `2 passed (42.0s)`, con `[bogota]` en 15.8 s y `[tokio-oscuro]` en 14.4 s.
    Agregué dos comprobaciones (`0d4215b`): el panel muestra «Riel: Simulado», y el acta de una factura pagada muestra
    la región «Ejecución del pago» con «Simulado» y «no se movió dinero», contra la API real.
  - Mi primer intento falló porque buscaba el botón «Pagadas» por nombre exacto, y su nombre accesible incluye el
    conteo («Pagadas 17»). Lo corregí antes de commitear.
- **La compuerta detecta la deriva**: con una línea `// drift` añadida a `schema.gen.ts`, `npm run check:api` falla
  (exit 1, «src/lib/api/schema.gen.ts no coincide con la API»). Lo revertí.
- **Historial TDD** (verificado antes del rebase, en un worktree aparte; entre paréntesis, el SHA nuevo):
  - Los tests de `a1a9e56` (`14ab28c`) contra el código de ese commit dan `8 failed, 31 passed`: los 8 nuevos de API
    están rojos antes de `6679ea5` (`3cd1362`).
  - `received-invoices.test.tsx` en `8b1bf2c` (`ff54d07`) da `1 failed | 2 passed`, rojo antes de `acfb21e`
    (`b544add`).
  - `d5bff90` (`5e699fd`) importa un componente que aún no existe, así que es rojo por construcción.
- **Autoría**: todos los commits de `origin/main..lane/L8-integration`, incluidos los de este informe, son de Juan David Leon con el correo noreply.
  Ninguno trae `Co-Authored-By`, «Generated with» ni menciones a Claude o IA.
- **§13**: ningún `+` del diff de L8 agrega Gemini ni Telegram, y `schema.gen.ts` no los menciona.

## Invariantes de DESIGN §3

L8 no cambia ninguna ruta de pago: el motor, el auditor, las reglas R1–R12, el registro y el riel de L9 no se tocan.

- `CompileRequest.base` (`apps/api/custodio/api/routes/policy.py:19`) sólo cambia contra qué política propone el
  modelo; la propuesta no se aplica. Aplicarla sigue pasando por `PUT /policy` o por `onboarding/complete`, con la
  misma validación de `Policy`. El cuerpo sigue bajo el límite de `body_limit.py` y la ruta bajo `ModelCallLimit`.
- `records.audit_report` (`records.py:189`) sólo lee: suma los veredictos guardados. Un pago que el auditor detuvo
  queda en `hold` (`invoice_service._held`), que no está en `PAID`, así que no se cuenta dos veces en `checked`.
  `improper_payments` coincide con `metrics.improper_payments`, que suma la misma columna `audit_blocked`.
- `records.autonomous_spend` (`records.py:176`) es sólo lectura para el panel. Cuenta lo mismo que la historia de pagos
  del motor, incluidos los pagos cuya ejecución por el riel de L9 falló, igual que R11.
- `tests/e2e_app.py` no se despliega (`vercel.json` sirve `main:app`) y pytest no lo recoge (no empieza por `test_`).
  Tras el rebase usa el riel por defecto de L9 (`simulated`).

## Hallazgos

| # | Gravedad | Dónde | Hallazgo | Estado |
|---|---|---|---|---|
| 1 | menor | `apps/web/src/lib/api/hooks.ts:135-151` | `useCompleteOnboarding` crea un espacio `blank` y lo escribe en la cookie **antes** de llamar `onboarding/complete`. Si la API rechazaba la empresa (422 por una política inválida, red caída, 5xx), el navegador quedaba apuntando a un espacio vacío y sin configurar, y el visitante perdía su espacio demo. `SimulationStep` (`finish-steps.tsx:27`) no reintenta, así que el error era permanente para esa visita. Además, el comportamiento nuevo del hook (crear un espacio propio) no tenía ningún test. | Test rojo en `350f4a9`; arreglo en `98b4381`: el hook guarda el espacio previo y lo restaura si `completeOnboarding` falla. |
| 2 | menor (rebase) | `apps/web/src/lib/api/mock/mock-client.test.ts` | Tras el rebase, dos tests de L9 fallaban (`2 failed`) porque pedían el acta de `F-001` sin procesar el demo, que en el mock de L8 arranca sin decidir. | Corregido dentro de `1e39b01` (usan `processedDemo()`). |

Observaciones que no cambié:

- **Propiedad de archivos**: el carril toca `scripts/check.sh`, `docs/DESIGN.md`, `apps/web/package.json` y su lockfile
  (dos dependencias de desarrollo fijadas) y servicios y rutas de la API. Es un carril de integración y el informe lo
  declara, pero sin `docs/lanes/L8-*.md` no puedo comprobar que el dueño lo haya autorizado. L8 no cambia
  `contracts.py`, `llm.py`, `config.py`, `pyproject.toml`, `uv.lock`, `vercel.json` ni `.github/`; los cambios en
  esos archivos que se ven contra el viejo `main` son de L9.
- **Cambio incompatible declarado**: `GET /decisions` pasa de `Decision[]` a `{decision, received_at, source}[]`.
  Ningún consumidor del repositorio usa esa ruta (tampoco los tests de L9); un agente externo sí lo notaría. Está en
  el informe y en DESIGN §8.
- `records.autonomous_spend` repite la suma por mes de `engine/decide.py:237` (`_agent_spending_in_history`, privada
  del motor). Las dos agrupan por `paid_on` y `by == "agent"`, así que hoy dan lo mismo; si R11 cambia su criterio,
  el panel podría desalinearse. No las uní para no hacer público un detalle del motor.
- `STREAM_DOC` usa `Any` (`redteam.py:17`): es el tipo que pide `responses=` de FastAPI, un borde. Lo dejo.
- Restaurar el espacio previo necesita la API key guardada. Si el navegador bloquea localStorage, el arreglo no puede
  restaurar y el navegador queda en el espacio nuevo, como antes. Es un caso raro y no inventé otro almacenamiento.
- El 500 sin clave en las rutas con modelo (la propuesta del informe para `llm.py`) es anterior a L8 y no es de este
  carril.
- El aviso de canvas en vitest que viene del test de portada de L9 (ver «Compuerta»).

## Commits de esta revisión (tras el rebase)

- `350f4a9` web: test that a refused onboarding leaves the browser in the workspace it had
- `98b4381` web: bring the browser back to its workspace when the API refuses the onboarding
- `0d4215b` e2e: check the payment rail badge and the acta's payment block against the real API
- este informe y la nota de rebase en `L8.md`

## Qué no pude verificar

- **Pruebas en vivo con el modelo: NO MEDIDO.** No hay `ANTHROPIC_API_KEY` en este entorno, así que no corrí
  `CUSTODIO_LIVE_TESTS=1 uv run pytest -m live`. El e2e usa los dobles deterministas, no Claude.
- **El riel de Stripe en vivo: NO MEDIDO.** No hay `STRIPE_SECRET_KEY` y el e2e corre con el riel `simulated`. El
  bloque del acta con una transferencia real o fallida sólo lo cubren los tests de componente de L9, con datos fijos.
- **El error de hidratación #418** reportado en producción: no intenté reproducirlo de nuevo. El e2e de los dos
  perfiles pasa sin errores de consola, que es lo mismo que afirma el carril.
- **Producción y Neon**: no desplegué ni probé contra Postgres (tampoco la migración `0003` de L9); todo fue SQLite y
  build local.
- **Firefox y WebKit**: sólo Chromium.
- **Que el dueño haya autorizado el alcance del carril** (archivos fuera de `apps/web`): no hay brief en el repositorio.
- **El historial TDD después del rebase**: lo verifiqué en los commits previos al rebase; los commits reescritos
  conservan los mismos tests, pero no repetí esa comprobación sobre ellos.
