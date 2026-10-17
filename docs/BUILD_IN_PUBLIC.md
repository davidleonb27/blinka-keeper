# Build in public

Una publicación cada 4 horas, en X y en LinkedIn, desde el viernes 16 de octubre a las 8:00 p. m. hasta el domingo 18 a
las 8:00 a. m. (hora de Colombia), cuatro horas antes de la entrega a las 11:59 a. m. El sábado a las 12:00 m. sale el
lanzamiento del reto público «Róbale a Custodio».

## Cómo usar este calendario

- **Hora de Colombia (UTC−5).** Las publicaciones de las 12:00 a. m. y las 4:00 a. m. se programan de antemano; no
  hace falta estar despierto.
- **Sólo cifras medidas.** Lo que está entre `{{llaves}}` se copia del contador de la demo justo antes de publicar. Si el
  contador dice NO MEDIDO, se escribe «aún no lo medimos». Nunca se redondea hacia arriba.
- `{{DEMO_URL}}` es el enlace de la demo desplegada.
- Cada borrador de X cabe en 280 caracteres, contando con que `{{DEMO_URL}}` ocupa 23 (así cuenta X cualquier enlace).
- Todas mencionan el hackathon 30X y a Blinka. Si el equipo confirma los usuarios oficiales, se añaden como menciones.
- **Antes de publicar, comprobar que es verdad.** Cada borrador describe algo que debe existir a esa hora (la Arena
  corriendo, el muro, el botón de alterar el registro). Si no existe todavía, se reescribe el texto.
- Imagen: la que indica cada publicación, desde `docs/img/` (ver [`img/LEEME.md`](img/LEEME.md)).
- Responder a quien intente el reto, con respeto y con el acta de su intento. Si logra algo, se dice.

## Calendario

### 2026-10-16 20:00 · Arranque del último tramo
**Imagen:** `acta.png`

#### X
> Desde hoy hasta el domingo 11:59 a. m. publicamos cada 4 horas cómo cerramos Custodio para el reto Blinka de 30X. Es un agente de cuentas por pagar: el modelo lee, el código decide, la persona autoriza. #30X #RetoBlinka

#### LinkedIn
> Quedan unas 40 horas para entregar Custodio en el hackathon 30X, reto Blinka. Vamos a contar el proceso cada 4 horas, con lo que funciona y lo que no.
>
> Custodio revisa facturas de proveedores y paga sólo lo que cabe en las reglas de la empresa. Retiene lo claramente indebido y le pregunta a una persona lo demás. El modelo lee y cita; el código decide.
>
> Somos DreamMakers: Adriano Joao Souza Reyna, Juan David Leon y Leober Ramos. Mañana al mediodía abrimos un reto público. #30X #Blinka

### 2026-10-17 00:00 · Una trampa por regla
**Imagen:** `panel.png`

#### X
> Nuestro dataset de facturas tiene una trampa por regla: cuenta cambiada, duplicado, beneficiario nuevo, fraccionamiento, texto oculto. Cada una dice qué regla la atrapa. Está publicado en el repo. #30X #RetoBlinka

#### LinkedIn
> Para el reto Blinka de 30X armamos un dataset propio con las trampas que pide el reto y algunas nuestras: duplicado exacto y con otro número, beneficiario nuevo o bloqueado, cuenta cambiada, desacuerdo con lo pactado, sobre el límite, cupo agotado, saldo insuficiente, pagos fraccionados, moneda ambigua e instrucciones escondidas en el PDF.
>
> Cada caso trae la decisión esperada y la regla que debería atraparlo. La tabla está en docs/DATASET.md. Los resultados sobre el dataset los publicaremos cuando los midamos, no antes. #30X #Blinka

### 2026-10-17 04:00 · Un auditor que no confía en el motor
**Imagen:** `acta.png`

#### X
> En Custodio un segundo código, escrito aparte, recalcula cada pago antes de hacerlo. Si discrepa del motor, gana el auditor y el pago no sale. Así buscamos cero pagos indebidos en el reto Blinka de 30X. #30X #RetoBlinka

#### LinkedIn
> Uno de los criterios del reto Blinka en 30X es que un solo pago indebido descalifica. Nuestra respuesta no es un prompt más cuidadoso.
>
> El modelo lee y debe citar el texto de donde sacó cada valor; el código verifica la cita. Doce reglas puras deciden. Y un auditor independiente, sin importar el código del motor, recalcula cada pago. Si no coinciden, el pago no se hace.
>
> Cada decisión queda con un acta que explica las doce reglas. #30X #Blinka

### 2026-10-17 08:00 · A mediodía abrimos el reto
**Imagen:** `arena.png`

#### X
> A las 12:00 m. abrimos «Róbale a Custodio»: intenta que pague algo que no debe. Antes, Claude lo ataca en la Arena; ahora lo puede probar cualquiera. Reto Blinka, hackathon 30X. #30X #RetoBlinka

#### LinkedIn
> Hoy a las 12:00 m. (hora de Colombia) abrimos al público «Róbale a Custodio» para el hackathon 30X, reto Blinka.
>
> Antes de abrirlo hicimos que Claude Opus atacara a Custodio en la Arena: escribe una factura fraudulenta, lee por qué la bloquearon y cambia de técnica. El defensor no cambia, porque sus reglas son código.
>
> Quien quiera intentarlo, a mediodía en {{DEMO_URL}}. #30X #Blinka

### 2026-10-17 12:00 · Lanzamiento: Róbale a Custodio
**Imagen:** `arena.png`

#### X
> Ya está abierto: Róbale a Custodio. Sube o escribe una factura trampa y mira si logras que pague algo indebido. El contador es público, los mejores ataques van al muro. Hackathon 30X, reto Blinka. {{DEMO_URL}} #30X #RetoBlinka

#### LinkedIn
> Lanzamos «Róbale a Custodio», el reto público de nuestro proyecto para el hackathon 30X, reto Blinka.
>
> Qué hacer: abre {{DEMO_URL}}, ve a «Róbale a Custodio», sube o escribe una factura trampa y mira qué decide. Puedes cambiar la cuenta, repetir un cobro, esconder una instrucción en el PDF o partir un pago en dos.
>
> Qué verás: el resultado al instante con el acta de las doce reglas, y un contador global de intentos y de pagos indebidos. Si logras que pague algo indebido, queda en el muro y lo corregimos a la vista. Cada ataque atrapado se vuelve un caso de prueba. #30X #Blinka

### 2026-10-17 16:00 · Primer parcial del reto
**Imagen:** captura del contador del reto

#### X
> Primer parcial de Róbale a Custodio: {{intentos}} intentos, {{indebidos}} pagos indebidos. El ataque más creativo hasta ahora: {{ataque}}. Sigue abierto para el hackathon 30X, reto Blinka. {{DEMO_URL}} #30X #RetoBlinka

#### LinkedIn
> Cuatro horas de reto público abierto en el hackathon 30X, reto Blinka. Parcial del contador de la demo: {{intentos}} intentos y {{indebidos}} pagos indebidos.
>
> El ataque que más nos gustó: {{ataque}}. Qué regla lo atrapó y cuál fue la razón que mostró el acta: {{regla}}.
>
> Si todavía no lo has intentado: {{DEMO_URL}}. #30X #Blinka

### 2026-10-17 20:00 · Lo que nos enseñaron los ataques
**Imagen:** captura del muro de ataques

#### X
> Lo que aprendimos del reto hasta ahora: {{aprendizaje}}. Cada ataque atrapado ya es un caso de prueba en el repo. Hackathon 30X, reto Blinka. {{DEMO_URL}} #30X #RetoBlinka

#### LinkedIn
> Balance de la tarde del reto público de Custodio, hackathon 30X, reto Blinka.
>
> Lo que aprendimos: {{aprendizaje}}.
>
> Lo que cambiamos por eso: {{cambio}}. Todo ataque atrapado se convierte en un caso de prueba que corre en cada commit. Lo que no atrapamos, si ocurre, lo publicamos. #30X #Blinka

### 2026-10-18 00:00 · Alterar el registro
**Imagen:** `registro-roto.png`

#### X
> Cada decisión de Custodio queda en un registro con hashes encadenados. En la demo hay un botón que altera una copia y muestra en qué entrada se rompe la cadena. Hackathon 30X, reto Blinka. #30X #RetoBlinka

#### LinkedIn
> Explicabilidad no es sólo un acta bonita. En Custodio cada decisión entra a un registro donde el hash de cada entrada incluye el de la anterior (SHA-256).
>
> Para que no tengas que creernos, la demo trae «alterar una copia»: cambia un dato en una copia del registro y muestra en qué entrada se rompe la cadena. El registro real no se toca. Proyecto para el hackathon 30X, reto Blinka. #30X #Blinka

### 2026-10-18 04:00 · Aprobar en un clic y firewall para agentes
**Imagen:** `panel.png`

#### X
> Lo dudoso no lo decide Custodio: queda pendiente en el acta web y un clic aprueba o rechaza. Y otros agentes pueden pedirle decisiones por API o MCP, como firewall de pagos. Hackathon 30X, reto Blinka. #30X #RetoBlinka

#### LinkedIn
> Dos piezas finales de Custodio para el reto Blinka del hackathon 30X:
>
> 1. Aprobación en un clic: lo que supera un tope o no está claro queda pendiente en el acta web, y la persona aprueba o rechaza. Aun aprobada, una factura no se paga si rompe la reserva de caja.
> 2. Firewall de pagos para otros agentes: por API o MCP, cualquier agente envía una intención de pago y recibe pagar, retener o escalar, con su acta. #30X #Blinka

### 2026-10-18 08:00 · Últimas horas
**Imagen:** `demo.gif`

#### X
> Faltan menos de 4 horas para entregar Custodio en el hackathon 30X, reto Blinka. Demo: {{DEMO_URL}} · Código: github.com/davidleonb27/custodio-blinka. El reto sigue abierto: {{intentos}} intentos, {{indebidos}} pagos indebidos. #30X #RetoBlinka

#### LinkedIn
> Hoy a las 11:59 a. m. cerramos la entrega de Custodio en el hackathon 30X, reto Blinka. Gracias a quienes intentaron romperlo.
>
> Contador de la demo en este momento: {{intentos}} intentos y {{indebidos}} pagos indebidos. Lo que aún no medimos lo dejamos escrito como NO MEDIDO en el README.
>
> Demo: {{DEMO_URL}}. Código abierto (MIT): github.com/davidleonb27/custodio-blinka. Equipo DreamMakers: Adriano Joao Souza Reyna, Juan David Leon y Leober Ramos. #30X #Blinka
