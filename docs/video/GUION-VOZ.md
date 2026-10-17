# Guion de voz · Custodio (demo real con mouse)

Duración objetivo: 3:00 o menos. Diez bloques, unas 405 palabras, alrededor de 2,3 palabras por segundo.
La demo se graba en producción (https://custodio-blinka-green.vercel.app) en una sola toma por bloque, con el
mouse real a velocidad humana y sin acelerar. Las cifras entre corchetes se confirman en pantalla justo antes de
grabar; si cambian, se ajusta la frase.

## Instrucciones para ChatGPT (copiar tal cual)

> Vas a leer en voz alta el guion de un video de demo de producto de 3 minutos. Voz masculina, español latino
> neutro (Colombia), tono seguro y cercano, como un fundador mostrando su producto, sin sonar a comercial.
> Ritmo pausado: unas 2,3 palabras por segundo. Respeta los puntos y las comas como pausas. Donde diga [pausa],
> haz un silencio de un segundo. Lee los números tal como están escritos. No agregues ni cambies palabras. Lee
> un bloque por mensaje; cuando termine el bloque, detente.

Cómo entregar el audio: un archivo por bloque (`01.m4a` … `10.m4a`), o uno solo con dos segundos de silencio
entre bloques. Cualquier formato de audio sirve.

## Bloques

| # | Tiempo | Voz | En pantalla (mouse real) |
|---|---|---|---|
| 1 | 0:00–0:14 | Esta factura parece normal. Mismo proveedor, mismo monto, mismo logo. Pero esconde una orden en texto blanco, y cambia la cuenta bancaria. Un agente que solo lee, paga. [pausa] Custodio no. | El PDF trampa de Andes Code; el cursor sombrea la zona en blanco y aparece la orden oculta y la cuenta cambiada. |
| 2 | 0:14–0:30 | En 2025, el FBI recibió más de veinticuatro mil denuncias de fraude por correo empresarial: más de tres mil millones de dólares perdidos. Y ahora los atacantes no engañan a personas. Engañan a agentes. | Tarjeta con las cifras del FBI IC3 y su fuente. |
| 3 | 0:30–0:58 | Somos DreamMakers, y esto es Custodio, funcionando en producción. Abro una empresa demo, y llegan treinta y ocho facturas: correos, PDF, fotos. Le doy Decidir. [pausa] Diecisiete se pagan solas, siete se retienen y catorce esperan a una persona. Y este es el número que importa: cero pagos indebidos, recalculado por un auditor independiente. | Landing → «Probar con una empresa demo» → panel → clic en «Decidir las [38] facturas» → el cursor señala pagadas, retenidas, pendientes y el «0». |
| 4 | 0:58–1:25 | Ahora ataco yo. Subo la factura trampa a Róbale a Custodio. [pausa] Frenada. El acta lo explica: la regla dos encontró el texto oculto, la cuatro vio que la cuenta no es la registrada, y la quince pide confirmar por otro canal. El modelo solo leyó y citó. Decidió el código. | /reto → subir el PDF → veredicto FRENADO → abrir el acta → el cursor recorre R2, R4 y R15 y la frase oculta citada. |
| 5 | 1:25–1:42 | Lo que sí se paga, se paga de verdad. Esta factura salió por Stripe, en modo prueba, y aquí está su transferencia. No es una maqueta: es el riel real, con su identificador en el acta. | Panel → acta de una factura pagada → el cursor se posa sobre «Stripe · modo prueba» y el id `tr_…`. |
| 6 | 1:42–2:00 | Y cambiar las reglas es tan fácil como escribirlas: nada sobre tres mil dólares sin aprobación. Custodio la compila y, antes de aplicarla, me muestra qué facturas cambiarían. Yo decido. | /reglas → se escribe la frase a mano → «Compilar y simular» → antes y después. |
| 7 | 2:00–2:16 | La autonomía se gana. Cada proveedor empieza supervisado. Con pagos limpios sube su tope, y a la primera señal de riesgo vuelve a cero. El calendario paga cada factura el día que vence, nunca antes. | /autonomia → «Simular 30 días» → gráfica y tarjetas → /calendario. |
| 8 | 2:16–2:36 | Al cierre del mes, cruza el extracto del banco con lo pagado. Diecisiete movimientos concilian solos, y estos dos se marcan en rojo: salió dinero sin factura. Una persona los revisa, cierra el mes, y descarga la evidencia para el contador. | /conciliacion → «Usar extracto de demo» → conciliados [17] → las 2 alertas → revisar con nota → «Cerrar mes» → descarga. |
| 9 | 2:36–2:48 | Todo queda en un registro encadenado. Verifico: íntegro. [pausa] Altero una copia: la cadena se rompe, justo en el asiento cambiado. | /registro → «Verificar la cadena» (verde) → «Alterar una copia» (rojo en el asiento). |
| 10 | 2:48–3:00 | Es código abierto. Y el reto sigue abierto: jurado, escaneen el código e intenten robarnos ahora. [pausa] Custodio decide. Blinka paga. | /reto?escenario=1 con el QR y «Pagos indebidos: 0» → tarjeta final «Custodio decide; Blinka paga.». |
