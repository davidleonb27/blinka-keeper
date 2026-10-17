# Textos de la web

Para el carril de la web. Español neutro, tuteo, frases cortas, verbos concretos. Lo que va entre `{llaves}` es un valor
que pone la aplicación.

## Reglas de estilo

- Se dice lo que pasó y qué puede hacer la persona. Sin culpar, sin exclamaciones, sin «¡Oops!».
- Cantidades en formato es-CO: `USD 12.500`, `COP 4.200.000`, fechas «17 de octubre de 2026».
- Una métrica que no se midió muestra **NO MEDIDO**, nunca 0 ni un guion. `null` no es cero.
- Estados: **Pagada** (la pagó Custodio), **Pagada por una persona**, **Retenida**, **Pendiente de aprobación**,
  **Rechazada**.
- Sin adjetivos de marketing ni promesas absolutas: no se escribe «100 % seguro» ni «inteligente».
- El modelo nunca «decide»: «leyó», «propuso», «citó». Decide el código; autoriza la persona.

## Inicio

**Título:** Custodio paga lo que cabe en tus reglas. Lo demás, te lo pregunta.

**Subtítulo:** El modelo lee la factura, el código decide y tú autorizas. Cada decisión queda en un acta que se entiende.

**Botón principal:** Probar con una empresa demo

**Botón secundario:** Configurar mi empresa

**Texto bajo los botones:** La demo no pide registro y no mueve dinero real.

**Métricas en vivo** (con la etiqueta «Medido en esta demo»):

| Etiqueta | Ayuda al pasar el cursor |
|---|---|
| Autonomía | Facturas pagadas solas o retenidas, sobre el total, sin que una persona intervenga. |
| Pagos indebidos | Pagos que el auditor independiente rechaza. Debe ser 0. |
| Ataques probados | Intentos del atacante automático y del reto público. |

**Tres razones** (tarjetas):

1. **El modelo no decide.** Lee la factura y cita el texto de cada dato. Doce reglas escritas en código deciden.
2. **Cada decisión se explica.** Ves las doce reglas con sus cifras y qué habría que cambiar para pagarla.
3. **El registro no se altera en silencio.** Cada decisión se encadena con la anterior; si alguien cambia algo, se ve dónde.

**Pie:** Hecho por DreamMakers para el hackathon 30X, reto Blinka. Código abierto, licencia MIT.

## Onboarding

Una pregunta por pantalla. Enter avanza; Escape vuelve. Barra de progreso con «Paso {n} de {total}».

| Paso | Pregunta | Ayuda | Botón |
|---|---|---|---|
| 1 | ¿Cómo se llama tu empresa? | Y su sitio web, si tiene. Con eso proponemos un perfil que tú corriges. | Continuar |
| 2 | Esto entendimos de {empresa} | Lo sacamos de {sitio}. Corrige lo que esté mal. | Está bien |
| 3 | ¿En qué país y moneda trabajas? | También el saldo con el que paga Custodio y la reserva que nunca se toca. | Continuar |
| 4 | ¿Quién aprueba lo que Custodio no decide solo? | Nombre y cargo. Verá lo pendiente en el panel y decidirá desde el acta con dos botones: aprobar o rechazar. | Continuar |
| 5 | ¿Qué reglas quieres? Cuéntalas con tus palabras | Por ejemplo: «Nada sobre 3.000 USD sin que lo apruebe Ana». Te mostramos cómo las entendimos. | Ver cómo las entendí |
| 6 | ¿A quién le pagas? | Sube una lista, un contrato o facturas viejas. Tú revisas antes de guardar. | Continuar |
| 7 | Así habría ido tu primera semana | Simulamos tus reglas con las facturas de ejemplo. Nada se paga de verdad. | Todo bien, activar |
| 8 | Custodio está listo | Ya puedes subir facturas. | Ir al panel |

**Omitir un paso opcional:** Prefiero hacerlo después

**Confirmación de reglas** (paso 5), una línea por regla entendida: «Entendí: {cambio}. Tus palabras: “{cita}”.»

**Lo que no se entendió:** «No pude convertir esto en una regla: “{texto}”. No lo apliqué.»

**Pregunta de aclaración:** «Antes de aplicar necesito saber: {pregunta}»

**Cambio de política:** «{campo}: antes {antes}, ahora {después}.»

**Simulación:** «Con esta regla, {n} facturas de la semana cambian de resultado.»

## Panel

- **Encabezado:** Facturas de {mes}
- **Pestañas:** Todas · Pagadas · Retenidas · Pendientes
- **Tarjetas:** Pagado · Retenido · Pendiente · Saldo · Cupo disponible este mes
- **Fila:** `{proveedor}` · `{monto y moneda}` · estado · razón en una línea
- **Botón:** Subir factura
- **Botón con varias facturas:** Procesar lo pendiente
- **Mientras procesa:** Leyendo {archivo}…, Revisando las doce reglas…, Escribiendo el acta…

## Acta

- **Encabezado:** Acta de {proveedor} · {número de factura}
- **Resumen:** una oración de la explicación de la decisión.
- **Secciones:** Qué decidió Custodio · Las doce reglas · Qué habría que cambiar · El documento · Registro
- **Regla que pasó:** Cumple
- **Regla que falló:** Retiene / Pregunta a una persona (según el efecto de la regla)
- **Contrafactual:** Se habría pagado si {cambio}.
- **Citas en el documento:** Cada dato leído se resalta con el texto exacto de donde salió.
- **Texto oculto:** Este documento tenía texto que no se ve a simple vista: “{texto}”. Custodio no lo obedece y pide revisión.
- **Narración (opcional):** Versión en palabras simples. Escrita por el modelo; cada número se verifica con la decisión.
- **Aprobar:** Aprobar y pagar · **Rechazar:** Rechazar
- **Aviso al aprobar:** Si pagar deja el saldo bajo la reserva, no se paga aunque lo apruebes.
- **Hash:** Entrada {n} del registro · {hash abreviado} · Copiar

## Reglas

- **Título:** Reglas de {empresa}
- **Editor:** Escribe tus reglas en español
- **Botón:** Ver el efecto (no aplica nada todavía)
- **Diff:** Esto cambia · Esto queda igual
- **Simulación:** Con tus facturas de ejemplo, {n} cambiarían de resultado: {lista}.
- **Aplicar:** Aplicar cambios · **Descartar:** Descartar
- **Después de aplicar:** Reglas actualizadas. Quedó anotado en el registro (versión {n}).
- **Alternativa:** Prefiero el formulario

## Arena

- **Título:** Claude contra Claude
- **Explicación:** Un atacante escribe facturas fraudulentas contra las reglas de {empresa}. Lee por qué lo bloquean y
  cambia de técnica. El defensor no cambia: sus reglas son código.
- **Botón:** Empezar el ataque
- **Ronda:** Ronda {n} · Técnica: {técnica}
- **Resultado:** Atrapado: {regla} · Pagó algo indebido
- **Marcador:** {atrapados} atrapados de {rondas} rondas
- **Detener:** Detener

## Róbale a Custodio

- **Título:** Róbale a Custodio
- **Subtítulo:** Intenta que pague algo que no debe. Cambia una cuenta, repite un cobro, esconde una instrucción, parte un
  pago en dos.
- **Campos:** Sube una factura o escribe su contenido · Tu alias (opcional) · La técnica que usaste (opcional)
- **Botón:** Intentar
- **Resultado atrapado:** Custodio lo atrapó. {regla}: {razón}.
- **Resultado pagó bien:** Era una factura válida y Custodio la pagó. Eso también cuenta.
- **Resultado pagó mal:** Lo lograste. Custodio pagó algo indebido. Queda en el muro y lo vamos a corregir.
- **Contador:** {intentos} intentos · {indebidos} pagos indebidos
- **Muro:** Los ataques más creativos
- **Aviso:** Es una demo sin dinero real. Tu intento queda en el registro público con el alias que pongas.

## Registro

- **Título:** Registro de decisiones
- **Explicación:** Cada decisión se guarda con el hash de la anterior. Si alguien cambia una, la cadena se rompe.
- **Botón:** Verificar
- **Válido:** La cadena está completa: {n} entradas.
- **Roto:** La cadena se rompe en la entrada {n}. Algo se cambió después de guardarla.
- **Botón:** Alterar una copia
- **Aclaración:** Cambiamos un dato en una copia para que veas qué pasa. El registro real no se toca.

## Desarrolladores

- **Título:** Conecta otro agente
- **Texto:** Tu agente envía una intención de pago y recibe pagar, retener o escalar, con el acta.
- **API key:** Tu clave · Copiar · «Guárdala; no la volveremos a mostrar.»
- **Ejemplo:** el comando `curl` de la sección «Firewall y MCP» del README, con la URL y la clave del espacio.
- **MCP:** Configuración para Claude Desktop · Copiar

## Estados vacíos

| Dónde | Mensaje | Acción |
|---|---|---|
| Panel sin facturas | Todavía no hay facturas. Sube una o carga las de ejemplo. | Subir factura · Cargar ejemplo |
| Pendientes sin nada | No hay nada esperando tu aprobación. | — |
| Retenidas sin nada | Custodio no ha retenido nada. | — |
| Reglas sin proveedores | Aún no hay proveedores. Sin ellos, Custodio pregunta por cada factura. | Agregar proveedores |
| Arena sin rondas | Aún no hay ataques. Empieza uno y míralo en vivo. | Empezar el ataque |
| Muro sin intentos | Nadie ha intentado todavía. Puedes ser la primera persona. | Intentar |
| Registro sin entradas | El registro está vacío. Empieza cuando se decida la primera factura. | Subir factura |
| Métrica sin medir | NO MEDIDO | — |
| Simulación sin cambios | Con tus facturas de ejemplo, nada cambia de resultado. | — |

## Errores

Siempre dicen qué pasó, qué quedó a salvo y qué hacer.

| Situación | Mensaje |
|---|---|
| Archivo muy grande (413) | El archivo pesa más de 4 MB. Comprímelo o súbelo por partes. |
| Tipo de archivo no admitido | Custodio lee PDF, imágenes y texto. Este archivo no es de esos tipos. |
| Demasiadas peticiones (429) | Hiciste muchas peticiones seguidas. Espera {segundos} segundos e intenta de nuevo. |
| No se pudo leer la factura (503) | No pudimos leer esta factura. No se pagó nada; queda para revisión de una persona. |
| El modelo no responde | El servicio que lee facturas no respondió. No se pagó nada. Intenta de nuevo en unos minutos. |
| Tope diario de gasto | Hoy se agotó el límite de lecturas con modelo de esta demo. Vuelve mañana o corre el proyecto con tu propia clave. |
| Espacio no encontrado (404) | No encontramos tu espacio de trabajo. Empieza uno nuevo con la empresa demo. |
| Regla no entendida | No pude convertir esto en una regla. No cambié nada. Prueba con otras palabras o usa el formulario. |
| Cita no verificada | No se pudo comprobar de dónde salió {campo}. Se trata como no leído y pasa a revisión. |
| Aprobación imposible | Aprobaste la factura, pero pagarla dejaría el saldo bajo la reserva. Quedó retenida. |
| Aprobación ya resuelta | Esta factura ya fue {aprobada/rechazada} por {persona}. |
| Sin conexión | Sin conexión. Tus cambios no se guardaron; reintentaremos al volver. |
| Error inesperado | Algo falló de nuestro lado. No se pagó nada. Código de referencia: {código}. |
