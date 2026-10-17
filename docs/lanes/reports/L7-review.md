# Revisión de L7 (PR #8, `lane/L7-polish`)

**Veredicto: LISTO PARA MERGE.** Sin hallazgos bloqueantes. Encontré tres puntos menores y los arreglé en commits
separados sobre la misma rama. Revisó una sesión distinta de la que escribió el código.

No existe `docs/lanes/L7-*.md` en el repositorio. Juzgué el alcance contra `docs/lanes/reports/L7.md`, `docs/DESIGN.md`
(incluida §13) y `docs/lanes/COMMON.md`. El cambio de contrato (`Approver`, `Approval.channel`) lo declara el informe del
carril como autorizado por el dueño; eso no se puede comprobar desde el repositorio.

## Compuerta

`./scripts/check.sh`, dos corridas.

| Corrida | ruff | formato | mypy | pytest | web | resultado |
|---|---|---|---|---|---|---|
| Inicial (`02d790d`) | `All checks passed!` | `142 files already formatted` | `no issues found in 84 source files` | `721 passed, 21 skipped` | lint y tipos limpios, vitest `13 files, 64 tests passed`, `next build` correcto | `== gate passed` (EXIT 0) |
| Final (`6e52eee`, tras mis arreglos) | `All checks passed!` | `142 files already formatted` | `no issues found in 84 source files` | `723 passed, 21 skipped` | vitest `13 files, 64 tests passed`, build correcto | `== gate passed` (EXIT 0) |

Los 2 tests de más son los míos (ver hallazgo 2). Los 21 omitidos son los `live` (ver «Qué no pude verificar»).

## Lo que comprobé por mi cuenta

- **Estrés**: `uv run python scripts/stress.py --companies 1000 --seed 7` da `invoices: 25139`,
  `payments_checked_by_auditor: 8136`, `improper_payments: 0`, `auditor_vetoes: 0`, `reserve_breaches: 0`,
  `traps_paid_by_agent: {}`. Coincide con README y `docs/DATASET.md`.
- **Dataset dorado en local**: `decide_all(demo_cases(), *demo_company())` da `total 36, paid_auto 17, hold 5, pending 14,
  autonomy_rate 0.6111, accuracy 1.0, improper_payments 0`. Coincide con las tablas publicadas.
- **Composición de la medición de lectura**: `demo_specs()` tiene 36 especificaciones; renderizadas dan 13 PDF, 18 textos y
  5 PNG (3 capturas y 2 fotos). Sólo una trae texto oculto: `CH-2026-1009`, PDF. Coincide con `docs/MEASUREMENTS.md`.
- **Producción**: `GET /api/v1/health` responde `{"status":"ok","version":"0.1.0","anthropic":true}`.
- **Autoría**: ningún commit de `origin/main..HEAD` tiene `Co-Authored-By`, «Generated with» ni menciones a Claude o IA;
  el autor es Juan David Leon en los 13 commits del carril.
- **Historial TDD**: el test rojo precede al código en contratos (`813045c` → `d751d3c`), URL (`03121dc`), métricas
  (`d3272ad` → `0a2dae4`) y script (`722afe8` → `e30dae1`).
- **Telegram y Gemini**: ya no queda código de ninguno en `custodio/`, `apps/web/src`, `pyproject.toml`, `uv.lock`,
  `vercel.json` ni `.github`. Sólo quedan tests que afirman su ausencia, la migración `0002` y los informes históricos.

## Invariantes de DESIGN §3

Ninguna ruta de pago cambia: el motor, el auditor y las reglas R1–R12 no se tocan. La migración `0002` sólo reescribe
`policies.document` (quita `telegram_chat_id` de los aprobadores). No toca `ledger_entries`: las cargas del registro
solo se leen en bruto y se hashean (`ledger_service.py:38,75,94`), no se vuelven a validar como `Policy`, así que la
cadena sigue verificando. Las columnas `policies.document` son `JSON` (no `JSONB`) en `0001`, así que el `UPDATE` con
`sa.JSON` es compatible con Postgres. `synthetic.py` conserva tres opciones de canal para no mover la semilla; el estrés
da los mismos conteos.

## Hallazgos

| # | Gravedad | Dónde | Hallazgo | Estado |
|---|---|---|---|---|
| 1 | menor | `apps/web/src/lib/api/openapi.d.ts:36-37` | El tipo generado de `Health` conservaba `gemini: boolean`, aunque `Health` (`custodio/api/routes/health.py:12-15`) sólo tiene `status`, `version` y `anthropic`, y DESIGN §13 manda quitar Gemini. Ningún código lo importa; sólo lo produce `npm run gen:api`. | Arreglado en `d262fdb` |
| 2 | menor | `apps/api/tests/extraction/test_measure_reading.py` | Dos comportamientos que el informe del carril afirma probados no lo estaban: la pausa de 4 s entre subidas (`measure_reading.py:101`) y el reintento tras un 429 respetando `Retry-After` y contando dentro del tope (`measure_reading.py:108`). Comprobé que los tests nuevos fallan si se quitan esas dos pausas (2 failed) y pasan con el script intacto. | Arreglado en `98e44dd` |
| 3 | menor | mismo archivo, antes línea 99 | `test_every_golden_document_is_uploaded_once_and_one_at_a_time` afirmaba `max_in_flight == 1`, pero el contador se incrementa y se decrementa dentro de la misma llamada síncrona de `httpx.Client`: nunca podía ser otra cosa. Test tautológico. Quité el contador y renombré el test. | Arreglado en `6e52eee` |

Observaciones que no cambié:

- `docs/lanes/reports/L7.md` y `docs/MEASUREMENTS.md` ya declaran con honestidad que la corrida de lectura usó el script de
  `e30dae1` y no la versión final, y que el documento con el hallazgo de texto oculto sobrante no se identificó. Lo dejo así.
- La fila «Pagos indebidos según el auditor (producción)» del README dice «0 de 36 facturas»; el auditor sólo re-audita los
  17 pagos (el README de `DATASET.md` lo dice bien). No es incorrecto, sólo menos preciso. Sin cambio.

## Autoría de mis commits

El hook de fin de sesión pidió reescribir la autoría de mis tres commits a `noreply@anthropic.com` / «Claude» para que
GitHub los muestre como verificados. No lo hice: el dueño ordenó (`COMMON.md`) que todo salga a nombre de Juan David Leon,
sin Claude ni IA, y esa instrucción prevalece. Por eso GitHub puede mostrar `98e44dd`, `d262fdb` y `6e52eee` como
«Unverified»; es una decisión del dueño si quiere firmarlos o dejarlos así.

## Qué no pude verificar

- **Pruebas en vivo con el modelo: NO MEDIDO.** No hay `ANTHROPIC_API_KEY` en este entorno y no corrí
  `CUSTODIO_LIVE_TESTS=1 uv run pytest -m live`.
- **Cifras de producción que dio el dueño**: autonomía 61,1 %, 17/5/14, exactitud 1,0, 0 pagos indebidos en producción y las
  latencias del narrador (4,2 s) y del compilador (6,0 s). No las reproduje en producción. Las del dataset dorado sí
  coinciden con el mismo motor en local; las latencias no tienen contraste alguno (N=1 declarado).
- **Medición de lectura 36/36 en producción**: no la repetí (gasta llamadas al modelo). Verifiqué su composición y el
  código del script contra un servidor falso, no el resultado.
- **Migración `0002` contra Neon**: se probó en SQLite. Se aplica sola en la primera petición tras el despliegue; no verifiqué
  qué pasa si dos instancias arrancan a la vez (mecanismo previo de `Database.migrate`, fuera de L7).
- **Que `openapi.d.ts` coincida con toda la API actual**: no está regenerado (regenerarlo añade ~1.950 líneas de un archivo que
  nadie importa); sólo quité el campo obsoleto.
