# Revisión L18c (PR #23, rama `fix/L18c`)

**Veredicto: LISTO PARA MERGE**

## Compuerta

`./scripts/check.sh` sobre `e68db35`: **gate passed**. API `1202 passed, 23 skipped`; web `vitest 183 passed (32 files)`,
eslint, tsc, `check:api` y `next build`. El dorado y la prueba de estrés (`test_golden.py`, `test_stress.py`) dan
`43 passed`, con `improper_payments == 0`. El PR no toca el motor: en la API solo cambia la regex de huecos de
`ai/profile.py`, que nunca llega a una decisión.

## Hallazgos

1. **Reutilizar un espacio blank sin usar** (`apps/web/src/lib/api/hooks.ts:214`): correcto.
   - Aislamiento: `getWorkspace()` lee solo el espacio cuya credencial ya tiene el navegador. No hay forma de nombrar
     el espacio de otro.
   - Exige `mode === "blank"` y `policy_version === 1`, y toda modificación de la política (onboarding, proveedores)
     crea una versión nueva. También exige `metrics.total === 0` (decididas) y `pending_invoices === 0` (sin decidir),
     así que un espacio con facturas no se reutiliza.
   - Si el resumen falla, crea un espacio nuevo.
2. **CSV** (`decisions-csv.ts:25`): toma el id del riel; si no hay, la `idempotency_key`; si tampoco, «—». Nunca queda
   vacío. Bien probado.
3. **Reglas** (`onboarding/state.ts:119`): una sugerencia del perfil que nadie tocó se reemplaza al cambiar de moneda.
   Un texto editado se conserva. Bien.
4. **Faltaba en el e2e «agregar el faltante»** (`e2e/colombia.e2e.ts`). Arreglado: desde el acta de TN-77 se sigue
   «Agregar proveedores», se agrega a mano y se exige que quede en COP en la política. Después se exporta.
5. **e2e intermitente (previo al PR)** (`apps/api/tests/e2e_app.py`). `empresa.e2e` falló 2 de 7 veces en
   `tokio-oscuro`: la vista previa del CSV no aparecía.
   - Causa: todos los navegadores del e2e llaman desde 127.0.0.1, y el tope de 20 llamadas al modelo por minuto e IP
     (ventana fija) los suma.
   - En `rate_counters`, las corridas fallidas llegaron a 20 en una ventana. Las de la base, sin cambios, a 18-19.
   - Arreglado: el e2e sube el tope por IP. El tope por espacio se mantiene.

## Arreglos (commits nuevos, sin rebase)

- `6e94ad8` test: el e2e de la API sube el tope por IP de llamadas al modelo.
- `e68db35` e2e: la empresa colombiana agrega el proveedor que R3 detuvo, en COP, antes de exportar.

## Flujo en Chromium (API real local, 1440 y 390 px)

Tres corridas completas seguidas: **32 passed** cada una, sin errores de consola (`watch(page)`). El flujo de
`colombia.e2e.ts` cubre:
- base COP y la plantilla sin «moneda», con una recarga a mitad del onboarding y un solo `POST /workspaces`;
- FV-1001 de Papelería Central SAS (COP 450.000), decidida por reglas, con R6 en `pass`;
- un proveedor no registrado (TN-77), detenido en R3;
- agregar el faltante en COP;
- exportar el CSV con `id_transferencia` no vacío.

## Qué no verifiqué

El flujo contra producción y contra el preview de Vercel. Tampoco «[monto]» con el modelo real.
