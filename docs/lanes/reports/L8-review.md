# Revisión de L8 (PR #10, `lane/L8-integration`)

**Veredicto: LISTO PARA MERGE.** Sin hallazgos bloqueantes. Encontré un defecto menor en el onboarding y lo arreglé
con test rojo primero, en dos commits separados sobre la misma rama. Revisó una sesión distinta de la que escribió el
código.

No existe `docs/lanes/L8-*.md` en el repositorio (ni en `main` ni en el historial). Juzgué el alcance contra
`docs/lanes/reports/L8.md`, `docs/DESIGN.md` (incluida §13) y `docs/lanes/COMMON.md`.

## Compuerta

`./scripts/check.sh`, dos corridas sobre el árbol limpio.

| Corrida | ruff | formato | mypy | pytest | web | resultado |
|---|---|---|---|---|---|---|
| Inicial (`9f4a4bf`) | `All checks passed!` | `143 files already formatted` | `Success: no issues found in 84 source files` | `729 passed, 21 skipped` | `check:api` «schema.gen.ts coincide con la API.», eslint y `tsc` limpios, vitest `14 passed (14)` archivos / `75 passed (75)` tests, `next build` correcto | `== gate passed` (EXIT 0) |
| Final (`49ff730`, tras mis arreglos) | `All checks passed!` | `143 files already formatted` | `Success: no issues found in 84 source files` | `729 passed, 21 skipped` | `check:api` coincide, eslint y `tsc` limpios, vitest `15 passed (15)` / `77 passed (77)`, `next build` correcto | `== gate passed` (EXIT 0) |

Los 2 tests de vitest de más son los míos (`src/lib/api/hooks.test.tsx`). Los 21 omitidos son los `live`.

Nota de método: una primera corrida mía salió EXIT 1 porque escribí mi test nuevo mientras la compuerta corría y
vitest lo tomó. La descarté y repetí la inicial con el árbol limpio; la tabla da sólo corridas limpias.

## Lo que comprobé por mi cuenta

- **e2e** (`cd apps/web && npm run e2e`, con el Chromium del entorno, sobre `49ff730`): `2 passed (43.6s)` —
  `[bogota]` 15.4 s y `[tokio-oscuro]` 13.1 s. Coincide con el informe del carril.
- **La compuerta detecta la deriva**: con una línea `// drift` añadida a `schema.gen.ts`, `npm run check:api` falla
  (exit 1, «src/lib/api/schema.gen.ts no coincide con la API»). Lo revertí.
- **Historial TDD**: en un worktree aparte, los tests de `a1a9e56` contra el código de ese commit dan
  `8 failed, 31 passed` (los 8 nuevos de API rojos antes de `6679ea5`); `received-invoices.test.tsx` en `8b1bf2c` da
  `1 failed | 2 passed` (el del aviso que sobrevive al desmontaje, rojo antes de `acfb21e`). `d5bff90` importa un
  componente que aún no existe, así que es rojo por construcción.
- **Autoría**: los 13 commits del carril son de Juan David Leon con el correo noreply; ninguno trae `Co-Authored-By`,
  «Generated with» ni menciones a Claude o IA.
- **§13**: ningún `+` del diff agrega Gemini ni Telegram; `schema.gen.ts` no los menciona (0 apariciones).

## Invariantes de DESIGN §3

Ninguna ruta de pago cambia: el motor, el auditor, las reglas R1–R12 y el registro no se tocan.

- `CompileRequest.base` (`apps/api/custodio/api/routes/policy.py:19`) sólo cambia contra qué política propone el
  modelo; la propuesta no se aplica. Aplicar sigue pasando por `PUT /policy` o `onboarding/complete`, con la misma
  validación de `Policy`. El cuerpo sigue bajo el límite de tamaño de `body_limit.py` y la ruta bajo `ModelCallLimit`.
- `records.audit_report` (`records.py:176`) sólo lee: suma los veredictos guardados. Un pago que el auditor detuvo queda
  en `hold` (`invoice_service._held`), que no está en `PAID`, así que no se cuenta dos veces en `checked`;
  `improper_payments` coincide con `metrics.improper_payments`, que suma la misma columna `audit_blocked`.
- `records.autonomous_spend` (`records.py:163`) es sólo lectura para el panel.
- `tests/e2e_app.py` no se despliega (`vercel.json` sirve `main:app`) y no lo recoge pytest (no empieza por `test_`).

## Hallazgos

| # | Gravedad | Dónde | Hallazgo | Estado |
|---|---|---|---|---|
| 1 | menor | `apps/web/src/lib/api/hooks.ts:129-145` (antes 129-139) | `useCompleteOnboarding` crea un espacio `blank` y lo escribe en la cookie **antes** de llamar `onboarding/complete`. Si la API rechaza la empresa (422 por una política inválida, red caída, 5xx), el navegador quedaba apuntando a un espacio vacío y sin configurar, y el visitante perdía su espacio demo. `SimulationStep` (`finish-steps.tsx:27`) no reintenta, así que el error era permanente para esa visita. Además el comportamiento nuevo del hook (crear un espacio propio) no tenía ningún test. | Test rojo en `f397b97`; arreglo en `49ff730`: guarda el espacio previo y lo restaura si `completeOnboarding` falla. |

Observaciones que no cambié:

- **Propiedad de archivos**: el carril toca `scripts/check.sh`, `docs/DESIGN.md`, `apps/web/package.json` y su lockfile
  (dos dependencias de desarrollo fijadas) y servicios y rutas de la API. Es un carril de integración y el informe lo
  declara, pero sin `docs/lanes/L8-*.md` no puedo comprobar que el dueño lo haya autorizado. `contracts.py`, `llm.py`,
  `config.py`, `pyproject.toml`, `uv.lock`, `vercel.json` y `.github/` no cambian.
- **Cambio incompatible declarado**: `GET /decisions` pasa de `Decision[]` a `{decision, received_at, source}[]`. Ningún
  consumidor del repositorio usa la ruta; un agente externo sí lo notaría. Está en el informe y en DESIGN §8.
- `records.autonomous_spend` (`records.py:163`) repite la suma por mes de `engine/decide.py:237`
  (`_agent_spending_in_history`, privada del motor). Ambos agrupan por `paid_on` y `by == "agent"`, así que hoy dan lo
  mismo; si R11 cambia su criterio, el panel podría desalinearse. No lo uní para no hacer público un detalle del motor.
- `STREAM_DOC` usa `Any` (`redteam.py:17`): es el tipo que pide `responses=` de FastAPI, un borde. Lo dejo.
- Restaurar el espacio previo necesita la API key guardada; si el navegador bloquea localStorage, el arreglo no puede
  restaurar y queda como antes (en el espacio nuevo). Es un caso raro y no inventé otro almacenamiento.
- El 500 sin clave en las rutas con modelo (propuesta del informe para `llm.py`) es previo a L8 y no es de este carril.

## Commits de esta revisión

- `f397b97` web: test that a refused onboarding leaves the browser in the workspace it had
- `49ff730` web: bring the browser back to its workspace when the API refuses the onboarding
- este informe

## Qué no pude verificar

- **Pruebas en vivo con el modelo: NO MEDIDO.** No hay `ANTHROPIC_API_KEY` en este entorno; no corrí
  `CUSTODIO_LIVE_TESTS=1 uv run pytest -m live`. El e2e usa los dobles deterministas, no Claude.
- **El error de hidratación #418** reportado en producción: no lo intenté reproducir de nuevo; el e2e de los dos perfiles
  pasa sin errores de consola, que es lo mismo que afirma el carril.
- **Producción y Neon**: no desplegué ni probé contra Postgres; todo fue SQLite y build local.
- **Firefox y WebKit**: sólo Chromium.
- **Que el dueño haya autorizado el alcance del carril** (archivos fuera de `apps/web`): no hay brief en el repositorio.
