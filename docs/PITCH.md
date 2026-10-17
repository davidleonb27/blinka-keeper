# Guion del video

Entrega: video de 3:00 exactos, demo en vivo y repo público. Equipo DreamMakers, Hackathon 30X, Reto Blinka.

## Reglas de grabación

- **Sólo cifras medidas.** Lo que está entre `{{llaves}}` se lee del panel de la demo desplegada justo antes de grabar.
  Si el panel dice NO MEDIDO, se dice «aún no lo medimos» y no se inventa nada.
- Las dos cifras del FBI y de la AFP del minuto 0:20 son externas y tienen fuente en pantalla (ver
  [`BUSINESS.md`](BUSINESS.md)).
- Una sola voz, ritmo de conversación: máximo 2,6 palabras por segundo (lo comprueba un test del repo).
- Grabar sobre la demo desplegada con la empresa demo. Pantalla a 1080p, zoom del navegador al 125 %.
- Subtítulos en español siempre; el video debe entenderse sin sonido.
- Antes de grabar: abrir un espacio nuevo, correr el lote y dejar una factura pendiente para el minuto 2:00.

## Versión de 3:00

### 0:00–0:20 · Dos facturas casi idénticas

**Se oye:** Mira estas dos facturas. Mismo proveedor, mismo monto, mismo logo. Una sola cosa cambió: el número de la cuenta a donde se paga. Una persona con prisa paga las dos. Un agente de IA que sólo lee también. Custodio no.

**Se ve:** Las dos facturas lado a lado, con el número de cuenta resaltado en rojo en la segunda. Corte a Custodio: la primera dice «Pagar», la segunda «Retener: la cuenta no es la registrada».

**Respaldo:** Capturas fijas de las dos facturas y del acta de la segunda, con zoom a la regla R4.

### 0:20–0:40 · El problema

**Se oye:** El FBI recibió en 2025 veinticuatro mil setecientas sesenta y ocho denuncias de fraude por correo empresarial. Pérdidas reportadas: más de tres mil millones de dólares. Y los agentes que leen facturas son un blanco nuevo: basta una instrucción escondida en el PDF.

**Se ve:** Texto grande «24.768 denuncias · US$ 3.046.598.558 · FBI IC3, 2025» con la fuente al pie. Luego un PDF con texto blanco sobre blanco que se destapa.

**Respaldo:** Diapositiva estática con las dos cifras y el enlace al informe; captura del texto oculto destapado en el acta.

### 0:40–1:15 · Una semana decidida

**Se oye:** Esta es Cobalto Labs. Una semana de facturas entra al panel. Las limpias se pagan solas. Las trampas se retienen. Lo dudoso espera a una persona. Cada fila tiene su razón en una línea. Abro un acta: doce reglas, cada una con sus cifras, y lo que habría que cambiar para pagarla. El modelo sólo leyó y citó. Decidió el código.

**Se ve:** Botón «Probar con una empresa demo», panel con pagado, retenido y pendiente. Apertura del acta de una factura retenida: las 12 reglas, el contrafactual, la cita resaltada en el documento, el hash.

**Respaldo:** Grabación del mismo recorrido hecha de antemano, sin cortes, a velocidad normal.

### 1:15–2:00 · Claude contra Claude

**Se oye:** ¿Aguanta de verdad? Pusimos a Claude Opus a atacarlo. Escribe una factura fraudulenta, ve por qué la bloquearon y cambia de técnica. Ronda tras ronda, el defensor no cambia, porque las reglas son código. Y ahora lo abrimos al público: Róbale a Custodio. Cualquiera sube una factura trampa. El contador marca {{intentos}} intentos y {{indebidos}} pagos indebidos.

**Se ve:** La Arena con las rondas en vivo: técnica, factura generada, veredicto, marcador. Después la página «Róbale a Custodio» con el contador en vivo y el muro de ataques. Se sube una factura trampa y aparece el resultado.

**Respaldo:** Una ejecución de la Arena grabada, con el marcador final visible; captura del contador del reto.

### 2:00–2:20 · El celular aprueba

**Se oye:** Si algo es legítimo pero grande, Custodio no decide solo. Le llega el acta a Ana por Telegram. Un toque para aprobar, y el panel se actualiza. Ni aprobando se rompe la reserva de caja.

**Se ve:** Pantalla dividida: el celular con el mensaje de Telegram y los botones; el panel que pasa de «pendiente» a «pagado por una persona».

**Respaldo:** Captura de pantalla del celular con el mensaje y del panel antes y después.

### 2:20–2:40 · Firewall y modelo de negocio

**Se oye:** Y no sirve sólo para facturas. Cualquier agente, el de Blinka, uno de Claude o un ERP, envía una intención de pago por API o MCP y recibe pagar, retener o escalar. Se cobra por decisión. Los precios aún no los medimos.

**Se ve:** Un cliente MCP en Claude Desktop pidiendo un pago y recibiendo «retener» con el enlace al acta. Debajo, el comando de ejemplo de la pantalla «Desarrolladores».

**Respaldo:** Captura de la pantalla «Desarrolladores» y de la respuesta JSON del firewall.

### 2:40–3:00 · Prueba y cierre

**Se oye:** No es una maqueta. Hay tests de propiedades sobre miles de empresas aleatorias y un botón para alterar el registro y ver dónde se rompe. Somos DreamMakers: Adriano, Juan David y Leober. Custodio: el modelo lee, el código decide, la persona autoriza.

**Se ve:** El botón «alterar una copia» y la cadena rota en rojo en una entrada. Cierre con el logo, el enlace de la demo, el repo y los tres nombres.

**Respaldo:** Captura de la cadena rota y plano fijo del cierre con el enlace.

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
