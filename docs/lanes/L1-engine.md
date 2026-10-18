# L1 · Motor de decisión, ledger y dataset

**Objetivo**: el corazón determinista. Si este carril es perfecto, Blinka Keeper nunca paga algo indebido.

## Archivos tuyos
`apps/api/custodio/engine/**`, `apps/api/custodio/dataset/**`, `apps/api/tests/engine/**`,
`apps/api/tests/dataset/**`, `apps/api/scripts/stress.py`.

## Qué implementar (firmas públicas ya fijadas en `engine/__init__.py` y `dataset/__init__.py`)

1. `engine/rules.py`: una función por regla R1–R12, cada una `(...) -> RuleResult` con razón en español y cifras
   concretas (formato es-CO: `USD 12.500`, `COP 4.200.000`). Semántica: `docs/DESIGN.md` §5 y
   `prototype/engine.js` líneas 289–457 (lee por rangos). Patrón de inyección ampliado (español e inglés).
2. `engine/beneficiaries.py`: casar proveedor por tax id normalizado o nombre normalizado/alias (sin tildes,
   minúsculas, sin puntuación ni sufijos societarios como S.A.S., Inc., Ltda.).
3. `engine/decide.py`: `decide_all` — orden por `received_at`, veredicto (retener > escalar > pagar), saldo y cupo,
   aprobaciones diferidas que nunca rompen la reserva, `Metrics` (incluida `accuracy` cuando hay `expected`).
4. `engine/explain.py`: `explanation` y `counterfactual` deterministas (portar `explain`/`counterfactual`).
5. `engine/audit.py`: auditor **independiente**: recalcula cada pago desde los datos crudos con código propio (no importa
   `rules.py` ni `decide.py`) y marca `improper_payments`.
6. `engine/simulate.py`: `simulate(cases, state, before, after)`.
7. `engine/ledger.py`: `canonical_json(obj) -> str`, `next_entry(prev: LedgerEntry | None, *, kind, subject_id,
   payload, at) -> LedgerEntry`, `verify(entries) -> LedgerVerification`.
8. `dataset/`: `cases.json` con la empresa demo («Cobalto Labs, Inc.», como el prototipo) y **≥ 36 facturas**:
   legítimas variadas (servicios, nómina tercerizada, hosting, arriendo, en USD/COP/MXN/BRL) y todas las trampas del
   reto y nuestras: duplicado exacto, duplicado con otro número, beneficiario nuevo, beneficiario bloqueado, cuenta
   cambiada, desacuerdo con lo pactado (fijo y tope mensual), sobre el límite por pago, sobre el tope de aprobación,
   cupo agotado, saldo/reserva insuficiente, fraccionamiento, moneda no permitida, moneda ambigua, lectura de baja
   confianza, instrucción visible al agente, texto oculto. Cada caso con `expected` y `trap`. `demo_specs()` devuelve
   los mismos como `InvoiceSpec` y `demo_cases()` como `InvoiceCase` con evidencia verificada.
9. `scripts/stress.py`: N empresas y lotes aleatorios (semilla fija) → JSON con decisiones, pagos indebidos según el
   auditor (debe ser 0) y tiempo. Uso: `uv run python scripts/stress.py --companies 1000 --seed 7`.

## Tests (escríbelos primero)

- Unitarios por regla, incluidos bordes (exactamente en el tope, tolerancia ±2 %, ventana de días en el límite).
- Dataset dorado: 100 % de `accuracy` y 0 pagos indebidos; un test por trampa que nombre la regla que la atrapa.
- Propiedades (Hypothesis): determinismo; nunca se paga con una regla de retención fallida; el saldo nunca queda bajo
  la reserva (tampoco con aprobaciones); aprobar una factura no cambia el estado de otras; quitar `expected` y `trap`
  no cambia nada; el auditor coincide con el motor en lotes aleatorios.
- Mutantes: un motor saboteado (p. ej. que ignora R4) es detectado por el auditor.
- Ledger: cadena válida; alterar cualquier campo de cualquier entrada se detecta en esa `seq`.

## Fuera de alcance
Persistencia, HTTP, modelos, lectura de documentos.
