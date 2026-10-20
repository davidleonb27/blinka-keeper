# Costo por factura

Costo en modelos de la lectura de una factura, **medido** sobre el pipeline real (no estimado). Lo que no aparece aquí
no se midió. Convención de [`MEASUREMENTS.md`](MEASUREMENTS.md): una cifra sin corrida detrás dice NO MEDIDO.

## Lectura doble con los modelos reales (2026-10-20)

**Estado: NO MEDIDO.** La corrida no se hizo: en el entorno de nube donde se preparó esta medición no existe la variable
`ANTHROPIC_API_KEY` (hay otra clave de Anthropic bajo otro nombre, de otro proyecto, y no se usó). El script quedó listo
y probado en seco; las tablas de abajo se llenan con la salida de `apps/api/cost-report.json` en cuanto se corra.

**Qué mide.** El costo en USD de cada llamada al modelo que hace la lectura de una factura tal como está desplegada:

| Paso | Módulo | Modelo (`Settings`) |
|---|---|---|
| Primera lectura (texto) | `custodio/extraction/structure.py` | `model_fast` = `claude-sonnet-5-5` |
| Primera lectura (PDF escaneado y PNG) | `custodio/extraction/vision.py` | `model_fast` = `claude-sonnet-5-5` |
| Segunda lectura independiente | `custodio/extraction/second_reading.py` | `model_second_reader` = `claude-opus-5-5` (sin `GEMINI_API_KEY`) |

Todas pasan por `custodio.llm.structured`, que devuelve `LLMResult` con modelo, tokens y `cost_usd`. El script no estima
nada: suma los `cost_usd` que el propio pipeline calcula a partir del uso de tokens que devuelve la API.

**Tabla de precios aplicada** (`custodio/llm.py`, `_PRICES`, USD por millón de tokens):

| Modelo | Entrada | Salida |
|---|---|---|
| `claude-opus-5-5` | 4,00 | 20,00 |
| `claude-sonnet-5-5` | 2,00 | 10,00 |
| `claude-haiku-5-5` | 0,10 | 0,50 |

Lecturas de caché a 0,1× el precio de entrada; escrituras de caché a 1,25× (función `_cost`). Las instrucciones estables
van en `system` con `cache_control`, así que a partir de la segunda factura la mayor parte del prompt se cobra como caché.

**Documentos.** 58 documentos distintos: las 38 facturas doradas de `custodio.dataset.demo_specs()` (19 en texto, 14 PDF,
5 PNG) y las 20 del set ciego L21 (`custodio/dataset/blind/l21.json`: 5 en texto, 9 PDF, 6 PNG). En total 24 en texto,
23 PDF y 11 PNG. Se recorren en ciclo hasta completar 100 lecturas (cada documento se lee una o dos veces).

**Cómo.** Desde `apps/api`, con `ANTHROPIC_API_KEY` en el entorno (nunca se imprime):

```bash
uv run python scripts/measure_cost.py --dry-run                      # sólo renderiza: 58 documentos
uv run python scripts/measure_cost.py --max 100 --out cost-report.json
```

Si el tope diario (`CUSTODIO_LLM_DAILY_BUDGET_USD`, 25 USD por defecto) corta antes de las 100, se sube sólo en esa
variable de entorno para la corrida.

**Resultado** (pendiente de corrida):

| Dato | Valor |
|---|---|
| Facturas leídas | NO MEDIDO |
| Lecturas con error | NO MEDIDO |
| Costo total de la corrida | NO MEDIDO |
| Costo por factura, media | NO MEDIDO |
| Costo por factura, mediana | NO MEDIDO |
| Costo por factura, p95 | NO MEDIDO |
| Costo por factura, máximo | NO MEDIDO |
| Proyección a 100 facturas | NO MEDIDO |
| Segundos por factura, mediana | NO MEDIDO |
| Segundos por factura, p95 | NO MEDIDO |

Por modelo:

| Modelo | Llamadas | Tokens entrada | Tokens salida | Tokens de caché leídos | USD total | USD por factura |
|---|---|---|---|---|---|---|
| `claude-sonnet-5-5` (primera lectura) | NO MEDIDO | NO MEDIDO | NO MEDIDO | NO MEDIDO | NO MEDIDO | NO MEDIDO |
| `claude-opus-5-5` (segunda lectura) | NO MEDIDO | NO MEDIDO | NO MEDIDO | NO MEDIDO | NO MEDIDO | NO MEDIDO |

Por tipo de documento:

| Tipo | Facturas | USD media | USD máximo |
|---|---|---|---|
| Texto (`text/plain`) | NO MEDIDO | NO MEDIDO | NO MEDIDO |
| PDF (`application/pdf`) | NO MEDIDO | NO MEDIDO | NO MEDIDO |
| PNG (`image/png`) | NO MEDIDO | NO MEDIDO | NO MEDIDO |

**Qué NO mide.** La compilación de reglas, el red team, la conciliación de PDF y la narración, que son llamadas aparte y no
forman parte de la lectura de una factura.
