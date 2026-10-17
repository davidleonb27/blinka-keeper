# Revisión de L12 · Controles de pago (R13 datos bancarios, R14 OFAC, R15 fuera de banda)

Rama: `claude/lane-l12-payment-controls-dr32yr` (PR #14). Revisión hecha por una sesión distinta de la que escribió el
carril, siguiendo `docs/lanes/REVIEW.md`.

## Veredicto: **LISTO PARA MERGE**

Encontré un camino que pagaba sin la revisión de R14 (bloqueante) y lo arreglé en esta rama. No queda ningún camino
conocido donde se pague con R13, R14 o R15 fallida. El dorado y la prueba de estrés siguen con 0 pagos indebidos.

## Rebase sobre `main`

La rama se rebasó sobre `origin/main` en `bbb7eb0` (merge de L11, PR #11) y se empujó con `--force-with-lease`.
Conflictos:

- `apps/web/src/lib/api/schema.gen.ts`: **regenerado** con `npm run gen:api` (`apps/web/scripts/gen-api-schema.mjs`),
  no a mano. Queda con lo de L11 (riel Blinka, instrucción de pago) y con lo de L12 (`email_domain`,
  `sender_email`, `sanctions_list_date`). `npm run check:api` → «schema.gen.ts coincide con la API».
- `apps/api/tests/delivery/test_delivery_docs.py`: se conservaron los dos lados, es decir, los tests de la página Blinka
  de L11 y el test de L12 que impide «12/doce reglas» en los documentos.
- `contracts.py`, `rules.py`, `decide.py` y `apps/web/src/lib/api/contracts.ts` se mezclaron sin conflicto. Revisé el
  diff de `contracts.py` contra `main`: sólo trae los cambios de L12 que pidió el carril (R13–R15,
  `neutral_when_skipped`, `email_domain` y `sender_email`, todos opcionales). Los campos de L11 quedan intactos.
- Efecto del rebase: L11 agregó `BLINKA.md` y `PAYMENTS.md` a los documentos vigilados, y `docs/BLINKA.md` decía
  «12 reglas» dos veces. La compuerta lo detectó (`1 failed`) y lo corregí (commit `docs: the Blinka page counts
  fifteen rules`).

## Hallazgos

### Bloqueante (arreglado)

1. **R14 fallaba en abierto con una lista vacía.** En `custodio/engine/rules.py:666`, si la lista cargada tenía
   0 entradas, R14 devolvía `skipped`. Como R13–R15 tienen `neutral_when_skipped` (`custodio/engine/decide.py:41`), ese
   `skipped` no frenaba el pago: una factura limpia se pagaba sola **sin que nadie la revisara contra OFAC**, y el acta
   decía «no se revisó». El auditor tampoco lo veía (`_sanctions_problems` no encontraba coincidencias en una lista
   vacía). Hoy sólo se llega por inyección (`sanctions=`), porque si falta la copia empaquetada, `bundled_sanctions`
   lanza un error. Aun así es justo la clase de camino que §3 prohíbe, y un `update_ofac.py` que escriba una lista
   vacía lo abriría en producción.
   - Arreglo: R14 **escala** con 0 entradas («el proveedor no se revisó y no se paga solo»), con su contrafactual.
     El auditor (`custodio/engine/audit.py:347`) marca como indebido todo pago automático revisado contra una lista
     vacía, así que gana aunque el motor se equivoque.
   - Test rojo antes del verde: `test: R14 and the auditor never let an unscreened name be paid alone` →
     `engine: escalate R14 when no sanctions list is loaded…`. Los tests son
     `test_r14_escalates_when_no_sanctions_list_is_loaded` y
     `test_an_autonomous_payment_screened_against_no_list_is_improper`. `docs/DESIGN.md` §5 lo dice en la fila de R14.

### Revisado sin problema

- **`verdict_of`** (`decide.py`): un ESCALATE de R13, R14 o R15 siempre impide `pay`. Sólo es neutral el `skipped` de
  esas tres. Revisé cada `skipped`:
  - R13 sin cuenta → R1 escala.
  - R13 con una cuenta de esquema desconocido → si difiere de la registrada, R4 escala; si el proveedor no está
    registrado, R3 escala.
  - R14 sin nombre → R1 escala.
  - R15 sin beneficiario → R3 escala.
  - R15 con un dominio ajeno no parecido → la cuenta es la registrada, así que no hay nada que verificar.

  Ninguno de esos `skipped` es lo único que deja pasar un pago.
- **Aprobación humana**: R13–R15 escalan (nunca retienen). Una persona puede aprobar, como pide el brief, y R12 y el
  auditor siguen aplicando a lo que aprueba.
- **Auditor**: recalcula R13–R15 por su cuenta (validadores, lista y dominios, sin importar las reglas). Los mutantes
  R13, R14 y R15 de `test_audit.py` lo prueban saboteando la regla (R15 junto con R4).
- **Todas las vías** (API, firewall, MCP, onboarding y simulador) pasan por `decide_all`. Ninguna evalúa reglas por
  otro camino.
- **Determinismo (§3)**: la copia OFAC se lee e indexa una vez por proceso (`@cache` y el índice en `__post_init__`).
  Misma entrada, misma salida.

### Falsos positivos y negativos de OFAC (medido contra la copia del 15-10-2026, 19.457 entradas)

| Nombre | Resultado |
| --- | --- |
| José Pérez · Jose Perez · María Fernanda López · Juan Carlos Rodríguez · Pedro Gómez · García García | sin coincidencia |
| Distribuidora Andina S.A.S. · Café Ñandú LTDA · Comercializadora del Pacífico S.A. de C.V. · Banco de Bogotá · Global Trading LLC · Andes Code · Joaquín Méndez | sin coincidencia |
| Banco Nacional de Cuba · `bánco nacionál de cúba` · BANCO NACIONAL DE CUBA | 1,00 (acentos y mayúsculas se pliegan bien) |
| Banco Nacional de **K**uba | 0,944 (un error de letra se atrapa) |
| Petróleos de Venezuela S.A. · Jong Un Kim · Cartel de Sinaloa · Al-Qa'ida | 1,00 (sufijo, orden y puntuación neutralizados) |
| Mohammed Ali | 0,958 contra «MOHAMMED, Wali»: **falso positivo** esperable con nombres comunes; escala y no retiene, así que el costo es una revisión humana |

No bloquean, pero quedan anotados:

- **Palabras de más evaden la coincidencia** (`custodio/engine/sanctions.py:149`): el puntaje es el mínimo de los dos
  sentidos. Por eso «Industrias Rosneft» no coincide con «ROSNEFT» (y lo mismo «Hamas Charity …»). Sugerencia para un
  carril futuro: avisar también cuando todas las palabras de una entrada de 2 o más palabras están en el nombre leído.
- **Dos ediciones en una palabra** quedan fuera del índice por borrado de una letra (`sanctions.py:188`). En la práctica
  esos casos ya quedan bajo el umbral: «Hezbollah» frente a «HIZBALLAH» da Jaro-Winkler 0,82.
- **Nombres sin letras latinas** (cirílico, árabe, CJK): `name_tokens` (`custodio/engine/text.py:43`) los deja vacíos y
  R14 queda `skipped` neutral. Como OFAC publica en caracteres latinos, un proveedor registrado con nombre no latino no
  se revisa. Habría que transliterar.
- **R15 y el remitente**: `sender_email` es el primer correo del texto del documento (`custodio/extraction/__init__.py:117`),
  no la cabecera del correo, y el regex es ASCII (`custodio/engine/domains.py:14`). Un defraudador puede poner primero
  el correo legítimo, y un homóglifo Unicode no se detecta. No abre un pago porque el cambio de cuenta lo sigue escalando
  R4 y R15 lo escala por su cuenta; sólo debilita la detección de dominios parecidos. El informe del carril ya lo dice.

### Tests, código e idioma

- Los tests prueban comportamiento (vectores conocidos de CLABE, IBAN, NIT, CPF y CNPJ; lista ficticia marcada como tal;
  mutantes del auditor; propiedad de Hypothesis). El TDD es visible: cada bloque tiene su commit rojo antes del verde.
- El código está en inglés y los textos de producto en español. Las funciones son cortas y los errores tipados. No vi
  código muerto.
- Autoría: los 23 commits de `origin/main..HEAD` son de «Juan David Leon <271861486+davidleonb27@users.noreply.github.com>»,
  sin trailers ni menciones a IA.

## Compuerta y cifras

`./scripts/check.sh` final (después del rebase y los arreglos):

```
== api: lint, format, types, tests
All checks passed!
173 files already formatted
Success: no issues found in 96 source files
985 passed, 22 skipped in 76.24s
== web: API schema, lint, types, tests, build
schema.gen.ts coincide con la API.
 Test Files  17 passed (17)
      Tests  89 passed (89)
✓ Compiled successfully
== gate passed
```

- Dorado: `uv run pytest -q tests/dataset/test_golden.py tests/dataset/test_payment_controls.py` → `48 passed`. La
  exactitud sigue en 1,0 y hay 0 pagos indebidos con 38 facturas.
- Estrés: `uv run python scripts/stress.py --companies 1000 --seed 7` → `invoices: 25139`,
  `payments_checked_by_auditor: 8136`, `improper_payments: 0`, `auditor_vetoes: 0`, `reserve_breaches: 0`,
  `traps_paid_by_agent: {}`, en 44,3 s.

## Lo que no pude verificar

- Lectura con el modelo real y métricas en producción: **NO MEDIDO**, igual que en el informe del carril. Hay que
  repetir `scripts/measure_reading.py` porque los documentos de la demo cambiaron.
- No volví a descargar la copia OFAC (`scripts/update_ofac.py`). Usé la que viene en la rama.
- El tiempo de carga del índice OFAC en Vercel. En local tardó 2,5 s la primera vez.
- Los textos de la web que aún dicen «doce reglas» y el modo mock con 12 reglas siguen pendientes para el carril de la
  web, como dice el informe.
