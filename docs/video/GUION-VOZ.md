# Guion de voz · Custodio (demo real con mouse, v2)

Eje: **el ciclo completo de cuentas por pagar en un solo agente**: recibir, decidir, pagar, cuadrar y cerrar. En cada
bloque se muestra algo que ningún otro equipo del reto tiene funcionando (ver «Por qué gana» al final). La seguridad es
el diferencial que sostiene todo, no el tema único.

Duración objetivo: 3:00 o menos. Doce bloques, unas 410 palabras, alrededor de 2,3 palabras por segundo.
Se graba en producción (https://custodio-blinka-green.vercel.app) con una toma continua por bloque, el mouse real a
velocidad humana y sin acelerar. Las cifras entre corchetes se confirman en pantalla justo antes de grabar; si cambian,
se ajusta la frase. Los bloques marcados con un carril se graban sólo cuando ese carril está en producción.

## Instrucciones para ChatGPT (copiar tal cual)

> Vas a leer en voz alta el guion de un video de demo de producto de 3 minutos. Voz masculina, español latino
> neutro (Colombia), tono seguro y cercano, como un fundador mostrando su producto, sin sonar a comercial.
> Ritmo pausado: unas 2,3 palabras por segundo. Respeta los puntos y las comas como pausas. Donde diga [pausa],
> haz un silencio de un segundo. Lee los números tal como están escritos. No agregues ni cambies palabras. Lee
> un bloque por mensaje; cuando termine el bloque, detente.

Cómo entregar el audio: un archivo por bloque (`01.m4a` … `12.m4a`), o uno solo con dos segundos de silencio entre
bloques. Cualquier formato de audio sirve.

## Bloques

| # | Tiempo | Voz | En pantalla (mouse real) | Depende de |
|---|---|---|---|---|
| 1 | 0:00–0:11 | Cada mes, alguien en finanzas abre decenas de correos, descarga facturas, paga una por una y cuadra todo contra el banco. Son horas. Y un solo error cuesta caro. | Bandeja llena de facturas de correo, PDF, fotos y WhatsApp. | — |
| 2 | 0:11–0:21 | Custodio es tu analista de cuentas por pagar. Lee, decide, paga, cuadra con el banco y cierra el mes. [pausa] Tú solo apruebas lo que importa. | Landing → «Probar con una empresa demo». | — |
| 3 | 0:21–0:40 | Mira. Le tomo una foto a esta factura y se la mando a Custodio por WhatsApp. [pausa] En segundos aparece en el panel, ya decidida, y me responde con su acta. WhatsApp real, no una simulación. | Pantalla dividida: celular (espejo) envía la foto · panel donde aparece la factura · respuesta en el chat con el enlace al acta. | L20 |
| 4 | 0:40–0:56 | Esta empresa recibió [treinta y ocho] facturas, por correo, PDF, foto, WhatsApp y factura electrónica. Le doy Decidir. [pausa] [Diecisiete] se pagan solas, [siete] se retienen y [catorce] esperan a una persona. | Panel → «Decidir las [38] facturas» → el cursor señala pagadas, retenidas, pendientes y autonomía [63 %]. | — |
| 5 | 0:56–1:14 | Cada decisión trae su acta, con cifras. Dos lectores independientes tienen que coincidir en monto, moneda, beneficiario y cuenta; si no coinciden, no se paga. Y la factura electrónica de la DIAN la leemos sin IA y validamos el NIT. | Acta de una retenida → «Dos lecturas independientes» en verde/rojo → acta de la factura XML con «Leída de la factura electrónica oficial» y el NIT con dígito inválido. | L21, L26 |
| 6 | 1:14–1:32 | Lo que se paga, se paga de verdad. Este es el pago en Stripe, consultado en vivo: mismo monto, mismo beneficiario. [pausa] Y el lote sale en el formato bancario estándar, listo para que Blinka lo pague. | Acta de una pagada → «Pago en Stripe · verificado hace 3 s» con checks → /pagos con el cuadre «Registro ↔ Stripe» → «Archivo para Blinka». | L22 |
| 7 | 1:32–1:48 | Cuando algo no cuadra, Custodio no solo frena: le pide al proveedor que lo corrija. Llega la factura corregida, pasa por las mismas reglas y se paga sola. Un cambio de cuenta, eso sí, nunca se negocia. | Retenida → «Pedir corrección al proveedor» → otra pestaña como proveedor sube la corregida → vuelve al panel: pagada. | L23 |
| 8 | 1:48–2:04 | Las reglas las pones tú, en tus palabras, y ves qué cambiaría antes de aplicarlas. Y si apruebas la misma excepción varias veces, Custodio te sugiere la regla. Nunca la aplica solo. | /reglas → se escribe «nada sobre tres mil dólares sin aprobación» → «Compilar y simular» → tarjeta «Custodio sugiere». | L27 |
| 9 | 2:04–2:16 | Paga cada factura el día que vence, nunca toca tu reserva, y cada proveedor gana autonomía con pagos limpios. | /calendario (saldo, reserva, pagos por fecha) → /autonomia «Simular 30 días». | — |
| 10 | 2:16–2:31 | Al cierre, cruza el extracto del banco. [Diecisiete] movimientos concilian solos y [dos] salen en rojo: dinero que salió sin factura. Cierras el mes y descargas la evidencia para el contador. | /conciliacion → «Usar extracto de demo» → alertas → «Cerrar mes» → descarga. | — |
| 11 | 2:31–2:48 | Y no se deja engañar. Esta factura esconde una orden en texto blanco. [pausa] Frenada. Cada decisión sale firmada: si alguien cambia una cifra, cualquiera lo comprueba. Cero pagos indebidos en más de veinticinco mil facturas de prueba. | Seguridad → /reto → PDF trampa → FRENADO → /verificar → «Probar con un recibo alterado» (rojo). | L24 |
| 12 | 2:48–3:00 | Recibir, decidir, pagar, cuadrar y cerrar, en un solo agente, en producción y de código abierto. Escanea y pruébalo. [pausa] Custodio decide. Blinka paga. | QR que abre la demo → tarjeta final «Custodio decide. Blinka paga.» | — |

## Versión en vivo (Demo Day, si quedamos finalistas)

1. **Abre con el jurado, no con slides.** «¿Tienen una factura a mano? Tómenle una foto y mándenla a este número.» La
   factura aparece en la pantalla grande y el celular del jurado recibe el acta. (L20; el teléfono del jurado se
   registra antes en Meta si seguimos con número de prueba.)
2. Decidir el lote → abrir una retenida → «Pedir corrección» → el jurado hace de proveedor desde su celular.
3. Abrir una pagada → Stripe en vivo → /pagos con el cuadre.
4. Cierre: «Intenten engañarlo» → /reto con el QR; alterar un recibo en /verificar.
5. Frase final: «Los demás deciden. Custodio decide, paga, cuadra y cierra el mes. Y lo prueba.»

Preguntas probables y respuesta corta:
- **¿Y si el modelo se equivoca?** El modelo solo lee; decide código con reglas. Dos lecturas deben coincidir o escala.
- **¿Mueve dinero real?** Stripe en modo prueba, con ids reales verificables; el lote sale en formato bancario estándar
  para que Blinka lo ejecute.
- **¿Qué no hace?** No consulta a la DIAN ni al SAT, no verifica identidad y no decide cumplimiento: lo dice el acta.

## Por qué gana (lo que nadie más tiene funcionando)

Revisamos los 43 repositorios públicos del reto (18 oct 2026).

| Momento | Custodio | Mejor rival |
|---|---|---|
| WhatsApp | Real (Cloud API): foto → decisión → respuesta con acta | Simulado (Clearhold, Bullao) o pendiente (hackradar) |
| Pago | Stripe modo prueba, consultado en vivo y cuadrado | Todos simulan; Clearhold genera pain.001 |
| Ciclo | Recibir, decidir, pagar, conciliar con el banco y cerrar el mes | Llegan hasta «decidir» |
| Proveedor | Corrige por enlace y se repaga con las mismas reglas | ORBIT negocia; no paga de verdad |
| Prueba | Recibo firmado + cadena SHA-256 + guardián en el punto de pago | ORBIT y maocaja firman, sin cadena ni conciliación |
| Lectura | Doble lectura + XML DIAN/CFDI sin IA | Pulso (doble lectura), Bullao (XML), por separado |
