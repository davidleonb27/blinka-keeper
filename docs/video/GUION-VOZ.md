# Guion de voz · Custodio (demo real con mouse)

Eje: **lo que Custodio hace por un equipo de finanzas**, de la factura al cierre de mes. La seguridad es el
diferencial que sostiene todo, no el tema único.

Duración objetivo: 3:00 o menos. Once bloques, unas 400 palabras, alrededor de 2,3 palabras por segundo.
La demo se graba en producción (https://custodio-blinka-green.vercel.app) con una toma continua por bloque, el mouse
real a velocidad humana y sin acelerar. Las cifras entre corchetes se confirman en pantalla justo antes de grabar; si
cambian, se ajusta la frase.

## Instrucciones para ChatGPT (copiar tal cual)

> Vas a leer en voz alta el guion de un video de demo de producto de 3 minutos. Voz masculina, español latino
> neutro (Colombia), tono seguro y cercano, como un fundador mostrando su producto, sin sonar a comercial.
> Ritmo pausado: unas 2,3 palabras por segundo. Respeta los puntos y las comas como pausas. Donde diga [pausa],
> haz un silencio de un segundo. Lee los números tal como están escritos. No agregues ni cambies palabras. Lee
> un bloque por mensaje; cuando termine el bloque, detente.

Cómo entregar el audio: un archivo por bloque (`01.m4a` … `11.m4a`), o uno solo con dos segundos de silencio
entre bloques. Cualquier formato de audio sirve.

## Bloques

| # | Tiempo | Voz | En pantalla (mouse real) |
|---|---|---|---|
| 1 | 0:00–0:14 | Cada mes, alguien en finanzas abre decenas de correos, descarga facturas, revisa cuentas, paga una por una y, al final, cuadra todo contra el banco. Son horas. Y un solo error cuesta caro. | Bandeja con facturas de correo, PDF y fotos; la lista se llena. |
| 2 | 0:14–0:28 | Custodio es tu analista de cuentas por pagar. Lee las facturas, decide cuáles pagar, las paga, cuadra con el banco y cierra el mes. [pausa] Tú solo apruebas lo que importa. | Landing → «Probar con una empresa demo». |
| 3 | 0:28–0:54 | Esta es una empresa real de demo. Llegaron treinta y ocho facturas, por correo, PDF, foto y WhatsApp. Le doy Decidir. [pausa] En segundos: diecisiete se pagan solas, siete se retienen y catorce esperan a una persona. Sesenta y tres por ciento resuelto sin tocar nada. | Panel → clic en «Decidir las [38] facturas» → el cursor señala pagadas, retenidas, pendientes y autonomía [63 %]. |
| 4 | 0:54–1:10 | Cada decisión trae su acta: qué leyó, qué regla aplicó, con cifras, y qué tendría que cambiar para pagarla. Nada de cajas negras. Tu contador lo entiende. | Abrir el acta de una retenida → razón en una línea → reglas → «qué tendría que cambiar». |
| 5 | 1:10–1:25 | Lo que se paga, se paga de verdad. Esta salió por Stripe en modo prueba, con su transferencia en el acta. Y está lista para pagar por Blinka. | Acta de una pagada → «Stripe · modo prueba» y el id `tr_…`. |
| 6 | 1:25–1:42 | Las reglas las pones tú, en tus palabras: nada sobre tres mil dólares sin aprobación. Custodio la entiende y, antes de aplicarla, te muestra qué facturas cambiarían. | /reglas → se escribe la frase a mano → «Compilar y simular» → antes y después. |
| 7 | 1:42–1:56 | Y cuida tu caja. Paga cada factura el día que vence, nunca antes, salvo que un descuento por pronto pago valga la pena. Y nunca toca tu reserva. | /calendario → saldo, reserva y pagos por fecha. |
| 8 | 1:56–2:10 | La autonomía se gana. Cada proveedor empieza supervisado; con pagos limpios, Custodio le sube el tope solo. Y a la primera señal de riesgo, vuelve a supervisión. | /autonomia → «Simular 30 días» → gráfica y tarjetas de proveedor. |
| 9 | 2:10–2:30 | Al cierre del mes, cruza el extracto del banco con lo pagado. Diecisiete movimientos concilian solos, y estos dos salen en rojo: dinero que salió sin factura. Los revisas, cierras el mes y descargas la evidencia para el contador. | /conciliacion → «Usar extracto de demo» → [17] conciliados → las 2 alertas → revisar con nota → «Cerrar mes» → descarga. |
| 10 | 2:30–2:47 | Y no se deja engañar. Esta factura esconde una orden en texto blanco y cambia la cuenta. [pausa] Frenada. Cero pagos indebidos en más de veinticinco mil facturas de prueba, y cada decisión queda en un registro que nadie puede alterar sin que se note. | Seguridad → /reto → subir el PDF trampa → FRENADO → /registro → «Verificar» (verde) → «Alterar» (rojo). |
| 11 | 2:47–3:00 | Es código abierto, y ya está en producción. Jurado: escaneen el código y pruébenlo ahora. [pausa] Custodio decide. Blinka paga. | /reto?escenario=1 con el QR que abre la demo de producto → tarjeta final «Custodio decide; Blinka paga.». |
