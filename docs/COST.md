# Costo por factura

Costo en modelos de la lectura de una factura, **medido** sobre el pipeline real: cada llamada al modelo de la corrida,
valorada con el uso de tokens que devolvió la API. Nada aquí es una estimación. Convención de
[`MEASUREMENTS.md`](MEASUREMENTS.md): lo que no aparece aquí no se midió.

## Lectura doble con los modelos reales (2026-10-20)

**Cifra para citar.** Leer una factura distinta cuesta **0,0124 USD** en modelos (media sobre los 58 documentos
distintos; mediana 0,0104 USD; p95 0,0237 USD). **100 facturas distintas: 1,24 USD.** La corrida completa de 100
lecturas costó 0,9714 USD porque 42 de ellas repitieron documentos ya leídos y el segundo lector las sirvió desde su
caché en memoria (ver «Cómo leerlo»).

**Qué mide.** El costo en USD de cada llamada al modelo que hace la lectura de una factura tal como está desplegada:

| Paso | Módulo | Modelo (`Settings`) |
|---|---|---|
| Primera lectura (texto y PDF con texto) | `custodio/extraction/structure.py` | `model_fast` = `claude-sonnet-5-5` |
| Transcripción de imágenes (PNG y PDF escaneado) | `custodio/extraction/vision.py` | `model_fast` = `claude-sonnet-5-5` |
| Segunda lectura independiente | `custodio/extraction/second_reading.py` | `model_second_reader` = `claude-opus-5-5` (sin `GEMINI_API_KEY`) |

Todas pasan por `custodio.llm.structured`, que devuelve `LLMResult` con modelo, tokens y `cost_usd`. El script
`apps/api/scripts/measure_cost.py` envuelve esa función, anota cada llamada y suma los `cost_usd` que el propio pipeline
calcula; no estima nada.

**Tabla de precios aplicada** (`custodio/llm.py`, `_PRICES`, USD por millón de tokens):

| Modelo | Entrada | Salida |
|---|---|---|
| `claude-opus-5-5` | 4,00 | 20,00 |
| `claude-sonnet-5-5` | 2,00 | 10,00 |
| `claude-haiku-5-5` | 0,10 | 0,50 |

Lecturas de caché a 0,1× el precio de entrada; escrituras de caché a 1,25× (función `_cost`). Las instrucciones estables
van en `system` con `cache_control`, así que desde la segunda factura la mayor parte del prompt se cobra como caché.

**Documentos.** 58 distintos: las 38 facturas doradas de `custodio.dataset.demo_specs()` (19 en texto, 14 PDF, 5 PNG) y
las 20 del set ciego L21 (`custodio/dataset/blind/l21.json`: 5 en texto, 9 PDF, 6 PNG). En total 24 en texto, 23 PDF y
11 PNG. El script los recorre en ciclo hasta completar 100 lecturas: las lecturas 1 a 58 son documentos distintos; las 59
a 100 repiten los primeros 42.

**Cómo.** Desde `apps/api`, con `ANTHROPIC_API_KEY` en el entorno (el script nunca la imprime):

```bash
uv run python scripts/measure_cost.py --dry-run                      # sólo renderiza: 58 documentos
uv run python scripts/measure_cost.py --max 100 --out cost-report.json
```

La corrida se hizo el 2026-10-20 desde un entorno de nube, con una clave de organización y el workspace fijado con la
cabecera `anthropic-workspace-id` a través de `ANTHROPIC_CUSTOM_HEADERS` (variable que lee el SDK). El tope diario
(`CUSTODIO_LLM_DAILY_BUDGET_USD`) se subió a 50 USD sólo en esa corrida; no hizo falta: gastó 0,97 USD. Salida cruda:
[`apps/api/cost-report.json`](../apps/api/cost-report.json); una línea por lectura (id, tipo, USD, segundos):
[`apps/api/cost-report.log`](../apps/api/cost-report.log).

**Resultado de la corrida** (100 lecturas, terminó el 2026-10-20 a las 03:10 UTC):

| Dato | Valor |
|---|---|
| Facturas leídas | 100 |
| Lecturas con error | 0 |
| Costo total de la corrida | 0,9714 USD |
| Costo por lectura, media | 0,0097 USD |
| Costo por lectura, mediana | 0,0099 USD |
| Costo por lectura, p95 | 0,0234 USD |
| Costo por lectura, máximo | 0,0244 USD |
| Proyección a 100 lecturas tal como se hicieron | 0,97 USD |
| Segundos por lectura, mediana | 3,40 s |
| Segundos por lectura, p95 | 7,16 s |

Por modelo (las 100 lecturas):

| Modelo | Llamadas | Tokens entrada | Tokens salida | Tokens de caché leídos | USD total | USD por lectura | USD por llamada |
|---|---|---|---|---|---|---|---|
| `claude-sonnet-5-5` (primera lectura) | 118 | 61.616 | 46.144 | 133.800 | 0,6114 | 0,0061 | 0,0052 |
| `claude-opus-5-5` (segunda lectura) | 58 | 31.023 | 10.679 | 55.680 | 0,3599 | 0,0036 | 0,0062 |

Por tipo de documento (las 100 lecturas):

| Tipo | Lecturas | USD media | USD máximo |
|---|---|---|---|
| Texto (`text/plain`) | 44 | 0,0077 | 0,0108 |
| PDF (`application/pdf`) | 38 | 0,0083 | 0,0109 |
| PNG (`image/png`) | 18 | 0,0176 | 0,0244 |

**Costo por factura distinta** (lecturas 1 a 58 de `cost-report.log`, cada documento leído por primera vez, con los dos
lectores llamando al modelo). Es la cifra que corresponde a facturas nuevas en producción:

| Dato | Valor |
|---|---|
| Facturas distintas | 58 |
| Costo total | 0,7186 USD |
| Costo por factura, media | 0,0124 USD |
| Costo por factura, mediana | 0,0104 USD |
| Costo por factura, p95 | 0,0237 USD |
| Costo por factura, máximo | 0,0244 USD |
| Proyección a 100 facturas distintas | 1,24 USD |
| Segundos por factura, mediana | 4,75 s |
| Segundos por factura, p95 | 7,50 s |

| Modelo | Llamadas | USD total | USD por factura distinta |
|---|---|---|---|
| `claude-sonnet-5-5` (primera lectura; dos llamadas por PNG) | 69 | 0,3587 | 0,0062 |
| `claude-opus-5-5` (segunda lectura) | 58 | 0,3599 | 0,0062 |

| Tipo | Facturas | USD media | USD máximo |
|---|---|---|---|
| Texto (`text/plain`) | 24 | 0,0099 | 0,0108 |
| PDF (`application/pdf`) | 23 | 0,0105 | 0,0109 |
| PNG (`image/png`) | 11 | 0,0218 | 0,0244 |

**Cómo leerlo.**

- El segundo lector guarda en memoria sus lecturas por hash del documento (`second_reading._Cache`, 64 entradas). En las
  lecturas 59 a 100 el documento ya estaba en caché, así que no hubo llamada a Opus: esas 42 lecturas costaron 0,0060 USD
  de media (sólo Sonnet). Por eso la media de la corrida (0,0097 USD) es menor que la de una factura distinta (0,0124 USD).
  En producción una factura nueva siempre paga los dos lectores.
- Las 58 llamadas a Opus de la corrida son exactamente las 58 primeras lecturas; su costo total (0,3599 USD) se reparte
  entre esas 58 facturas. El costo de Sonnet en la primera pasada es el total de la pasada menos el de Opus.
- Una imagen cuesta el doble que un texto o un PDF con texto porque hace dos llamadas al primer lector: la transcripción
  (`vision.transcribe`) y después la lectura de campos (`structure.read_fields`); de ahí las 118 llamadas a Sonnet
  (100 lecturas + 18 PNG).
- La caché de prompt funciona: de los tokens de entrada, la mayoría se cobró como lectura de caché (133.800 frente a
  61.616 frescos en Sonnet; 55.680 frente a 31.023 en Opus). Los tokens de entrada reportados no incluyen las escrituras
  de caché, pero su costo sí está dentro de `cost_usd`.
- Los precios son los de la tabla `_PRICES` del repo, no una factura de Anthropic. Si la tabla queda desactualizada, la
  cifra real se mueve en la misma proporción.
- Es una sola corrida sobre documentos sintéticos cortos (una página). Facturas reales más largas o escaneadas con ruido
  tendrán más tokens de entrada y costarán más; esa cifra está NO MEDIDA.
- Los segundos se midieron desde la máquina de la corrida hasta la API, con el segundo lector corriendo en paralelo al
  primero; no incluyen la cola ni la red del despliegue en Vercel.

**Qué NO mide.** La compilación de reglas, el red team, la conciliación de PDF y la narración, que son llamadas aparte y no
forman parte de la lectura de una factura.
