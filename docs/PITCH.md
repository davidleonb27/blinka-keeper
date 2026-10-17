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
- Antes de grabar: abrir un espacio nuevo, correr el lote y dejar una factura pendiente para el minuto 1:40.
- El minuto 2:00 necesita el despliegue con `CUSTODIO_PAYMENT_RAIL=stripe_test` y una clave `sk_test_`: `GET
  /api/v1/health` debe decir `"payment_rail": "stripe_test"`. Si no, esa escena se graba con el respaldo y se dice
  «simulado» en pantalla.
- **Toma** dice cómo se filma cada escena; **Respaldo**, qué se usa si la toma en vivo falla.

## Versión de 3:00

### 0:00–0:20 · Dos facturas casi idénticas

**Se oye:** Mira estas dos facturas. Mismo proveedor, mismo monto, mismo logo. Una sola cosa cambió: el número de la cuenta a donde se paga. Una persona con prisa paga las dos. Un agente de IA que sólo lee también. Custodio no.

**Se ve:** Las dos facturas lado a lado, con el número de cuenta resaltado en rojo en la segunda. Corte a Custodio: la primera dice «Pagar», la segunda «Retener: la cuenta no es la registrada».

**Toma:** Plano de pantalla completa sobre el documento; zoom lento al número de cuenta y corte seco al veredicto.

**Respaldo:** Capturas fijas de las dos facturas y del acta de la segunda, con zoom a la regla R4.

### 0:20–0:35 · El problema

**Se oye:** En 2025 el FBI recibió veinticuatro mil setecientas sesenta y ocho denuncias de fraude por correo empresarial: más de tres mil millones de dólares perdidos. Y un agente que lee facturas es un blanco nuevo.

**Se ve:** Texto grande «24.768 denuncias · US$ 3.046.598.558 · FBI IC3, 2025» con la fuente al pie. Luego un PDF con texto blanco sobre blanco que se destapa.

**Toma:** Diapositiva fija de 8 s con la fuente legible; después el acta con el texto oculto destapado.

**Respaldo:** Diapositiva estática con las dos cifras y el enlace al informe; captura del texto oculto destapado en el acta.

### 0:35–1:05 · Una semana decidida

**Se oye:** Esta es Cobalto Labs. Una semana de facturas entra al panel. Las limpias se pagan solas. Las trampas se retienen. Lo dudoso espera a una persona. Cada fila tiene su razón en una línea. Abro un acta: quince reglas, cada una con sus cifras, y lo que habría que cambiar para pagarla. El modelo sólo leyó y citó. Decidió el código.

**Se ve:** Botón «Probar con una empresa demo», panel con pagado, retenido y pendiente. Apertura del acta de una factura retenida: las 15 reglas, el contrafactual, la cita resaltada en el documento, el hash.

**Toma:** Grabación de pantalla continua, sin cortes, cursor visible; el acta se abre con zoom al 125 %.

**Respaldo:** Grabación del mismo recorrido hecha de antemano, sin cortes, a velocidad normal.

### 1:05–1:40 · Claude contra Claude

**Se oye:** ¿Aguanta de verdad? Pusimos a Claude Opus a atacarlo. Escribe una factura fraudulenta, ve por qué la bloquearon y cambia de técnica. Ronda tras ronda, el defensor no cambia, porque las reglas son código. Y ahora lo abrimos al público: Róbale a Custodio. Cualquiera sube una factura trampa. El contador marca {{intentos}} intentos y {{indebidos}} pagos indebidos.

**Se ve:** La Arena con las rondas en vivo: técnica, factura generada, veredicto, marcador. Después la página «Róbale a Custodio» con el contador en vivo y el muro de ataques. Se sube una factura trampa y aparece el resultado.

**Toma:** La Arena acelerada al doble entre rondas y a velocidad normal en cada veredicto; el contador en plano fijo.

**Respaldo:** Una ejecución de la Arena grabada, con el marcador final visible; captura del contador del reto.

### 1:40–2:00 · Una persona aprueba

**Se oye:** Si algo es legítimo pero grande, Custodio no decide solo. Deja el acta abierta para Ana. Ella la lee, toca aprobar, y el panel se actualiza. Ni aprobando se rompe la reserva de caja.

**Se ve:** Pantalla dividida: el acta con los botones «Aprobar» y «Rechazar»; el panel que pasa de «pendiente» a «pagado por una persona».

**Toma:** Pantalla dividida en dos mitades; el clic en «Aprobar» se ve completo, sin corte.

**Respaldo:** Capturas del acta pendiente y del panel antes y después de aprobar.

### 2:00–2:25 · El pago sale de verdad

**Se oye:** Y cuando Custodio dice pagar, el pago sale. La factura que Ana aprobó viaja por Stripe en modo prueba: una transferencia real, con dinero de prueba. El acta muestra su identificador. Lo abro, y es la misma transferencia en Stripe. Una clave de dinero real se rechaza.

**Se ve:** El acta de la factura aprobada con el bloque «Ejecución del pago»: «Stripe · modo prueba», el monto enviado y «Transferencia tr_…». Clic en el identificador: el dashboard de Stripe en modo prueba abre la misma transferencia, con el enlace al acta en su metadata.

**Toma:** Zoom al identificador `tr_…` en el acta; corte al dashboard de Stripe con el mismo identificador resaltado. El identificador se lee de la pantalla al grabar; no se escribe a mano.

**Respaldo:** Captura del acta con el `tr_…` y captura del dashboard de Stripe con el mismo identificador, tomadas en la misma sesión.

### 2:25–2:45 · Firewall y Blinka

**Se oye:** Para Blinka es una pieza más. Su agente, o el de su cliente, pregunta por API o MCP y recibe pagar, retener o escalar. Lo que se paga se vuelve la instrucción exacta para ACH, wire, Bre-B, SPEI o Pix.

**Se ve:** Un cliente MCP en Claude Desktop pidiendo un pago y recibiendo «retener» con el enlace al acta. Después la instrucción para Blinka en el acta (red, monto, cuenta registrada, referencia al acta) y la tabla de redes de `docs/BLINKA.md`.

**Toma:** Terminal y Claude Desktop lado a lado; la instrucción JSON con zoom en `network` y `reference`.

**Respaldo:** Captura de la pantalla «Desarrolladores», de la respuesta JSON del firewall y de la instrucción para Blinka.

### 2:45–3:00 · Cierre

**Se oye:** No es una maqueta: mil empresas simuladas y un registro que delata cualquier cambio. Somos DreamMakers: Adriano, Juan David y Leober. El modelo lee, el código decide, la persona autoriza. Custodio decide; Blinka paga.

**Se ve:** El botón «alterar una copia» y la cadena rota en rojo en una entrada. Cierre con el logo, «Custodio decide; Blinka paga», el enlace de la demo, el repo y los tres nombres.

**Toma:** Dos segundos de la cadena rota; plano fijo del cierre durante los últimos 8 s, sin movimiento.

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

**Se ve:** El panel con pagado, retenido y pendiente; un acta abierta con las quince reglas.

### 0:36–0:50 · Claude contra Claude

**Se oye:** Pusimos a Claude a atacarlo. Cambia de técnica; las reglas no cambian. Ahora tú: Róbale a Custodio.

**Se ve:** La Arena en vivo y la página del reto con su contador.

### 0:50–1:00 · Cierre

**Se oye:** Custodio, de DreamMakers. El modelo lee, el código decide, la persona autoriza. Pruébalo, el enlace está abajo.

**Se ve:** Logo, enlace de la demo y el repo.
