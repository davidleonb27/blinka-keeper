# Revisión de L18 · «Usar con mi empresa» (PR #21)

**Veredicto: LISTO PARA MERGE** (con los arreglos de abajo ya en la rama).

## Compuerta

- Inicial (`8d8d4ba`): API `1180 passed, 23 skipped`, ruff y mypy limpios. La parte web se cortó en `check:api` porque
  cambié el OpenAPI (ruta nueva) mientras corría; no es un fallo del PR.
- Final (`75761f5`): **gate passed**. API `1185 passed, 23 skipped`; web `check:api` al día, eslint, tsc,
  `vitest: 166 passed (29 files)`, `next build`.
- Playwright (Chromium de `/opt/pw-browsers`, API real local `tests.e2e_app`): **28 passed**, cero errores de consola,
  excepciones o respuestas ≥ 400 (`e2e/problems.ts`).
- Dorado y prueba de estrés (`tests/dataset/test_golden.py`, `tests/engine/test_stress.py`): 43 passed, 0 pagos
  indebidos.

## Hallazgos y arreglos

1. **Bloqueante, arreglado. Inyección de fórmulas en el CSV exportado.**
   `apps/web/src/components/panel/decisions-csv.ts:8`: las celdas sólo se entrecomillaban. El proveedor y el número de
   factura salen de la lectura de un documento que controla quien lo envía, así que una factura con proveedor
   `=HYPERLINK(...)` se ejecutaba al abrir el CSV en Excel o Sheets. Ahora una celda de texto que empieza por
   `= + - @`, tabulador o retorno de carro lleva un `'` delante; los números (monto) no se tocan. Test primero
   (`68ef319`), arreglo después (`14b479c`).

2. **Riesgo medio, arreglado. «Sólo agregar» vivía sólo en la web.**
   `/proveedores` armaba la política completa en el navegador y la enviaba con `PUT /policy`:
   - la garantía de no tocar a los registrados dependía del cliente;
   - con una política vieja en caché, el `PUT` deshacía cualquier cambio hecho entretanto. Por ejemplo, volvía a subir
     un umbral que alguien había bajado.

   Nueva ruta `POST /api/v1/policy/beneficiaries` (`apps/api/custodio/api/routes/policy.py:39`,
   `policy_service.add_beneficiaries`, `apps/api/custodio/services/policy_service.py:36`):
   - parte de la política vigente en el servidor y sólo añade;
   - rechaza con 422 `policy_invalid` un proveedor que comparta id, identificación tributaria (normalizada como en
     `match_beneficiary`) o nombre/alias con uno registrado o con otro del mismo lote;
   - pide nombre e identificación no vacíos y admite como máximo 200 por llamada;
   - cada alta crea una versión nueva y su asiento `policy_changed`.

   Tests: `fd3fed3`, rojo antes de `1be4516`. Cubren el alta y que lo demás queda idéntico; los impostores (misma
   identificación con otro formato, mismo nombre, alias igual a un nombre registrado, mismo id) no cambian nada; un
   duplicado dentro del lote; que se conserve un cambio de política hecho entretanto; y el aislamiento entre espacios.
   La web usa ahora `addSuppliers` (live y mock) y se borró `withAdditions`, que quedó sin uso (`7a89ddc`).
   `planAdditions` sigue armando la vista previa.

   - Ningún camino de este carril cambia los datos bancarios de un registrado. Un cambio de cuenta sigue llegando en
     una factura y pasa por R4, R13 y R15.
   - `PUT /policy` sigue aceptando cualquier política válida del propio espacio. Es la vía existente de `/politica`, no
     la introduce este carril, y queda en el registro. Restringirla es una decisión de producto aparte.

3. **Subida de varios archivos: correcta.** El cliente valida antes de enviar:
   - 4 MB y la lista de extensiones;
   - `.eml` y `.txt` se mandan como texto;
   - envío en serie;
   - error legible por archivo.

   El servidor conserva sus guardias, que este carril no toca:
   - `MAX_DOCUMENT_BYTES` y el límite de cuerpo (`body_limit.py`);
   - validación de tipo en `invoice_service`;
   - `ModelCallLimit`;
   - espacio tomado de `CurrentWorkspace`.

   El e2e confirma el rechazo de `.xlsx` sin afectar a los demás archivos.

4. **E2E ampliado** (`75761f5`, `e2e/empresa.e2e.ts`). Además del flujo original, ahora:
   - sube dos facturas juntas, una de un proveedor registrado y otra no (`Decidir 2 facturas`);
   - el acta de la segunda enlaza a «Agregar proveedores»;
   - el proveedor se agrega por la ruta nueva;
   - una factura nueva del mismo proveedor ya sale con `beneficiary_id` y la anterior sigue sin pagar;
   - el CSV final la incluye.

   Corre a 1440 px (bogota) y 390 px (tokio-oscuro).

## Lo demás

- Invariantes de `DESIGN.md` §3: el motor, la reserva y las reglas no cambian; el lote se paga por el riel existente.
- `contracts.py` sin cambios. Se añadieron `invoice_number` en `DecisionItem` (del autor) y el cuerpo
  `NewBeneficiaries` (local a la ruta).
- Idioma y autoría correctos; commits con la identidad del proyecto.

## No verificado

- Lectura con modelos reales y tests `live`.
- Producción (Vercel).
- Cómo trata cada hoja de cálculo el `'` delante (Excel y Sheets lo ocultan; LibreOffice puede mostrarlo).
