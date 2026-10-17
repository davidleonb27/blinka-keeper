# Revisión de L17 · Blindaje de la demo y usabilidad

Rama `lane/L17-ux`, PR #20. Revisión hecha en una sesión distinta de la que escribió el carril, siguiendo
`docs/lanes/REVIEW.md`.

## Veredicto: LISTO PARA MERGE

Esto vale con los cuatro commits de arreglo de esta revisión. El PR tal como llegó (`16f5219`) tenía un bloqueante: el
registro encadenado todavía devolvía 500 en Postgres cuando llegaban varias escrituras a la vez.

## Compuerta

- Al llegar (`16f5219`): `./scripts/check.sh` → **gate passed**. API `1181 passed, 23 skipped`; web `155 passed
  (26 archivos)`, build OK.
- Al terminar (`cf07583`): **gate passed**. API `1183 passed, 23 skipped`; web `155 passed (26 archivos)`, build OK.
- Postgres 16 local, `CUSTODIO_TEST_POSTGRES_URL=… pytest tests/api`: **151 passed, 2 skipped**. Los tests de
  concurrencia, límites y reto se corrieron tres veces más sobre el código final: 18/18 cada vez.
- `npm run e2e` (Chromium escritorio es-CO y Pixel 7 Tokio oscuro): **26 passed**.
- Motor, dorado y estrés (`tests/engine`, `tests/dataset/test_golden.py`): **451 passed**, con 0 pagos indebidos en el
  dorado y en la prueba de estrés. El diff no toca `custodio/engine`, `contracts.py` ni el dataset.

## Hallazgos

### 1. Bloqueante, arreglado: el reintento del registro se agotaba bajo carga real en Postgres

`apps/api/custodio/services/ledger_service.py:30`. El reintento con savepoint (5 intentos) está bien para dos
escritores. Con ocho subidas simultáneas al mismo espacio (`POST /api/v1/invoices`), un escritor puede perder la
carrera más de cinco veces seguidas. En Postgres eso daba `UniqueViolation` en `uq_ledger_entries_workspace_id_seq` y
un 500 en entre 4 y 7 de las 24 peticiones de cada corrida. Con 60 intentos pasaba, así que era inanición del
reintento y no un error de lógica. En SQLite no se reproducía, porque SQLite ya serializa a los escritores.

El test del autor sí ejerce la concurrencia: dos sesiones reales, la segunda lee la cabeza vieja y queda bloqueada en el
insert. Pero sólo cubre a dos escritores.

**Arreglo:**

- Test rojo `d428091`: ocho hilos suben 3 facturas cada uno por HTTP. El test exige cero errores, que los 24 asientos
  estén en la cadena, `seq` contiguos y que la cadena verifique.
- Arreglo `8299105`: en Postgres, `append` toma `pg_advisory_xact_lock(hashtextextended('ledger:<espacio>', 0))`
  antes de leer la cabeza. Los escritores de un mismo espacio se turnan hasta confirmar, y los de otros espacios no se
  esperan entre sí. El reintento con savepoint se queda como el camino de SQLite.
- El test del autor se ajustó: en Postgres el segundo escritor espera el candado antes de leer la cabeza, así que ya no
  puede leer una cabeza vieja. En SQLite se sigue exigiendo la lectura vieja, para que siga ejerciendo el reintento.

### 2. Bloqueante, arreglado: los contadores de tasa fallaban o perdían golpes con peticiones simultáneas

`apps/api/custodio/services/rate_limits.py:36`. El código es anterior al carril, pero pega de frente con el objetivo de
blindar la demo: un salón del jurado sale por una sola IP, y el reto ahora deja 30 intentos por minuto. `_hit` hacía
leer, insertar o sumar, y escribir. Eso tenía dos fallos:

- (a) Dos peticiones en una ventana nueva chocaban en el insert. Daba `IntegrityError` y un 500 en cada cambio de
  minuto, tanto en SQLite como en Postgres.
- (b) En Postgres se perdían actualizaciones. De 40 golpes simultáneos sólo contaba 11, así que los topes (30/min por
  IP, 2000/día del reto) se podían saltar con ráfagas.

**Arreglo:** test rojo `9bbe756` (8 hilos × 5 golpes: cero errores y contador = 40). Arreglo `c45d125`: un único
`INSERT … ON CONFLICT DO UPDATE SET count = count + 1 RETURNING count`, con el dialecto de Postgres o de SQLite. Si el
conteo pasa el tope se lanza `RateLimited`. Como la sesión se deshace, un intento rechazado sigue sin contar, igual que
antes.

### 3. Menor, arreglado: el rótulo del muro no reconocía «Ningún …»

`apps/web/src/components/challenge/attempt-verdict.ts:29`. El patrón cubría «ninguna detectada» y «ninguno
detectado», pero no «Ningún ataque aparente» ni «No hay fraude». Así, un intento frenado podía seguir leyéndose como
inofensivo. Ahora el patrón incluye `ning[uú]n` y `no hay fraude`, y el test del muro suma ese caso (`cf07583`).

### Sin hallazgos

- **Topes.** `RateLimits` (`context.py:29-32`): Stripe 2000 por día UTC, 40 por espacio sin cambio, reto 30 por minuto
  por IP. El diff sólo cambia constantes y los tests las fijan.
- **Rótulo del muro.** `wallLabel` nombra las reglas en `hold` o `escalate` («Frenado por R2, R4 y R15») cuando el
  nombre del modelo dice que no hubo fraude o no hay nombre. Respeta `broke_through` y los pagos limpios. Se resuelve al
  mostrar, así que también corrige los intentos ya guardados. Se usa en el muro, el escenario y el resultado.
- **Invariantes (DESIGN §3).** Ningún camino nuevo paga con una regla de retención fallida. El candado y el upsert no
  cambian ninguna decisión.
- **Seguridad.** No hay secretos nuevos. El candado se toma por espacio, así que no mezcla espacios. Los contadores
  siguen guardando un resumen de la IP, nunca la dirección.
- **Contratos.** `contracts.py` y `schema.gen.ts` no cambian.
- **Idioma y autoría.** El código está en inglés y el producto en español. Ningún commit lleva atribuciones.

## UI con Playwright (Chromium, 1440 y 390 px, build de producción con la API de dobles)

| Comprobación | 1440 | 390 |
| --- | --- | --- |
| Panel inicial: «38 facturas recibidas…», un solo «Decidir las 38 facturas», sin «NO MEDIDO» ni «Autonomía 0 %» | ✓ | ✓ |
| Al decidir: «Decidiendo…» deshabilitado y barra con etapas | ✓ | ✓ |
| Después de decidir aparecen las métricas | ✓ | ✓ |
| El recorrido marca «Decidir», «Abrir un acta» (desde su enlace) y «Verificar el registro» | ✓ | ✓ |
| Autonomía: «Aún ningún proveedor se ganó un tope» y un solo «Simular 30 días» visible, como acción principal | ✓ | ✓ |
| Landing: «15 reglas», sin «12 reglas» ni «★» | ✓ | ✓ |
| Arena: «ataque contra defensa», sin «Claude contra Claude» | ✓ | ✓ |
| Sin scroll horizontal (landing, panel, autonomía) | ✓ | ✓ |
| Errores de consola / hidratación #418 | 0 / no | 0 / no |

## Qué no pude verificar

- No probé contra producción ni con modelos reales (`-m live`).
- No hice pruebas de carga de más de 8 escritores ni contra Neon o PgBouncer. El candado es `xact`, así que también
  funciona en modo de pool por transacción.
- No ejercí a mano los pasos «Ajustar una regla», «Conciliar el banco» ni «Intenta robarle» del recorrido en el
  navegador. Sus marcas salen de los mismos `onSuccess` de las mutaciones que sí comprobé.
