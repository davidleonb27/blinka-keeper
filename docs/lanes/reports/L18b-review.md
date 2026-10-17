# Revisión L18b · «Usar con mi empresa» para una empresa colombiana

Rama `fix/L18b-empresa-real` (PR #22), revisada sobre `e732d3e`. Veredicto: **LISTO PARA MERGE**.

## Compuerta

`./scripts/check.sh`: **gate passed**. API `1198 passed, 23 skipped`; web `check:api` al día, eslint, tsc,
`vitest 179 passed (32 files)`, `next build`.

## 1. El motor no cambia

- El diff no toca `apps/api/custodio/engine` ni `contracts.py`.
- `pytest -k "golden or stress or dorado or estres"`: 45 passed. Entre ellos `tests/dataset/test_golden.py` y
  `tests/engine/test_stress.py`, que exigen 0 pagos indebidos.
- `onboarding_service.complete` sólo cambia de dónde sale la moneda base (de la política elegida y no del perfil
  propuesto). `policy_service.apply` la sigue validando.

## 2. Ningún error de validación del onboarding termina en 500

Lo probé contra la API local (`tests.e2e_app`) y contra el lector real `custodio.ai.suppliers`.

| Entrada | Respuesta |
|---|---|
| Plantilla con «moneda» vacía, con y sin `currency` | 200, COP (o la moneda base del espacio) |
| CSV sin columna «moneda» | 200, en la moneda enviada |
| Faltan columnas · archivo vacío · CSV binario · XLSX dañado (lector real) | 422 `unreadable_supplier_file` |
| PNG (lector real) | 415 `unsupported_supplier_file` |
| `currency` que no es un código de tres letras · falta el archivo | 422 `invalid_request` |
| `complete` con moneda base fuera de las permitidas | 422 `policy_invalid` |
| `complete` con proveedores incompletos | 422 `invalid_request` |
| `complete` con perfil en USD y política en COP | 200, el espacio queda en COP |

Hallazgo: con un CSV que no está en UTF-8, el doble de prueba `tests/api/doubles.py:519` (`import_suppliers`, sólo
para e2e) daba 500. El lector real no falla: usa latin-1 y responde 422. **Arreglado** en `test: the e2e supplier
double reads a non-UTF-8 file…`.

## 3. Flujo con Playwright (Chromium de `/opt/pw-browsers`, API real local)

`colombia.e2e.ts`: 2/2 pasan en `bogota` (1440 px) y 2/2 en `tokio-oscuro` (390 px). Cero errores de consola y cero
respuestas ≥ 400 (`watch`):

- `/empezar` con país CO y base COP. Las reglas se prellenan sin «[». La plantilla se lee sin «moneda» y Papelería
  Central SAS queda en COP. Se hace **un solo** `POST /workspaces` y el registro guarda el país CO.
- FV-1001 de Papelería Central SAS (NIT 900123456-1, COP 450.000, Bancolombia 123-456789-01) queda `paid_auto` o
  `pending_approval`. R8 no la retiene.
- Una factura de Tintas del Norte SAS (no registrado) no se paga. Hallazgo: el test sólo exigía «no pagada».
  **Reforzado**: ahora exige que R3 dé `escalate`, es decir, que la detenga R3 (`e2e: an unregistered supplier's
  invoice is stopped by R3…`).
- `/proveedores` sin onboarding muestra el aviso de demo con el enlace a `/empezar`.

## 4. Los dos `<main>` con `cacheComponents`

Lo verifiqué con una prueba temporal, que no quedó en el repositorio, en los dos proyectos:

- El DOM tiene dos `<main>`. El segundo es el de la landing, dentro de un `DIV` con `display: none`, y
  `checkVisibility()` da `false`.
- El snapshot de accesibilidad de `body` tiene **un solo** `main` y no contiene el texto de la landing.

La explicación del reporte es correcta.

## Otros hallazgos (no bloqueantes, sin cambios)

- `apps/web/src/lib/api/workspace.ts`: la marca `freshBlank` vive en memoria. Si alguien recarga `/empezar` antes de
  terminar, el onboarding crea otro espacio en blanco y deja uno vacío. Tampoco hay salto de vuelta a la demo: quien
  llega a `/empezar` y lo abandona queda en un espacio en blanco vacío.
- Comportamiento previo a este PR: `/onboarding/complete` acepta `opening_balance` negativo y `fx_units_per_base` con
  0 o sin la moneda base. No da 500 en el onboarding, pero merece validarse en otro carril.
- Commits con la identidad del proyecto y sin atribuciones. Código en inglés, textos de producto en español.

## No verificado

- El preview de Vercel.
- La importación de PDF con el modelo real (el e2e usa dobles).
- La suite e2e completa: sólo corrí `colombia.e2e.ts`; el autor reporta 32 passed.
