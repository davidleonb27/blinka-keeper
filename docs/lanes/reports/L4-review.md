# Revisión de L4 · API, persistencia, aprobaciones, firewall, MCP y reto público (PR #4)

Rama: `lane/L4-api`. Revisión hecha por una sesión distinta de la que escribió el código, siguiendo
`docs/lanes/REVIEW.md`. Base de la rama: `c76cf02` (`origin/main` avanzó después a `8052f47`; ver «Integración»).

## Veredicto: LISTO PARA MERGE

Encontré un camino bloqueante (dos aprobaciones simultáneas de la misma decisión dejaban dos pagos en el ledger) y un
hueco defensivo en el veto del auditor. Los dos están arreglados en esta rama con su test rojo primero. Lo que queda
abajo como «no arreglado» no rompe ningún invariante de `docs/DESIGN.md` §3; son mejoras para después.

## Compuerta

- Antes de la revisión (`24de352`): `./scripts/check.sh` → ruff `All checks passed!` · `66 files already formatted` ·
  mypy `Success: no issues found in 45 source files` · pytest `95 passed, 2 skipped` · `== gate passed` (exit 0).
- Después de los arreglos (`3b22290` + este informe): ruff `All checks passed!` · `66 files already formatted` · mypy
  `Success: no issues found in 45 source files` · pytest `97 passed, 2 skipped` · `== gate passed` (exit 0).
  Los 2 omitidos son los tests live de triaje (`tests/api/test_triage_live.py`).
- Suite completa contra Postgres 16.15 local (`CUSTODIO_TEST_POSTGRES_URL=postgresql://postgres@127.0.0.1:55432/postgres`):
  antes `95 passed, 2 skipped`; después `97 passed, 2 skipped`.
- CI del PR en `24de352`: check `gate` en verde.

## Integración con `main` actual

`origin/main` ya trae L1 (motor, auditor, ledger), L3 y L6. La rama no tiene conflictos con `8052f47`
(`git merge-tree` limpio), así que no hice rebase. En un worktree aparte con la rama mezclada con `origin/main`:

- `./scripts/check.sh` → `113 files already formatted` · mypy `Success: no issues found in 70 source files` · pytest
  `501 passed, 19 skipped` · `== gate passed`.
- Humo de `main:app` con el motor real de L1 (SQLite, sin modelos): `POST /workspaces` 201 (antes daba 500 porque
  faltaba `custodio.engine.ledger`) · `POST /invoices/process` 200 con 36 casos (17 pagadas solas, 5 retenidas, 14
  pendientes, `vetoed: []`, auditor `agrees: true`) · aprobar `F-003` → `paid_human` · segunda aprobación → 409 ·
  `GET /ledger/verify` válido (92 entradas) · tamper-demo rompe la copia en la 92 y el real sigue válido ·
  `GET /challenge/stats` 200.
- `POST /firewall/intents` responde 500 honesto con `main` actual: L2 aún no está fusionado y
  `custodio.extraction.extract_text` lanza `NotImplementedError`. Se resuelve cuando entre L2.

## Hallazgos

### Arreglados en esta rama

1. **Bloqueante · dos aprobaciones simultáneas pagaban dos veces** — `apps/api/custodio/services/approval_service.py:27`
   (antes la línea `if records.decision(...).status is not DecisionStatus.PENDING_APPROVAL`). La decisión se leía y se
   decidía en la misma transacción sin bloquearla. Lo reproduje en Postgres 16 con dos hilos: las dos respondían
   `paid_human`, quedaban 2 filas en `approvals` y **2 entradas `payment` para `F02`** en el ledger (el saldo derivado
   lo contaba una vez porque la fila de la decisión se sobrescribe, pero el registro decía dos pagos). En Postgres la
   segunda esperaba el bloqueo de la fila de la decisión y, al seguir, leía la cabeza del ledger ya confirmada, así
   que la unicidad de `seq` no la frenaba.
   Arreglo: `records.claim_pending` (`apps/api/custodio/services/records.py:88`) reclama la decisión con un
   `UPDATE … WHERE status = 'pending_approval'` antes de aprobar; la segunda aprobación espera, no encuentra la fila
   pendiente y responde 409. Funciona igual en SQLite y Postgres.
   Test: `tests/api/test_decisions.py:97` (`test_two_simultaneous_approvals_pay_only_once`), rojo en `0699b21`
   (`[200, 200]` en SQLite y en Postgres) y verde en `3524be5`; el script de carrera contra Postgres ahora da
   `A: paid_human, B: DecisionNotPending`, 1 aprobación, 1 pago.
2. **Defensivo · un hallazgo crítico del auditor sobre el lote no detenía nada** —
   `apps/api/custodio/services/invoice_service.py:182`. `_stopped_payments` sólo vetaba pagos con un hallazgo de su
   propio `invoice_id`, o todos si `improper_payments` superaba los atribuidos. Un hallazgo crítico sobre el lote
   (como la violación `'saldo'` de `prototype/engine.js:534`, «los pagos aprobados tocan la reserva») que no se
   contara en `improper_payments` dejaba salir los pagos. Arreglo: un hallazgo crítico que no nombra un pago del
   lote cuenta como objeción al lote y no sale ningún pago (gana el auditor). Con el auditor real de L1 en `main` hoy
   no es alcanzable (cada hallazgo es crítico y nombra el pago), así que no cambia ninguna decisión actual.
   Test: `tests/api/test_invoices.py:133`, rojo en `8efa575`, verde en `e19cafc` (el doble `FakeAuditor` acepta
   `batch_findings`).
3. **Informe del carril desactualizado** — `docs/lanes/reports/L4.md`: conteos (95 → 97, invoices 13, decisions 14) y
   la nota de concurrencia, en `3b22290`.

### No arreglados (no bloqueantes)

4. **Contadores de tasa con carrera** — `apps/api/custodio/services/rate_limits.py:35`. `SELECT` y luego `INSERT`/
   incremento en Python: dos peticiones simultáneas en una ventana nueva chocan en la clave primaria (una responde 500)
   y con READ COMMITTED se pueden perder incrementos, así que el tope (incluido el diario global `challenge:all`) es
   aproximado bajo concurrencia. Propuesta: `INSERT … ON CONFLICT DO NOTHING` por dialecto y luego
   `UPDATE … SET count = count + 1 WHERE count < :limit` mirando `rowcount`. No lo cambié porque no encontré un test
   rojo determinista en SQLite que la compuerta corra.
5. **IP del cliente desde `X-Forwarded-For`** — `apps/api/custodio/api/deps.py:57`. Toma la primera IP de la cabecera.
   Es correcto si Vercel la sobrescribe (su documentación dice que lo hace); si la web llama a la API desde el
   servidor por el binding de Services, la IP sería la de la web y el límite por IP se volvería global. NO VERIFICADO
   en Vercel.
6. **`POST /workspaces` sin límite** — `apps/api/custodio/api/routes/workspaces.py:25`. Cada llamada siembra la demo
   (36 facturas y su ledger). Crear espacios nuevos también esquiva el límite por espacio (queda el de IP y el tope
   de gasto de `llm.py`). El brief sólo exige límites en rutas con modelos; recomiendo un límite por IP.
7. **Red team: un solo cupo de tasa por corrida de hasta 12 rondas** — `apps/api/custodio/api/routes/redteam.py:25`.
   Cada ronda llama al atacante y al lector. Además, si `_record_verdict`
   (`apps/api/custodio/services/redteam_service.py:88`) choca con otra escritura del mismo espacio en el ledger, el
   stream se corta sin un evento `error`. Poco probable en la demo.
8. **Triaje del reto dentro de la transacción** — `apps/api/custodio/services/challenge_service.py:49`. La llamada a
   `model_cheap` ocurre con la transacción abierta; en Neon pooled conviene sacarla antes de escribir.
9. **El aprobador es texto libre** — `apps/api/custodio/services/approval_service.py:31`. No se compara con
   `policy.approvers`. Con la cabecera del espacio como única credencial es nominal, pero la regla «lo aprueba Ana»
   no se hace cumplir. Decisión de producto para el coordinador (o L1, si `decide_all` debe validarlo).
10. **Textos de hasta 4 MB van al lector** (factura en texto, `document_text` del firewall). El tope diario de
    `llm.py` limita el gasto; un tope de caracteres más bajo para texto sería más barato.
11. **Menores de código limpio**: `assert` para estrechar tipos en `apps/api/custodio/services/onboarding_service.py:93`
    (aceptable); `tests/test_base.py` está fuera de la lista de archivos de L4, pero sus 2 tests nuevos acompañan el
    cambio autorizado de `config.py` (§13), así que lo doy por bueno.

## Lo que revisé y está bien

- **Corrección**: todas las rutas de `docs/DESIGN.md` §8 bajo `/api/v1`, sin Telegram (§13). `/health` responde
  `{status, version, anthropic}`. `DATABASE_URL` `postgres://`/`postgresql://` → `postgresql+psycopg://`. La migración
  `0001` coincide con los modelos (`alembic.autogenerate.compare_metadata` sin diferencias) y no tiene
  `approval_tokens`.
- **Invariantes §3**: el motor recibe `InvoiceCase` sin `expected` ni `trap` (`records.as_case`); el veto del auditor
  gana y no descuenta; la guarda extra de reglas de retención; aprobar vuelve a correr el motor con el saldo del
  momento (test de la reserva); un `hold` no se aprueba (409); toda escritura queda en el ledger y se verifica en cada
  flujo; el tamper-demo nunca toca el ledger real; un `LLMError` en lectura deja la factura sin leer para R1, con 503
  honesto y la factura guardada.
- **Seguridad**: la api key se guarda sólo como SHA-256; 404 uniforme por cabecera; los espacios del reto y del red
  team no se abren por cabecera ni por api key; firewall y MCP usan el mismo embudo `invoice_service.decide`, el mismo
  límite de tasa y la misma api key (la puerta ASGI de MCP da 401 sin clave); los errores no filtran secretos (el log
  de `LLMError` sólo registra el tipo); la IP se guarda como digest; cuerpo > 4 MB + 64 KB → 413 antes de la ruta.
- **Tests**: prueban comportamiento por HTTP con dobles honestos detrás de las firmas públicas. TDD visible verificado
  ejecutando la suite en cada commit rojo: `147ca70` (error de colección: los módulos no existían), `6d8550e`
  (1 failed), `d626fe7` (1 failed, 37 passed), `29014ee` (1 failed, 102 passed), `cae60a0` (1 failed, 19 passed), cada
  uno antes de su implementación.
- **Propiedad de archivos y contratos**: sin cambios en `contracts.py`, `llm.py`, `pyproject.toml`, `uv.lock`,
  `vercel.json`, `scripts/` ni `.github/`. `config.py` cambió sólo en lo que autoriza §13.
- **Idioma y autoría**: código e identificadores en inglés, mensajes al usuario en español. Los 16 commits del autor y
  los míos están a nombre de Juan David Leon `<271861486+davidleonb27@users.noreply.github.com>`, sin trailers ni
  menciones de herramientas.

## Commits de esta revisión

- `8efa575` api: add failing test that a critical audit finding on the whole batch stops every payment
- `e19cafc` api: stop every payment of a batch when the auditor objects to the batch as a whole
- `0699b21` api: add failing test that two simultaneous approvals pay only once
- `3524be5` api: claim a pending decision with a row write before approving it
- `3b22290` docs: refresh the L4 report counts and concurrency note after review
- este informe

## Lo que NO pude verificar

- **Tests con modelos reales: NO MEDIDO.** `ANTHROPIC_API_KEY` no está en el entorno; los 2 tests live de triaje
  quedaron omitidos.
- **Integración con L2: NO MEDIDO.** L2 no está en `main`; firewall, MCP `submit_payment_intent`, subida de facturas,
  reto y red team con el lector real dan 500 honesto hasta que entre.
- Integración con L3 real por HTTP (compilar, narrar, perfil, proveedores, red team): NO MEDIDO, necesita modelo.
- Despliegue en Vercel (lifespan ASGI para MCP, SSE detrás del proxy, `X-Forwarded-For`), Neon real y un cliente MCP
  de escritorio: NO MEDIDO. Postgres se probó sólo en local (16.15).
- Concurrencia fuera de la aprobación doble (límites de tasa, procesar lotes en paralelo): sólo revisada leyendo el
  código, no medida.
