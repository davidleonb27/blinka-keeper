# Caso de negocio

Regla de este documento: **cada cifra lleva su fuente enlazada; si no hay fuente, dice NO MEDIDO.** Las cifras de
Custodio salen del panel de la demo, no de este texto.

## El problema

Una empresa paga a sus proveedores con facturas que le llegan por correo, WhatsApp o PDF. El fraude más barato para el
atacante es una factura casi idéntica a la real con un dato cambiado, casi siempre la cuenta bancaria, o una factura
repetida. El FBI lo agrupa como compromiso de correo empresarial (BEC): una estafa contra empresas que trabajan con
proveedores o que hacen transferencias con regularidad
([definición, glosario del informe IC3 2025](https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf)).

### Lo que está medido

| Dato | Fuente |
|---|---|
| 24.768 denuncias de BEC en Estados Unidos en 2025, con pérdidas reportadas de US$ 3.046.598.558 | [FBI IC3, Informe anual 2025](https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf) |
| En 2024 fueron 21.442 denuncias y US$ 2.770.151.146 | [FBI IC3, Informe anual 2025](https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf) (tabla comparativa) |
| Más de US$ 30 millones perdidos en 2025 en BEC con inteligencia artificial confirmada | [FBI IC3, Informe anual 2025](https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf) |
| 74 % de las organizaciones sufrió BEC en 2025 y 76 % sufrió fraude de pagos, intentado o real (465 tesoreros encuestados en enero de 2026) | [AFP, comunicado del 14 de abril de 2026](https://www.financialprofessionals.org/about/learn-more/press-releases/Details/over-75-percent-of-us-firms-experienced-payments-fraud-in-2025-while-ai-adoption-for-fraud-mitigation-lags) |
| En banca digital de América Latina, los casos de ingeniería social crecieron 155 % y las cuentas mula reportadas 42 % (36 entidades, más de 300 millones de clientes) | [BioCatch, Informe 2026 de tendencias de fraude en banca digital en América Latina](https://www.biocatch.com/report-2026-digital-banking-fraud-trends-in-latin-america) |

Las denuncias del FBI son pérdidas reportadas, no el costo total, y son de Estados Unidos. La encuesta de la AFP es de
tesoreros, sobre todo estadounidenses. El dato de BioCatch es de fraude en banca digital, no de pagos a proveedores.

### Lo que no encontramos

- Una cifra medida de fraude por cambio de cuenta o facturas duplicadas en pymes de América Latina: NO MEDIDO. Los
  reportes regionales que encontramos miden fraude bancario y cuentas mula, no pagos entre empresas.
- La proporción de pymes latinoamericanas que paga a mano con una persona revisando facturas: NO MEDIDO.
- Cuántas pérdidas habría evitado Custodio en esas empresas: NO MEDIDO. Sólo podemos decir qué atrapa en el dataset
  ([`DATASET.md`](DATASET.md)), y eso se publica cuando el coordinador lo mide.

Por eso el argumento para América Latina es una hipótesis que hay que validar en pilotos, no un hecho medido: el patrón
de ataque es el mismo, los pagos en varias monedas y por canales como correo y WhatsApp lo facilitan, y la verificación
sigue siendo manual.

## Para quién

Una pyme que paga a proveedores desde una cuenta propia, con facturas que llegan por canales informales, con una o dos
personas que hoy revisan todo a mano y un dueño o gerente que aprueba lo grande. Cobalto Labs, la empresa demo, es ese
caso: una compañía con proveedores en varias monedas.

Segundo cliente: quien construye agentes que pagan (una fintech, un ERP, un asistente con herramientas). No quiere
escribir otro motor de reglas de pagos y necesita un freno que no dependa de lo que diga el modelo.

## Qué vendemos

1. **Custodio para cuentas por pagar.** La app: lectura de facturas, reglas en español, actas, aprobación por celular.
2. **Firewall de pagos para agentes.** API y servidor MCP. Un agente envía una intención de pago y recibe pagar,
   retener o escalar, con su acta y su hash en el registro.

## Modelo de ingresos

| Unidad | Quién paga | Estado |
|---|---|---|
| Por decisión del firewall | quien conecta un agente | hipótesis; precio NO MEDIDO |
| Por agente o espacio conectado | la empresa que lo usa | hipótesis; precio NO MEDIDO |
| Reto público «Róbale a Custodio» | nadie; es prueba pública y captación | en curso |

No publicamos precios porque no hemos medido dos cosas: el costo real por decisión (modelo, base de datos, hospedaje) y
cuánto está dispuesta a pagar una empresa. El costo se mide con el gasto estimado por llamada que registra `custodio.llm` durante la
semana del reto; el precio se averigua en entrevistas. Hasta entonces, NO MEDIDO.

## Por qué puede funcionar

- La decisión es código determinista: la misma factura da siempre el mismo resultado, y por eso se puede auditar y
  vender como control, no como opinión de un modelo.
- El costo de modelo es acotado porque sólo se usa para leer y narrar; el volumen del reto público usa el modelo más
  barato y tiene tope diario.
- La alternativa que tiene hoy una pyme es verificar por teléfono o duplicar aprobaciones. Custodio la automatiza y deja
  evidencia.

## Riesgos y límites

- Todo el dataset es sintético: una pyme real traerá formatos que no vimos. Se mide cuando alguien lo pruebe.
- Un lector que se equivoque en un valor no paga mal: sin cita verificada el valor cuenta como no leído y se escala.
  Pero escalar demasiado cansa a la persona; esa tasa de escalamiento hay que medirla en pilotos.
- Custodio decide con las reglas que le dan. Si la empresa las deja flojas, paga conforme a ellas.
- Fuera de alcance de esta entrega: mover dinero real, pasarelas, KYC y cumplimiento regulatorio.

## Siguientes pasos

1. Publicar y medir: autonomía, exactitud y pagos indebidos sobre el dataset, con el comando de
   [`DATASET.md`](DATASET.md).
2. Dejar el reto público abierto y reportar los intentos y los ataques atrapados tal como los muestra el contador.
3. Probar con facturas reales (anonimizadas) de tres pymes y medir qué porcentaje se decide sin persona.
4. Entrevistar a quienes construyen agentes de pago para fijar la unidad de cobro.
