# Cómo paga Custodio

> **Custodio decide; el riel paga.** Hoy: Stripe en modo prueba. En producción: el riel de la empresa, por ejemplo
> Blinka (ACH, wire, Bre-B, SPEI, Pix).

El motor y el auditor deciden qué se paga. El riel sólo ejecuta lo que ya quedó decidido: no lee facturas, no evalúa
reglas y no puede pagar algo que el motor retuvo o que el auditor vetó. Cambiar de riel no cambia ninguna regla ni quién
decide.

## Recorrido de un pago

1. `invoice_service.decide` corre el motor y el auditor, como siempre.
2. Si la decisión queda pagada (`paid_auto` o `paid_human`) y el auditor no la vetó, `payment_service.execute` arma una
   `PaymentOrder` (llave de idempotencia, espacio, factura, beneficiario, nombre registrado del proveedor, monto en USD,
   moneda y monto originales, enlace al acta) y se la pasa al riel.
3. El riel devuelve un recibo (`PaymentExecution`): riel, estado (`executed`, `simulated` o `failed`), id externo,
   enlace al dashboard, hora y, si falló, un error en español sin secretos.
4. El recibo queda en la tabla `payment_executions` (única por espacio y factura), en el acta (`Decision.execution`) y
   en el asiento `payment` del registro encadenado, que agrega `rail`, `execution_status`, `external_id` y
   `livemode: false`.

Una ejecución fallida no deshace la decisión: la factura sigue pagada por el motor (el saldo ya la descuenta) y el acta
muestra el error con el botón «Reintentar pago» (`POST /api/v1/decisions/{id}/execute`). Reintentar un pago que ya salió
devuelve el mismo recibo y no llama al riel.

## Quién paga y quién no

| Superficie | ¿Ejecuta? | Por qué |
|---|---|---|
| Panel: procesar facturas | sí | es la empresa pagando sus facturas |
| Panel: aprobar una factura | sí, sólo después de aprobar | la persona autoriza; antes no sale nada |
| Firewall y MCP | no | responden a otro agente; ese agente paga con su riel |
| «Róbale a Custodio» | no | cada intento corre en un espacio aislado |
| Red team | no | los ataques corren en un espacio aislado |

Hay dos guardias: `decide` sólo ejecuta cuando quien llama lo pide (`execute_payments=True`, sólo el panel), y aun así
nunca en un espacio que no sea de un visitante. Un test lo prueba para el firewall, el reto y el red team con facturas
legítimas que sí quedan pagadas en papel.

## Los dos rieles

| `CUSTODIO_PAYMENT_RAIL` | `STRIPE_SECRET_KEY` | Riel activo |
|---|---|---|
| sin definir o `simulated` | cualquiera | `simulated`: no mueve dinero ni usa la red; el recibo lo dice |
| `stripe_test` | empieza por `sk_test_` | `stripe_test` |
| `stripe_test` | empieza por `sk_live_` o `rk_live_` | `simulated`, con un aviso en el log (sin la clave) |
| `stripe_test` | vacía u otra cosa | `simulated`, con un aviso en el log |

`GET /api/v1/health` dice cuál está activo en `payment_rail`. La web lo muestra en el panel y en cada acta.

## Stripe en modo prueba

- **Cuenta del proveedor.** La primera vez que se paga a un beneficiario se crea una cuenta conectada *Custom* de prueba
  en EE. UU. con la capacidad `transfers`, usando los valores mágicos de Stripe para que quede verificada al instante:
  persona natural, nacimiento 1901-01-01, `ssn_last_4` 0000, dirección `address_full_match`, cuenta bancaria
  `btok_us_verified`, aceptación de términos con fecha e IP fijas y `business_profile.name` con el nombre del proveedor.
  El mapeo (beneficiario + nombre normalizado → `acct_…`) vive en la tabla global `stripe_accounts`, así que los espacios
  de demo reutilizan las mismas cuentas en vez de crear cuentas sin fin.
- **Transferencia.** Un `Transfer` en USD por `amount_base` redondeado a centavos hacia esa cuenta, con metadata
  `{workspace_id, invoice_id, acta_url}`, `transfer_group = workspace:factura` e `Idempotency-Key = workspace:factura`.
  El recibo enlaza a `https://dashboard.stripe.com/test/connect/transfers/<tr_id>`.
- **Saldo de prueba.** Si Stripe responde `balance_insufficient`, se recarga el saldo de prueba de la plataforma con un
  PaymentIntent confirmado con `pm_card_bypassPending` por lo que falta más 1.000 USD y se reintenta una vez. Sólo
  ocurre con una clave `sk_test_`.
- **Errores.** Cualquier error de Stripe se vuelve un recibo `failed` con un mensaje en español armado sólo con el tipo y
  el código del error (el mensaje original de Stripe puede citar parte de la clave). Nunca sale una excepción hacia la API.
- **Topes.** Como mucho 40 transferencias por espacio y 400 por día UTC en todo el despliegue. Al pasarlos, el recibo es
  `failed` con «Tope de pagos de prueba alcanzado». Un espacio cuya moneda base no es USD tampoco paga por este riel.

### Idempotencia: lo que la API real obliga a hacer distinto

Stripe guarda durante 24 horas la respuesta de cada llave de idempotencia, **errores incluidos**. Si el primer intento
falló con un error definitivo, reintentar con la misma llave devolvería el mismo error. Por eso:

- el primer intento usa exactamente `workspace:factura`; cada reintento usa `workspace:factura:intento-N`;
- la transferencia tras una recarga usa `…:tras-recarga`, y la recarga, `…:recarga`;
- antes de enviar, el riel busca una transferencia del mismo `transfer_group`. Si una respuesta se perdió en la red pero
  la transferencia sí salió, el reintento la encuentra y la reutiliza en vez de pagar dos veces.

Si la base de datos revierte después de que Stripe aceptó la transferencia, el siguiente intento repite la llave original
y Stripe devuelve la misma transferencia (dentro de sus 24 horas) o el riel la encuentra por su grupo.

### El SDK oficial

Se usa `stripe==16.0.0` (fijo en `apps/api/pyproject.toml` y `uv.lock`), que fija a su vez la versión de la API
(`2026-09-30.endive`). Lo que da: la versión de la API no cambia por debajo sin un cambio de código; codifica los
parámetros anidados como los espera Stripe; manda la llave de idempotencia y reintenta los errores de red con la misma
llave (`max_network_retries=2`); tipa los parámetros (mypy rechaza un campo que no existe en esa versión) y convierte los
errores HTTP en excepciones con su código. Sin él habría que reimplementar todo eso a mano con `httpx`, y un error de
codificación o un reintento sin llave podría crear una transferencia doble o romperse en silencio al cambiar la API.

Los tests no usan la red: un transporte falso (`tests/payments/stripe_fake.py`) va debajo del SDK real, así que se
ejercitan su codificación, sus cabeceras y su lectura de errores. El falso repite, como Stripe, la respuesta guardada de
una llave ya usada. El test `tests/payments/test_stripe_live.py` (marcado `live`) hace una transferencia real de 1 USD en
modo prueba con `CUSTODIO_LIVE_TESTS=1` y una `STRIPE_SECRET_KEY` de prueba.

## Por qué modo prueba

El reto deja fuera el dinero real, las pasarelas y el KYC. El modo prueba de Stripe es un riel real (la misma API, las
mismas cuentas conectadas, las mismas transferencias, visibles en el dashboard) con dinero de prueba. Demuestra que la
decisión de Custodio llega hasta un pago verificable sin que nadie pueda perder plata, y la guardia de claves `live` hace
que un error de configuración no pueda convertirse en un pago real.

## Cómo se conectaría Blinka

Blinka es el riel de la empresa: ya tiene a los beneficiarios verificados y mueve el dinero por ACH, wire, Bre-B, SPEI o
Pix. Conectarlo es escribir un `BlinkaRail` con el mismo protocolo (`custodio/payments/port.py`):

```python
class PaymentRail(Protocol):
    @property
    def name(self) -> str: ...
    def execute(self, order: PaymentOrder) -> PaymentReceipt: ...
```

`execute` llamaría a la API de pagos de Blinka con la `idempotency_key` de la orden, el beneficiario y el monto, y
devolvería el id del pago y su enlace. No cambia el motor, ni el auditor, ni el registro, ni quién decide: la elección del
riel es una línea en `choose_rail`.
