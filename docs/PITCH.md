# Guion del video

Entrega: video de 3:00 exactos, demo en vivo y repo público. Equipo DreamMakers, Hackathon 30X, Reto Blinka.

## Reglas de grabación

- **Sólo cifras medidas.** Lo que está entre `{{llaves}}` se lee del panel de la demo desplegada justo antes de grabar.
  Si el panel dice NO MEDIDO, se dice «aún no lo medimos» y no se inventa nada.
- Las cifras del FBI del minuto 0:09 son externas y tienen fuente en pantalla (ver
  [`BUSINESS.md`](BUSINESS.md)).
- Una sola voz, ritmo de conversación: máximo 2,6 palabras por segundo (lo comprueba un test del repo).
- Grabar sobre la demo desplegada con la empresa demo. Pantalla a 1080p, zoom del navegador al 125 %.
- Subtítulos en español siempre; el video debe entenderse sin sonido.
- Antes de grabar: abrir un espacio nuevo y correr el lote. `docs/video/render.sh` lo hace solo: crea un espacio demo
  nuevo en producción, graba las tomas con Playwright y monta los dos cortes con ffmpeg (ver
  [`lanes/reports/L16.md`](lanes/reports/L16.md)).
- La escena del pago (1:42) necesita el despliegue con `CUSTODIO_PAYMENT_RAIL=stripe_test` y una clave `sk_test_`: `GET
  /api/v1/health` debe decir `"payment_rail": "stripe_test"`. Si no, esa escena se graba con el respaldo y se dice
  «simulado» en pantalla.
- **Toma** dice cómo se filma cada escena; **Respaldo**, qué se usa si la toma en vivo falla.

## Versión de 3:00

Es el guion de `docs/video/out/custodio-pitch-horizontal.mp4` (2:59.0). Los tiempos de abajo son
los del corte en segundos enteros sobre 3:00; los exactos, frase por frase, están en
[`video/GUION.md`](video/GUION.md).

### 0:00–0:09 · Una maqueta lo dice; Blinka Keeper lo demuestra

**Se oye:** Cualquiera puede hacer una maqueta bonita. Esto es Blinka Keeper funcionando de verdad: en producción, con pagos reales y bajo ataque.

**Se ve:** Tarjeta: «Una maqueta lo dice» se tacha; «Blinka Keeper lo demuestra». En producción · pagos reales · bajo ataque.

**Toma:** Tarjeta animada, sin producto.

**Respaldo:** Tarjeta `open` de `docs/video/titles.html`.

### 0:09–0:18 · El problema

**Se oye:** En 2025, el FBI recibió más de 24.000 denuncias de fraude por correo empresarial: más de 3.000 millones de dólares.

**Se ve:** Tarjeta: 24.768 denuncias y US$ 3.046.598.558 (FBI IC3, Informe anual 2025, fuente en pantalla).

**Toma:** Tarjeta animada; las cifras cuentan hasta su valor y la fuente queda fija al pie.

**Respaldo:** Tarjeta `problem`, con la fuente del FBI IC3 en pantalla.

### 0:18–0:31 · Una empresa demo nueva, 38 facturas

**Se oye:** Esta es Cobalto Labs, una empresa demo recién creada, con 38 facturas de correos, PDF, fotos y WhatsApp. Un clic, y quince reglas escritas en código deciden cada una.

**Se ve:** Producto: inicio → «Probar con una empresa demo» → panel con 38 facturas recibidas → «Decidir las 38 facturas» (acelerado ×4).

**Toma:** Grabación continua con cursor visible; la espera de la decisión va acelerada ×4 y lo dice en pantalla.

**Respaldo:** Toma `landing` de `docs/video/record.mjs` (espacio demo nuevo en producción).

### 0:31–0:41 · Las cifras del panel

**Se oye:** Diecisiete se pagan solas. Siete trampas se retienen. Catorce esperan a una persona. Pagos indebidos: cero, y un auditor independiente está de acuerdo.

**Se ve:** Producto: zoom a «Pagos indebidos 0» y a Pagado / Retenido / Pendiente (17 · 7 · 14 de 38).

**Toma:** Zoom suave a «Pagos indebidos» y a los tres totales, en la misma toma.

**Respaldo:** Toma `landing`, marcas `zoom_zero` y `zoom_counts`.

### 0:41–0:52 · Un ataque de verdad

**Se oye:** Ahora, un ataque de verdad. Esta factura de Andes Code parece normal, pero esconde una orden en texto blanco y trae la cuenta bancaria cambiada.

**Se ve:** Tarjeta: el PDF real que se sube; un barrido destapa la línea en blanco y marca la cuenta cambiada.

**Toma:** Tarjeta animada sobre el PDF real; un barrido destapa la línea oculta.

**Respaldo:** Tarjeta `pdf` con el PDF real que genera `docs/video/make_attack_pdf.py`.

### 0:52–1:06 · El reto público lo frena

**Se oye:** La subimos al reto público. Frenada. Blinka Keeper destapa la frase oculta, cita las reglas que la frenan y no obedece al documento.

**Se ve:** Producto: «Róbale a Blinka Keeper», se sube el PDF, FRENADO, las reglas que se dispararon (R2, R4) y la cita destapada.

**Toma:** Grabación continua: se sube el PDF, la lectura va ×3 y el resultado a velocidad normal con zoom.

**Respaldo:** Toma `attack`: el mismo PDF subido a «Róbale a Blinka Keeper».

### 1:06–1:18 · La Arena cambia de técnica

**Se oye:** Y no es un solo truco. En la Arena, un modelo atacante inventa fraudes, lee por qué lo bloquearon y cambia de técnica. Tres ataques, tres atrapados, cero pagos indebidos.

**Se ve:** Producto: Arena, 3 rondas en vivo (acelerado ×6) y el marcador final.

**Toma:** Encuadre fijo bajo el título de la página; las rondas ×6 y el marcador final a velocidad normal.

**Respaldo:** Toma `arena`: 3 rondas en vivo.

### 1:18–1:36 · Cada decisión, con su acta

**Se oye:** Cada decisión trae su acta: por qué, qué regla aplicó y qué tendría que cambiar. Aquí cambió la cuenta y el correo imita el dominio: la retiene y pide llamar al contacto registrado. Y cruza cada proveedor con la lista de sanciones de la OFAC.

**Se ve:** Producto: acta de Joaquín Méndez (F-038): cuenta cambiada y dominio parecido; a quién llamar (R15) y la lista OFAC del 15 de octubre (R14).

**Toma:** Zoom a «Por qué» y «Qué tendría que cambiar», luego a R14 (OFAC) y R15 (fuera de banda).

**Respaldo:** Toma `held`: acta de Joaquín Méndez (F-038).

### 1:36–1:46 · Pago real en Stripe

**Se oye:** Y cuando paga, paga de verdad: una transferencia en Stripe, en modo prueba, con su identificador en el acta.

**Se ve:** Producto: acta de una factura pagada sola; zoom a «Stripe · modo prueba» y la transferencia tr_….

**Toma:** Zoom al identificador `tr_…` en el acta; no se abre el dashboard de Stripe.

**Respaldo:** Toma `paid_stripe`: acta con la transferencia `tr_…` (grabada antes del tope diario de Stripe).

### 1:46–1:57 · Autonomía ganada

**Se oye:** Cada proveedor se gana su tope de pago automático. Simulamos treinta días: una sola señal de riesgo lo devuelve a supervisión.

**Se ve:** Producto: Autonomía → «Simular 30 días» (×2) → el resultado y un proveedor «En supervisión» tras «Confianza revocada».

**Toma:** Clic en «Simular 30 días» (×2) y zoom al resultado y a una tarjeta en supervisión.

**Respaldo:** Toma `autonomy`: `/autonomia` con «Simular 30 días».

### 1:57–2:05 · Conciliación y cierre de mes

**Se oye:** Y al cierre del mes, cruza el extracto del banco con lo pagado y marca cada salida sin factura.

**Se ve:** Producto: Conciliación → «Usar extracto de demo» (×3) → conciliado, diferencias, comisiones y «Sin factura».

**Toma:** Encuadre bajo la ayuda de carga; la conciliación ×3 y zoom al resumen y a «Sin factura».

**Respaldo:** Toma `reconcile`: `/conciliacion` con el extracto de demo.

### 2:05–2:16 · El registro detecta la alteración

**Se oye:** Ese registro está encadenado con SHA-256. Verificar: íntegro. Si alguien altera una copia, la cadena se rompe justo en el asiento cambiado.

**Se ve:** Producto: Registro → «Verificar la cadena» (verde) → «Alterar una copia» (rojo en el asiento exacto).

**Toma:** Zoom al verde de la verificación y al rojo de la copia alterada.

**Respaldo:** Toma `ledger`: verificar y alterar una copia.

### 2:16–2:28 · Reglas en tus palabras

**Se oye:** ¿Quieres cambiar una regla? Escríbela en español. Blinka Keeper la compila y te muestra qué facturas cambiarían antes de aplicarla.

**Se ve:** Producto: Reglas: se escribe «Nada sobre 1.000 USD sin que lo apruebe Ana» → compilar y simular (acelerado ×3).

**Toma:** Se teclea la regla en cámara; la compilación va ×3 y la simulación con zoom.

**Respaldo:** Toma `rules`: compilar y simular sin aplicar.

### 2:28–2:37 · Medido a escala

**Se oye:** Y lo medimos a escala: mil empresas simuladas, veinticinco mil facturas, ocho mil pagos auditados otra vez. Cero indebidos.

**Se ve:** Tarjeta: 1.000 empresas · 25.139 facturas · 8.136 pagos re-auditados · 0 pagos indebidos (README › Métricas).

**Toma:** Tarjeta animada.

**Respaldo:** Tarjeta `proof` con las cifras del README › Métricas.

### 2:37–2:48 · Maqueta contra producto

**Se oye:** Una maqueta lo dice. Blinka Keeper lo demuestra: ataque real, pago real y un registro verificable. Código abierto, con licencia MIT y autoalojable con Docker.

**Se ve:** Tarjeta: «Una maqueta lo dice» frente a «Blinka Keeper lo demuestra, en producción», fila por fila.

**Toma:** Tarjeta animada, fila por fila.

**Respaldo:** Tarjeta `compare`.

### 2:48–2:55 · Jurado: intenten robarnos ahora

**Se oye:** Y el reto sigue abierto. Jurado: escaneen el código e intenten robarnos ahora. Pagos indebidos: cero.

**Se ve:** Producto: «Róbale a Blinka Keeper» en modo escenario: el QR a /reto y «Pagos indebidos 0» en vivo.

**Toma:** Plano fijo del modo escenario y zoom al contador; el número se lee de la pantalla.

**Respaldo:** Toma `stage`: `/reto?escenario=1`.

### 2:55–3:00 · Cierre

**Se oye:** Blinka Keeper decide; Blinka paga. Somos DreamMakers.

**Se ve:** Tarjeta: «Blinka Keeper decide; Blinka paga.», enlace de la demo, repo, MIT y el equipo.

**Toma:** Plano fijo.

**Respaldo:** Tarjeta `close`.

## Corte vertical de 40 s

Para redes y Build in Public, en el formato vertical de la competencia pero con producto real:
`docs/video/out/custodio-pitch-vertical.mp4` (1080×1920, 0:40.2).

- **0:00.0** Otros te muestran maquetas. Esto es Blinka Keeper, en producción. Tarjeta vertical: «Una maqueta lo dice. Blinka Keeper lo demuestra.»
- **0:06.8** Una factura con una orden escondida en texto blanco y la cuenta cambiada. Tarjeta vertical: el PDF con la línea oculta destapada y la cuenta cambiada.
- **0:13.4** Blinka Keeper la frena y destapa la trampa. Producto: resultado del reto, FRENADO, con la cita destapada.
- **0:20.6** Cuando paga, paga de verdad: una transferencia en Stripe, en modo prueba. Producto: la factura aprobada sale por Stripe en modo prueba, con su transferencia tr_….
- **0:25.4** Cruza el extracto del banco con lo pagado y marca cada salida sin factura. Producto: la conciliación con el extracto de demo y la alerta «Sin factura».
- **0:30.6** Ahora tú: escanea el código e intenta robarnos. Pagos indebidos: cero. Producto: modo escenario del reto, con el QR y «Pagos indebidos 0».
- **0:35.7** Blinka Keeper decide; Blinka paga. Tarjeta vertical: «Blinka Keeper decide; Blinka paga.»

## Versión de 60 s

### 0:00–0:08 · Gancho

**Se oye:** Dos facturas idénticas. Sólo cambió el número de cuenta. Una se paga. La otra, no.

**Se ve:** Las dos facturas lado a lado y el número de cuenta que cambia, resaltado.

### 0:08–0:20 · Problema

**Se oye:** En 2025 el FBI recibió más de veinticuatro mil denuncias de fraude por correo empresarial. Un agente de IA que lee facturas es el blanco ideal.

**Se ve:** «24.768 denuncias · FBI IC3, 2025» con la fuente al pie.

### 0:20–0:36 · El código decide

**Se oye:** En Blinka Keeper el modelo lee y cita. Doce reglas en código pagan, retienen o preguntan a una persona. Cada decisión trae su acta y queda en un registro que no se puede alterar.

**Se ve:** El panel con pagado, retenido y pendiente; un acta abierta con las quince reglas.

### 0:36–0:50 · Claude contra Claude

**Se oye:** Pusimos a Claude a atacarlo. Cambia de técnica; las reglas no cambian. Ahora tú: Róbale a Blinka Keeper.

**Se ve:** La Arena en vivo y la página del reto con su contador.

### 0:50–1:00 · Cierre

**Se oye:** Blinka Keeper, de DreamMakers. El modelo lee, el código decide, la persona autoriza. Pruébalo, el enlace está abajo.

**Se ve:** Logo, enlace de la demo y el repo.
