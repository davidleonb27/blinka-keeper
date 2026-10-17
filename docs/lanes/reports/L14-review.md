# Revisión de L14 · Conciliación bancaria y cierre de mes (PR #17)

**Veredicto: LISTO PARA MERGE**

Rama `claude/l14-bank-reconciliation-p0r4n1`, revisada sobre `10284bc` (ya contiene `origin/main` en `c546f4f`).
Los arreglos van en commits nuevos, sin rebase ni force-push.

## Compuerta

- Antes de los arreglos: `./scripts/check.sh` → `== gate passed` (api: `1116 passed, 23 skipped`; web: schema, lint,
  types, tests y build correctos).
- Después de los arreglos: `./scripts/check.sh` → `== gate passed` (api: `1118 passed, 23 skipped`; web: `145 passed`
  en 24 archivos, build correcto).
- `uv run pytest tests/reconciliation -q` tras los arreglos → `94 passed, 1 skipped` (el omitido es el test live).

## Hallazgos y arreglos

1. **Cargo/abono con «0,00» en la columna que no aplica dejaba todas las filas NO LEÍDAS** —
   `apps/api/custodio/reconciliation/csv_statement.py:204`. Muchos bancos exportan `1.400,00;0,00`; la regla «cargo y
   abono a la vez → no se elige» lo trataba como conflicto. No era inseguro (bloquea el cierre) pero hacía inusable un
   extracto real. **Arreglado**: una celda de cargo o abono que se lee como cero cuenta como vacía (`_nonzero`, l. 215).
   Dos valores distintos de cero siguen quedando NO LEÍDOS.
2. **Un monto con una marca de texto («50,00 DB», «50 DR») se leía como +50, es decir, como ingreso** —
   `csv_statement.py:221`. Una salida marcada así escapaba de la alerta roja y no bloqueaba el cierre: dinero que sale
   sin factura que lo explique quedaba como «fuera de cuentas por pagar». **Arreglado**: si la celda del monto trae una
   palabra que no es un código de moneda de tres letras (`USD`, `COP`; también se admiten `US$` y `R$`), la fila queda
   NO LEÍDA con la razón, en vez de adivinar el signo. «CR» también queda NO LEÍDA (prudente; una persona la revisa).

Tests rojos primero (`test_a_zero_in_the_other_column_of_debit_and_credit_counts_as_empty`,
`test_an_amount_with_a_debit_or_credit_word_stays_unread_instead_of_turning_positive` en
`apps/api/tests/reconciliation/test_csv_statement.py:146` y `:157`), commit aparte antes del arreglo.

## Lo que revisé y está bien

- **Parser CSV**: separadores `;`, `,` y tabulador; preámbulo del banco y filas de saldo/total; UTF-8 con y sin BOM y
  Latin-1; `-1.400,00`, `1,400.00-`, `(25.00)`, `−12,50`, `USD -5,00`; fechas ISO, `dd/mm/aaaa`, `dd-mm-aa`, y mes/día
  sólo cuando el archivo lo prueba o los encabezados son ingleses (con aviso). Límite de 2000 movimientos y 4 MB
  (`MAX_STATEMENT_BYTES`, más el límite global de cuerpo en `api/body_limit.py`). Probado a mano con casos fuera de los
  tests.
- **Emparejamiento** (`reconciliation/match.py`): mismo monto exacto en la moneda del movimiento (cuantizado a
  centavos), nunca entre monedas que no se pueden comparar; la tolerancia de cambio sólo aplica a pagos en otra moneda
  y es explícita (`MatchSettings`, ≤ 5 %). Un movimiento lo toma un solo pago; los duplicados exactos se marcan con su
  ancla; los pagos sin movimiento quedan PENDIENTES con su razón; las salidas sin pago son alerta roja con pista
  (factura retenida/rechazada, referencia con monto distinto). Propiedades con Hypothesis cubren el orden y el uso único.
- **La conciliación no paga ni cambia decisiones**: `reconciliation_service` no importa `payments/` ni escribe
  `DecisionRow`; sólo agrega asientos `reconciliation`, `reconciliation_review` y `period_closed` al registro y una fila
  en `reconciliations`. El modelo sólo lee PDFs/imágenes y cada fila se verifica contra el texto visible.
- **Aislamiento entre espacios**: `_row` comprueba `workspace_id` (404 si no coincide), el historial, `_latest`,
  `_closure` y el paquete filtran por espacio; la herramienta MCP usa la misma resolución de espacio por API key.
- **Migración `0005`**: `down_revision = "0004"`. En SQLite: `upgrade head` → `downgrade 0004` → `upgrade head` →
  `downgrade base` → `upgrade head`, termina en `0005 (head)` sin errores.
- **Cierre de mes en el registro encadenado**: `close_period` escribe `period_closed` con el resumen y se niega si quedan
  alertas sin revisar o si la cadena no verifica; un mes cerrado no admite nuevas conciliaciones ni revisiones (409).
  Así lo dice `docs/DESIGN.md` §14.
- **Contratos**: sólo tres valores nuevos en `LedgerKind`, justificados en el informe del carril.
- **Autoría**: todos los commits a nombre de Juan David Leon, sin atribuciones.

## UI (Chromium con Playwright, build de producción contra la API real)

- `walkthrough.e2e.ts` perfil Bogotá → `1 passed`, cero errores de consola, cero excepciones y cero HTTP ≥ 400
  (incluye el paso completo de conciliación, revisión de alertas, cierre y descarga del paquete).
- Prueba propia a **360 × 780** (spec temporal, no se dejó en el repo): demo → decidir facturas → `/conciliacion` →
  extracto de demo → revisar una alerta. `scrollWidth` del documento = 360 (sin scroll horizontal; sólo la barra de
  navegación desborda dentro de su propio contenedor desplazable), cero errores de consola y de red. Tarjetas, montos,
  insignias y formularios se leen y se usan bien a ese ancho.

## Pendiente o no verificado (no bloquea)

- Lectura real de PDF/imagen con Claude: sin `ANTHROPIC_API_KEY` en este entorno; el test live quedó omitido.
- Postgres: no probado (sólo SQLite).
- Dos cierres simultáneos del mismo mes no tienen restricción única (lo declara el autor). Sugerencia futura: índice
  único parcial o `SELECT … FOR UPDATE` en Postgres.
- Montos con espacio como separador de miles («1 400,00») quedan NO LEÍDOS: seguro, pero obliga a revisar.
- El CSV se parte por líneas: un campo entre comillas con salto de línea dentro rompe esa fila (queda NO LEÍDA o falla
  el encabezado). Raro en exportaciones bancarias.
- Un movimiento que paga varias facturas (uno a muchos) no se empareja y queda como alerta (declarado por el autor).
- La referencia exacta (nivel 1) no exige la ventana de fechas; el monto exacto la acota lo suficiente.
