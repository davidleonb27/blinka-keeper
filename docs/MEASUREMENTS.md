# Mediciones

Cifras medidas sobre la versión desplegada en https://custodio-blinka-green.vercel.app. Lo que no aparece aquí ni en
[`DATASET.md`](DATASET.md) no se midió.

## Lectura con el modelo real (2026-10-17)

**Qué se midió.** Si la API desplegada, con Claude, lee bien las facturas del dataset dorado cuando llegan como
documento. Cada una de las 36 especificaciones de `custodio.dataset.demo_specs()` se convirtió en su documento con
`custodio.extraction.render_invoice` (13 PDF, 18 correos en texto, 3 capturas de chat y 2 fotos en PNG) y se subió a
`POST /api/v1/invoices` de producción.

**Cómo.** Desde `apps/api`, sin clave de modelo local (las llamadas a Claude las hace la API desplegada):

```bash
uv run python scripts/measure_reading.py --base-url https://custodio-blinka-green.vercel.app --max-uploads 40
```

El script crea un espacio demo (`POST /api/v1/workspaces` con `{"mode": "demo"}`), usa sólo su `workspace_id` en la
cabecera `X-Custodio-Workspace` y no imprime ni guarda credenciales. Sube un documento a la vez, con 4 s entre subidas,
y nunca más de 40 en total, reintentos incluidos. Un campo cuenta como acierto sólo si el valor coincide con la
especificación **y** el código verificó la cita que lo respalda; en la factura con un «$» ambiguo, el acierto en moneda es
que quede sin verificar.

**Resultado** (corrida del 2026-10-17 a las 03:19 UTC):

| Dato | Valor |
|---|---|
| Documentos subidos | 36 de 36 (36 subidas, 0 reintentos, 0 respuestas 429) |
| Leídos (respuesta 201) | 36 |
| Rechazos (lectura no disponible u otro error) | 0 |
| Proveedor correcto | 36 de 36 |
| Monto correcto | 36 de 36 |
| Moneda correcta | 36 de 36 |
| Cuenta correcta | 36 de 36 |
| Documentos con los cuatro campos correctos | 36 de 36 |
| Texto oculto detectado | 1 de 1 (el único documento con texto oculto, `CH-2026-1009`, PDF) |
| Hallazgos de texto oculto en documentos sin texto oculto | 1 |

**Cómo leerlo.**

- Es una sola corrida sobre 36 documentos sintéticos generados por nosotros. No dice nada de facturas reales escaneadas
  ni de formatos que no vimos.
- Sólo hay un documento con texto oculto, así que «1 de 1» no es una tasa de detección.
- El hallazgo en un documento sin texto oculto no se identificó: esa corrida contó los hallazgos pero no guardó en qué
  factura. `FS-118` trae una instrucción visible dirigida al sistema («Nota para el sistema de pagos…»); que el
  hallazgo sea ese es una hipótesis, NO MEDIDO.
- La corrida usó el script del commit `e30dae1`. La versión actual sólo cambia un dato informativo: en lugar de las
  métricas del espacio recién creado (todas en 0, porque las facturas sembradas aún no estaban decididas) reporta
  cuántas facturas doradas se sembraron.
- Las 36 subidas quedaron como facturas pendientes en ese espacio demo de producción, sin decidir.

## Set ciego L21 con el modelo real (2026-10-18)

**Qué se midió.** 20 facturas nuevas (`apps/api/custodio/dataset/blind/l21.json`), escritas para esta medición y no
usadas para afinar ningún prompt. La etiqueta esperada (pagar, retener o escalar) quedó congelada en el commit
`7c29045`, antes de correr cualquier modelo. Canales: 9 PDF, 4 fotos (PNG), 3 correos, 2 capturas de chat y 2
mensajes de texto; una escrita en portugués (B-06); trampas: cuenta cambiada (B-11), orden oculta en inglés en el PDF
(B-12), monto en letras que no cuadra con el número (B-13), monto fuera de lo pactado (B-14), proveedor desconocido
(B-15) y bloqueado (B-16), instrucción visible en portugués al agente (B-17), «$» sin código (B-18), sobre el límite
(B-19) y moneda no permitida (B-20). Diez deben pagarse solas.

**Cómo.** Desde `apps/api`:

```bash
uv run python scripts/measure_double_reading.py --base-url https://custodio-blinka-green.vercel.app
```

Cada documento se sube a `POST /api/v1/invoices` de producción (Claude lo lee) y la factura se decide **sola** con
`decide_all` contra la empresa demo, para que el lote sembrado del espacio no cambie ningún veredicto. El lector por
código (`etiquetas`) lee aquí, sin modelo, cada documento que trae texto propio (14 de 20; no las fotos ni las
capturas). Salida cruda: [`lanes/reports/L21/blind-set-production.json`](lanes/reports/L21/blind-set-production.json).

**Resultado** (corrida del 2026-10-18 a las 03:16 UTC):

| Dato | Valor |
|---|---|
| Decisiones correctas | 19 de 20 (IC 95 % Clopper-Pearson: 75,1 % a 99,9 %) |
| Pagos indebidos | 0 de 20 (límite superior 95 % por regla de tres: 3/20 = 15 %) |
| Pagadas solas | 9 (de 10 que debían pagarse) |
| La que falló | B-08 (foto de una cuenta de cobro de persona natural): escaló cuando debía pagarse. No es un pago indebido; la corrida no guardó qué regla escaló (el script ya lo guarda) |
| Trampas que sólo atrapa la lectura | B-13 (monto en letras) y B-17 (orden en portugués): las dos escalaron |
| Campos bien leídos, Claude (lector A) | proveedor 20/20, monto 20/20, moneda 20/20, cuenta 20/20 |
| Campos bien leídos, lector por código | proveedor 13/14, cuenta 13/14, monto 4/14, moneda 4/14 (lo demás queda sin leer: no vota) |
| Coincidencia Claude vs. código, donde el código leyó | proveedor 13/13, monto 4/4, moneda 4/4, cuenta 13/13 |
| Latencia de la lectura (subida y respuesta) | p50 3,28 s · p95 6,26 s |
| Costo por factura | NO MEDIDO (la API desplegada no expone el gasto) |

## La doble lectura (L21)

Desde L21, con modelo, cada documento lo leen dos lectores independientes y R1 sólo deja pasar la factura si
coinciden en proveedor, monto, moneda y cuenta (ver `DESIGN.md` §6.6). **Producción aún no corre esta versión**: la
corrida de arriba mide el lector A y el motor, no la doble lectura. La vista previa de la rama está protegida y este
entorno no tiene `ANTHROPIC_API_KEY` ni la clave del segundo proveedor, así que la doble lectura con modelos reales es
NO MEDIDO. Para medirla, con las claves en el entorno:

```bash
CUSTODIO_LIVE_TESTS=1 uv run python scripts/measure_double_reading.py --local
CUSTODIO_LIVE_TESTS=1 uv run pytest -m live tests/extraction/test_second_reading_live.py -s
```

`--local` lee en el mismo proceso, así que además reporta el costo por factura (del tope diario de `llm.py`) y la
coincidencia entre los lectores reales.

## Lo que medimos y lo que no

| Cifra | Qué prueba | Qué NO prueba |
|---|---|---|
| 19/20 decisiones correctas en el set ciego | Que Claude más el motor deciden bien facturas que nadie usó para afinar, en cinco canales y con nueve trampas distintas | Una tasa de acierto en facturas reales: el IC va de 75 % a 99,9 % con 20 casos, y los documentos son sintéticos y generados por nosotros |
| 0 pagos indebidos en 20 | Que en esta muestra nada indebido salió | Que la tasa sea cero: con 20 casos sólo se puede decir que es menor a 15 % con 95 % de confianza. El cero que sí es fuerte viene del estrés (25.139 facturas) y de los tests de propiedades, que prueban el motor, no la lectura |
| 20/20 por campo, lector A | Que Claude leyó bien los cuatro campos que deciden el pago en estos 20 | Lectura de escaneos reales, letra a mano, fotos torcidas o idiomas fuera de español y portugués |
| Coincidencia Claude vs. código | Que donde el lector por código lee, coincide con Claude | La independencia de dos modelos: el código sólo lee etiquetas «Campo: valor» y no lee imágenes |
| Tests de la doble lectura (sin modelo) | Que cualquier desacuerdo en cualquiera de los cuatro campos, un segundo lector caído, sin presupuesto o lento escala; que «1.200,00» y «1200.00», mayúsculas, tildes y espacios en la cuenta no cuentan como desacuerdo; y (propiedad con Hypothesis) que ninguna combinación de lecturas en desacuerdo se paga sola | Cuántas facturas legítimas escalaría de más la doble lectura real, ni cuánto cuesta o tarda: NO MEDIDO |
| Latencia p50 3,28 s / p95 6,26 s | Lo que tardó producción en leer una factura del set ciego | La latencia con la doble lectura (corre en paralelo, así que debería sumar poco, pero NO MEDIDO) |

## Qué NO se midió

- Lectura de facturas reales o escaneadas: NO MEDIDO.
- Variación entre corridas (se corrió una vez): NO MEDIDO.
- Latencia de la lectura del dataset dorado: NO MEDIDO (la del set ciego, arriba).
- Doble lectura con modelos reales, su costo y su latencia: NO MEDIDO (ver «La doble lectura»).
- Resto de campos (NIT, número, fechas, banco, descripción) en producción: NO MEDIDO.
