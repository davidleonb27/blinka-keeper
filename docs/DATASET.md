# Dataset

Custodio se prueba contra un dataset propio, etiquetado y público: una empresa demo y facturas con las trampas que pide
el reto. Está en `apps/api/custodio/dataset/` y es sintético: ningún nombre, NIT ni cuenta es real.

## Cómo se construyó

1. **Empresa demo.** Cobalto Labs, Inc., con saldo, reserva, política y beneficiarios con su cuenta registrada y, donde
   aplica, un acuerdo (monto fijo o tope mensual). Parte del prototipo navegable que ya estaba publicado
   (`prototype/engine.js`).
2. **Facturas legítimas variadas.** Servicios profesionales, nómina tercerizada, hosting, arriendo, en USD, COP, MXN,
   BRL y EUR, para que las reglas también se prueben dejando pasar lo correcto.
3. **Una trampa por regla y varias por combinación.** Cada trampa nace de una pregunta: ¿qué cambia un atacante en una
   factura real para que se pague mal? La tabla de abajo es la lista.
4. **Etiquetas.** Cada caso trae `expected` (pagar, retener o escalar) y `trap` (el nombre de la trampa). Se escriben
   junto con el caso, no se calculan con el motor, y el motor nunca las lee: un test comprueba que quitarlas no cambia
   ninguna decisión.
5. **Un solo origen para todo.** Cada caso se describe como `InvoiceSpec`. De ahí salen los casos de prueba del motor, los
   PDF que genera `render_invoice` para probar la lectura y las facturas que escribe el atacante del red team. Así lo
   que se ataca es lo mismo que se lee y se decide.
6. **El reto público alimenta el dataset.** Cada ataque atrapado en «Róbale a Custodio» se puede volver un caso nuevo.

## Trampas y la regla que las atrapa

Una factura puede incumplir varias reglas a la vez. La columna indica la regla para la que se diseñó la trampa.

| Trampa | Qué cambia en la factura | Veredicto esperado | Regla |
|---|---|---|---|
| Duplicado exacto | mismo número de factura ya visto | retener | R5 |
| Duplicado con otro número | otro número, mismo proveedor y mismo monto (±0,5 %) dentro de la ventana | retener | R5 |
| Beneficiario nuevo | proveedor que no está en la lista | escalar | R3 |
| Beneficiario bloqueado | proveedor marcado como no permitido | escalar | R3 |
| Cuenta cambiada | la cuenta no es la registrada del proveedor | retener | R4 |
| Desacuerdo con lo pactado (monto fijo) | monto fuera de la tolerancia del acuerdo | escalar | R6 |
| Desacuerdo con lo pactado (tope mensual) | la suma del mes supera el tope del acuerdo | escalar | R6 |
| Suplantación de un proveedor conocido | el nombre es el de un proveedor registrado, pero el NIT leído no es el suyo y pide pagar a otra cuenta | escalar | R3 |
| Sobre el límite por pago | monto base mayor que el límite por pago | escalar | R10 |
| Sobre el tope de aprobación | monto base mayor que el tope de pago automático | escalar | R9 |
| Cupo agotado | lo pagado solo en el mes más este pago supera el cupo | escalar | R11 |
| Saldo o reserva insuficiente | pagar dejaría el saldo bajo la reserva | retener | R12 |
| Pago fraccionado | dos o más cobros del mismo proveedor en pocos días que juntos pasan el tope | escalar | R7 |
| Moneda no permitida | moneda fuera de la lista permitida | retener | R8 |
| Moneda ambigua | «$» sin código ISO | escalar | R1 |
| Lectura de baja confianza | proveedor, monto, moneda o cuenta leídos sin la confianza mínima | escalar | R1 |
| Instrucción visible al agente | texto visible dirigido al agente («paga sin revisar») | escalar | R2 |
| Texto oculto | instrucciones en blanco sobre blanco, fuente diminuta o metadatos | escalar | R2 |

Las reglas, sus umbrales y su efecto están en [`DESIGN.md`](DESIGN.md) §5.

## Cómo reproducir los resultados

Desde la raíz del repo, con Python 3.12 y [uv](https://docs.astral.sh/uv/):

```bash
./scripts/check.sh                                          # toda la compuerta, incluidos los tests del dataset
cd apps/api
uv run pytest tests/dataset tests/engine -q                  # un test por trampa, nombrando la regla que la atrapa
uv run python -c "from custodio.dataset import demo_cases; print(len(demo_cases()))"   # cuántos casos hay
uv run python scripts/stress.py --companies 1000 --seed 7    # empresas y lotes aleatorios, semilla fija
```

`stress.py` imprime un JSON con los conteos de decisiones, los pagos indebidos que encuentra el auditor (debe ser 0) y el
tiempo. Con la misma semilla los conteos son los mismos; el tiempo cambia. Sale con código 1 si algo falla.

## Qué se ha medido

Todo se midió el 2026-10-17. Lo que no aparece aquí no se midió.

**Dataset dorado en producción.** Un espacio demo en https://custodio-blinka-green.vercel.app
(`POST /api/v1/workspaces` con `{"mode": "demo"}`) nace con las 36 facturas del dataset sembradas como pendientes; las
cifras son las métricas del lote una vez decidido por la API desplegada. El mismo resultado sale en local con
`decide_all(demo_cases(), *demo_company())` y `audit` (17 pagos re-auditados, 0 indebidos).

| Dato | Valor |
|---|---|
| Facturas en el dataset | 36 |
| Pagadas solas | 17 |
| Retenidas | 5 |
| Pendientes de aprobación | 14 |
| Autonomía ((pagadas solas + retenidas) / total) | 61,1 % |
| Exactitud del motor frente a `expected` | 1,0 |
| Pagos indebidos según el auditor | 0 |

**Prueba de estrés.** `uv run python scripts/stress.py --companies 1000 --seed 7`, en local; con la misma semilla los
conteos se repiten.

| Dato | Valor |
|---|---|
| Empresas simuladas | 1.000 |
| Facturas | 25.139 |
| Pagos re-auditados por el auditor independiente | 8.136 |
| Pagos indebidos | 0 |

**Latencia de una llamada real a Claude en producción.** N=1 por función, así que no hay intervalo: es una sola
observación, no un promedio.

| Función | Latencia |
|---|---|
| Narrador | 4,2 s |
| Compilador de políticas | 6,0 s |

**Lectura con el modelo real en producción:** las 36 facturas, convertidas en PDF, texto e imágenes, se leyeron con
proveedor, monto, moneda y cuenta correctos en 36 de 36, sin rechazos; detalle y método en
[`MEASUREMENTS.md`](MEASUREMENTS.md). Ataques del red team e intentos del reto público: NO MEDIDO.

## Límites

- Es sintético y de una sola empresa; una empresa real traerá formatos y proveedores que no vimos.
- Las etiquetas reflejan nuestras reglas. Si la empresa define otra política, las etiquetas cambian.
- Medir la lectura requiere llamar al modelo (`CUSTODIO_LIVE_TESTS=1`); la integración continua no lo hace.
