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

## Qué NO se midió

- Lectura de facturas reales o escaneadas: NO MEDIDO.
- Variación entre corridas (se corrió una vez): NO MEDIDO.
- Latencia de la lectura: NO MEDIDO.
- Resto de campos (NIT, número, fechas, banco, descripción) en producción: NO MEDIDO.
