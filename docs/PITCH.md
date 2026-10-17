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

## Versión de 3:00

Es el guion de `docs/video/out/custodio-pitch-horizontal.mp4` (2:55.8). Los tiempos de abajo son
los del corte repartidos sobre 3:00 y redondeados al segundo; los exactos, frase por frase, están en
[`video/GUION.md`](video/GUION.md).

### 0:00–0:09 · Una maqueta lo dice; Custodio lo demuestra

**Se oye:** Cualquiera puede hacer una maqueta bonita. Esto es Custodio funcionando de verdad: en producción, con pagos reales y bajo ataque.

**Se ve:** Tarjeta: «Una maqueta lo dice» se tacha; «Custodio lo demuestra». En producción · pagos reales · bajo ataque.

**Respaldo:** Tarjeta `open` de `docs/video/titles.html`.

### 0:09–0:23 · El problema

**Se oye:** En 2025, el FBI recibió más de 24.000 denuncias de fraude por correo empresarial: más de 3.000 millones de dólares. A un agente que lee facturas le basta una frase escondida.

**Se ve:** Tarjeta: 24.768 denuncias y US$ 3.046.598.558 (FBI IC3, Informe anual 2025, fuente en pantalla).

**Respaldo:** Tarjeta `problem`, con la fuente del FBI IC3 en pantalla.

### 0:23–0:37 · Una empresa demo nueva, 36 facturas

**Se oye:** Esta es Cobalto Labs, una empresa demo recién creada. Le llegan 36 facturas: correos, PDF, fotos y WhatsApp. Un clic, y Custodio decide cada una con doce reglas escritas en código.

**Se ve:** Producto: inicio → «Probar con una empresa demo» → panel con 36 facturas recibidas → «Decidir las 36 facturas» (acelerado ×4).

**Respaldo:** Toma `landing` de `docs/video/record.mjs` (espacio demo nuevo en producción).

### 0:37–0:47 · Las cifras del panel

**Se oye:** Diecisiete se pagan solas. Cinco trampas se retienen. Catorce esperan a una persona. Pagos indebidos: cero, y un auditor independiente está de acuerdo.

**Se ve:** Producto: zoom a «Pagos indebidos 0» y a Pagado / Retenido / Pendiente.

**Respaldo:** Toma `landing`, marcas `zoom_zero` y `zoom_counts`.

### 0:47–0:57 · Un ataque de verdad

**Se oye:** Ahora, un ataque de verdad. Esta factura de Andes Code parece normal, pero esconde una orden en texto blanco y trae la cuenta bancaria cambiada.

**Se ve:** Tarjeta: el PDF real que se sube; un barrido destapa la línea en blanco y marca la cuenta cambiada.

**Respaldo:** Tarjeta `pdf` con el PDF real que genera `docs/video/make_attack_pdf.py`.

### 0:57–1:15 · El reto público lo retiene

**Se oye:** La subimos al reto público. Retenida. Custodio destapa la frase oculta, cita las reglas que la frenan y no obedece al documento.

**Se ve:** Producto: «Róbale a Custodio», se sube el PDF, «No pasó. Custodio no pagó», R2 + R4, la cita destapada y el contador.

**Respaldo:** Toma `attack`: el mismo PDF subido a «Róbale a Custodio».

### 1:15–1:27 · La Arena cambia de técnica

**Se oye:** Y no es un solo truco. En la Arena, un modelo atacante inventa fraudes, lee por qué lo bloquearon y cambia de técnica. Tres ataques, tres atrapados, cero pagos indebidos.

**Se ve:** Producto: Arena, 3 rondas en vivo (acelerado ×6) y el marcador final.

**Respaldo:** Toma `arena`: 3 rondas en vivo.

### 1:27–1:41 · Cada decisión, con su acta

**Se oye:** Cada decisión trae su acta: por qué, qué regla aplicó y qué tendría que cambiar para pagarla. La cuenta no es la registrada: regla R4. El modelo lee y cita; decide el código.

**Se ve:** Producto: acta de Andrés Paredes: por qué, qué tendría que cambiar, R4 resaltada.

**Respaldo:** Toma `held`: acta de Andrés Paredes.

### 1:41–1:52 · Pago real en Stripe

**Se oye:** Y cuando paga, paga de verdad: una transferencia en Stripe, en modo prueba, con su identificador en el acta.

**Se ve:** Producto: acta de una factura pagada; zoom a «Stripe · modo prueba» y la transferencia tr_….

**Respaldo:** Toma `paid`: acta con la transferencia `tr_…`.

### 1:52–2:08 · Una persona aprueba

**Se oye:** Lo que se sale de lo acordado espera a una persona. Ana revisa, aprueba, y el pago sale con su aprobación en el registro.

**Se ve:** Producto: Cumulus Hosting fuera de lo acordado; Ana Gómez aprueba; zoom a la transferencia tr_….

**Respaldo:** Toma `approve`: Cumulus Hosting aprobada por Ana Gómez.

### 2:08–2:22 · El registro detecta la alteración

**Se oye:** Ese registro está encadenado con SHA-256. Verificar: íntegro. Si alguien altera una copia, la cadena se rompe justo en el asiento cambiado.

**Se ve:** Producto: Registro → «Verificar la cadena» (verde) → «Alterar una copia» (rojo en el asiento exacto).

**Respaldo:** Toma `ledger`: verificar y alterar una copia.

### 2:22–2:36 · Reglas en tus palabras

**Se oye:** ¿Quieres cambiar una regla? Escríbela en español. Custodio la compila y te muestra qué facturas cambiarían antes de aplicarla.

**Se ve:** Producto: Reglas: se escribe «Nada sobre 1.000 USD sin que lo apruebe Ana» → compilar y simular (acelerado ×3).

**Respaldo:** Toma `rules`: compilar y simular sin aplicar.

### 2:36–2:45 · Medido a escala

**Se oye:** Y lo medimos a escala: mil empresas simuladas, veinticinco mil facturas, ocho mil pagos auditados otra vez. Cero indebidos.

**Se ve:** Tarjeta: 1.000 empresas · 25.139 facturas · 8.136 pagos re-auditados · 0 pagos indebidos (README › Métricas).

**Respaldo:** Tarjeta `proof` con las cifras del README › Métricas.

### 2:45–2:55 · Maqueta contra producto

**Se oye:** Una maqueta lo dice. Custodio lo demuestra: ataque real, pago real y un registro que se puede verificar. Código abierto, con licencia MIT.

**Se ve:** Tarjeta: «Una maqueta lo dice» frente a «Custodio lo demuestra, en producción», fila por fila.

**Respaldo:** Tarjeta `compare`.

### 2:55–3:00 · Cierre

**Se oye:** Custodio decide; Blinka paga. Somos DreamMakers.

**Se ve:** Tarjeta: «Custodio decide; Blinka paga.», enlace de la demo, repo, MIT y el equipo.

**Respaldo:** Tarjeta `close`.

## Corte vertical de 43 s

Para redes y Build in Public, en el formato vertical de la competencia pero con producto real:
`docs/video/out/custodio-pitch-vertical.mp4` (1080×1920, 0:43.0).

- **0:00.0** Otros te muestran maquetas. Esto es Custodio, en producción. Tarjeta vertical: «Una maqueta lo dice. Custodio lo demuestra.»
- **0:06.8** Una factura con una orden escondida en texto blanco y la cuenta cambiada. Tarjeta vertical: el PDF con la línea oculta destapada y la cuenta cambiada.
- **0:13.4** Custodio la retiene y destapa la trampa. Producto: resultado del reto, Retenida, con la cita destapada.
- **0:20.9** Cuando paga, paga de verdad: una transferencia en Stripe, en modo prueba. Producto: acta pagada con la transferencia tr_… de Stripe en modo prueba.
- **0:25.7** Alteras una copia del registro y la cadena se rompe justo ahí. Producto: la copia alterada rompe la cadena en el asiento exacto.
- **0:31.9** Mil empresas, veinticinco mil facturas: cero pagos indebidos. Tarjeta vertical: 1.000 empresas, 25.139 facturas, 0 pagos indebidos.
- **0:38.5** Custodio decide; Blinka paga. Tarjeta vertical: «Custodio decide; Blinka paga.»

## Versión de 60 s

### 0:00–0:08 · Gancho

**Se oye:** Dos facturas idénticas. Sólo cambió el número de cuenta. Una se paga. La otra, no.

**Se ve:** Las dos facturas lado a lado y el número de cuenta que cambia, resaltado.

### 0:08–0:20 · Problema

**Se oye:** En 2025 el FBI recibió más de veinticuatro mil denuncias de fraude por correo empresarial. Un agente de IA que lee facturas es el blanco ideal.

**Se ve:** «24.768 denuncias · FBI IC3, 2025» con la fuente al pie.

### 0:20–0:36 · El código decide

**Se oye:** En Custodio el modelo lee y cita. Doce reglas en código pagan, retienen o preguntan a una persona. Cada decisión trae su acta y queda en un registro que no se puede alterar.

**Se ve:** El panel con pagado, retenido y pendiente; un acta abierta con las doce reglas.

### 0:36–0:50 · Claude contra Claude

**Se oye:** Pusimos a Claude a atacarlo. Cambia de técnica; las reglas no cambian. Ahora tú: Róbale a Custodio.

**Se ve:** La Arena en vivo y la página del reto con su contador.

### 0:50–1:00 · Cierre

**Se oye:** Custodio, de DreamMakers. El modelo lee, el código decide, la persona autoriza. Pruébalo, el enlace está abajo.

**Se ve:** Logo, enlace de la demo y el repo.
