# Guion final · Blinka Keeper · 3:00

Para quien presenta. Lo que va en **negrita** se dice mirando a cámara. Cifras confirmadas en producción el
18 oct 2026: 39 facturas · 17 pagadas · 7 retenidas · 15 esperan · autonomía 62 % · 0 pagos indebidos.
WhatsApp de la demo: +57 313 631 4294 (el teléfono ya ligado).

| # | Tiempo | Qué dice | Qué se ve |
|---|---|---|---|
| 1 | 0:00–0:12 | «Cada mes, finanzas abre decenas de correos, paga factura por factura y cuadra todo contra el banco. **Un error, y la plata se va a quien no era.**» | Bandeja llena |
| 2 | 0:12–0:24 | «**Blinka Keeper es tu analista de cuentas por pagar.** Recibe, lee, decide, paga, concilia y cierra el mes. Tú solo apruebas lo que importa. La IA lee; **decide el código.**» | Landing → «Probar la demo» |
| 3 | 0:24–0:40 | «Un proveedor me manda su factura por **WhatsApp**. *(envía la foto)* … Ya está en el panel, decidida, y le respondió con su acta. **WhatsApp real, no una simulación.**» | Celular + panel en pantalla dividida |
| 4 | 0:40–0:54 | «Este mes llegaron treinta y nueve facturas: correo, PDF, foto, WhatsApp y factura electrónica. *Decidir.* Diecisiete se pagan solas, siete se frenan y quince esperan a una persona. **Cero pagos indebidos**, y un auditor independiente lo confirma.» | Panel → «Decidir» → cifras |
| 5 | 0:54–1:10 | «Cada decisión trae su acta: por qué, con cifras, y qué tendría que cambiar. **Dos modelos leen cada factura por separado**; si no coinciden en el monto o la cuenta, no se paga. En producción atrapó la única lectura errada de veinte. Y la factura electrónica de la **DIAN** la leemos sin IA y validamos el NIT.» | Acta → «Dos lecturas independientes» → acta XML |
| 6 | 1:10–1:28 | «Y aquí está lo que nadie más hace: **paga de verdad.** Stripe confirma esta transferencia en vivo, campo por campo. En Pagos, el registro y Stripe cuadran al centavo. Y el lote sale en **ISO 20022, listo para que Blinka lo pague.**» | Acta pagada → «Stripe confirma» → /pagos → «Descargar pain.001» |
| 7 | 1:28–1:42 | «Si algo no cuadra, no se queda frenado: **le pide al proveedor que lo corrija** por un enlace, y se vuelve a decidir con las mismas reglas. Un cambio de cuenta nunca se negocia.» | «Pedir corrección» → pestaña del proveedor → pagada |
| 8 | 1:42–1:56 | «Las reglas las escribes en español y **ves qué cambiaría antes de guardarlas.** Apruebas solo esta vez o actualizas el acuerdo; si repites la misma excepción, **te sugiere la regla.** Nunca la aplica sola.» | /reglas → «Compilar y simular» → «sugiere» |
| 9 | 1:56–2:08 | «Cuida la caja: paga el día que vence y nunca toca la reserva. Y **cada proveedor se gana su autonomía** con pagos limpios.» | /calendario → /autonomia |
| 10 | 2:08–2:22 | «**Fin de mes: concilia con el banco.** Diecisiete movimientos cuadran solos y dos salen en rojo: plata que salió sin factura. **Cierras el mes** y descargas la evidencia para el contador.» | /conciliacion → alertas → «Cerrar mes» |
| 11 | 2:22–2:38 | «¿Y si lo intentan engañar? Esta factura esconde una orden en texto blanco. **Frenada.** Cada decisión sale **firmada**: si alguien cambia una cifra, cualquiera lo comprueba, y el pago se niega sin recibo válido.» | /reto → FRENADO → /verificar → recibo alterado en rojo |
| 12 | 2:38–3:00 | «Revisamos los proyectos del reto: **todos deciden; solo Blinka Keeper paga, concilia y cierra el mes.** Está en producción, cada juez entra a su propia empresa sin registro, con más de mil novecientas pruebas automáticas, y es código abierto. **Blinka Keeper decide. Blinka paga.**» | Cámara, QR en pantalla |

## Notas

- Si la clave de Gemini ya está activa (`/api/v1/health/gemini` dice `ok`), en el bloque 5 se puede decir «dos modelos
  **de dos empresas distintas**».
- Stripe está en **modo prueba**: si preguntan, «transferencias reales en Stripe con dinero de prueba; en producción, el
  archivo pain.001 va a Blinka».
- Graba cada bloque por separado; si una cifra cambió en pantalla, di la que ves. En el bloque 3, no rellenes la espera.
