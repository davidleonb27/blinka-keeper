# Pitch de Blinka Keeper · para quien presenta

Tres minutos, hablado con tus palabras. Lo que va en **negrita** se dice mirando al jurado. Demo en vivo:
https://blinka-keeper.vercel.app · WhatsApp de la demo: **+57 313 631 4294**.

## 1. El problema (0:00–0:25)

«Cada mes, un equipo de finanzas abre decenas de correos, descarga facturas, revisa cuentas, paga una por una y al
final cuadra todo contra el banco. Son horas. Y basta una factura con la cuenta bancaria cambiada para perder plata:
solo en Estados Unidos, el fraude por correo empresarial costó más de tres mil millones de dólares en 2025.

Blinka le paga a proveedores en todo el mundo. **La pregunta no es cómo pagar: es qué se debe pagar.** Eso es lo que
resuelve Blinka Keeper.»

## 2. Qué es (0:25–0:45)

«**Blinka Keeper es un analista de cuentas por pagar que trabaja solo, dentro de las reglas de la empresa.**
Recibe la factura por donde llegue, la lee, decide si se paga, se frena o se le pregunta a una persona, la paga, la
cuadra con el banco y cierra el mes. La IA solo lee; **decide el código**, con quince reglas que cualquiera puede auditar.»

## 3. La demo (0:45–2:15)

1. **WhatsApp real.** Mandas la foto de una factura al número de la empresa. En segundos aparece en el panel, decidida,
   y responde con su acta. *(Ningún otro equipo tiene WhatsApp funcionando de verdad.)*
2. **Decide el lote.** Treinta y nueve facturas: diecisiete se pagan solas, siete se frenan, quince esperan a una
   persona. **Cero pagos indebidos**, y un auditor independiente lo confirma.
3. **El acta.** Cada decisión explica por qué, con cifras, y qué tendría que cambiar. **Dos modelos de dos empresas
   distintas (Claude y Gemini)** leen cada factura; si no coinciden en el monto o la cuenta, no se paga. La factura
   electrónica de la DIAN se lee sin IA y se valida el NIT.
4. **El pago es real.** Abres una pagada: **Stripe confirma la transferencia en vivo**, campo por campo. Y el lote sale
   como archivo bancario estándar **ISO 20022 (pain.001), listo para que Blinka lo pague.**
5. **No solo frena: resuelve.** Si el monto no cuadra, le pide al proveedor que corrija por un enlace; la factura
   corregida se paga sola con las mismas reglas. Un cambio de cuenta nunca se negocia.
6. **Aprende sin perder el control.** «Aprobar solo esta vez» o «actualizar el acuerdo». Si apruebas lo mismo varias
   veces, te sugiere la regla; **nunca la aplica sola.**
7. **Cierre de mes.** Cruza el extracto del banco: lo que salió sin factura sale en rojo. Evidencia para el contador.
8. **Prueba de todo.** Cada decisión sale con **recibo firmado** que cualquiera verifica, en un registro encadenado.
   Si alguien cambia una cifra, se nota.

## 4. Por qué es el mejor (2:15–2:45)

«Revisamos los cuarenta y tres proyectos públicos de este reto. **Todos deciden. Ninguno paga de verdad.**

- Somos los únicos con **pagos reales en Stripe** verificados en vivo, y con el ciclo completo hasta el cierre de mes.
- Somos los únicos con **WhatsApp real**: los demás lo simulan o lo dejaron pendiente.
- Lo mejor de cada rival lo tenemos junto: doble lectura con dos empresas, recibos firmados, corrección con el
  proveedor, factura electrónica sin IA y aprobaciones que enseñan.
- Y está en producción, con más de mil seiscientas pruebas automáticas y código abierto.»

## 5. Qué le sirve a Blinka (2:45–3:00)

«Para Blinka, Blinka Keeper es la capa que faltaba antes del pago: **decide qué pagar, con prueba**, y le entrega el
lote listo en formato bancario. Más pagos por cliente, menos fraude, y un argumento de confianza para empresas que
todavía pagan a mano. **Blinka Keeper decide. Blinka paga.** Escaneen el QR y pruébenlo ahora.»

## Preguntas probables

- **¿Y si la IA se equivoca?** La IA solo lee. Dos lectores de dos empresas deben coincidir; si no, escala. Decide
  código determinista y un auditor recalcula cada pago.
- **¿Mueve dinero real?** Stripe en modo prueba, con transferencias reales verificables. Para producción, el archivo
  pain.001 va directo a Blinka.
- **¿Cuánto cuesta por factura?** Centavos de dólar por lectura; hay un tope diario de gasto configurable.
- **¿Qué no hace?** No consulta a la DIAN ni al SAT, no verifica identidad y no decide cumplimiento: el acta lo dice.
- **¿Cómo lo adopta una empresa?** En /empezar sube sus proveedores y reglas; es autohospedable con un comando.

## La competencia, en corto

43 repositorios públicos del reto (revisados el 18 de octubre de 2026). Los más fuertes y qué tenemos frente a cada uno:

| Rival | Su mejor carta | Nosotros |
|---|---|---|
| Clearhold | Pitch y video pulidos, pain.001, bandeja simulada | pain.001 + pago real en Stripe + WhatsApp real |
| ORBIT | Negocia con el proveedor, recibos Ed25519 | Corrección con el proveedor + recibos firmados + registro encadenado |
| Pulso | Doble lectura Claude + Gemini, 400 pruebas | Doble lectura Claude + Gemini, más de 1.600 pruebas |
| Bullao | XML DIAN/CFDI, aprobar una vez vs. acuerdo | Lo mismo, más pago real y conciliación |
| Centinela | Doble lectura con intervalo de confianza | Doble lectura y medición honesta con «lo que no medimos» |

**¿Ganamos?** No hay garantía: decide el jurado. Pero hoy somos el producto más completo del reto y el único que cierra
el ciclo con dinero real. Lo que puede costarnos es un error en vivo o un video flojo; por eso cada pantalla está
probada en producción y el guion está ensayado.
