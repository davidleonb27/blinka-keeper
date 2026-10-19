# Recibos firmados

> Cada decisión de Blinka Keeper sale con un recibo firmado con Ed25519 que un tercero verifica **sin acceso al sistema**:
> sólo con la clave pública. La cadena SHA-256 del registro prueba que nada cambió adentro; el recibo lo prueba afuera.

## Qué firma

`GET /api/v1/decisions/{id}/receipt` devuelve:

```json
{
  "format": "custodio-receipt/1",
  "algorithm": "Ed25519",
  "key_id": "cust-56475aa75463474c",
  "body": {
    "invoice":  { "id", "number", "received_at", "source", "document_id", "document_sha256" },
    "reading":  { "amount": { "value": "4200.00", "verified": true }, "…": "cada campo leído" },
    "rules":    [ { "rule_id": "R1", "outcome": "pass" }, "… las 15" ],
    "policy":   { "version", "sha256", "ledger_seq", "ledger_hash" },
    "decision": { "verdict": "pay | hold | escalate | reject", "status", "agent_verdict", "approved_by" },
    "payment":  { "beneficiary_id", "beneficiary_name", "account_last4", "account_sha256", "amount", "currency",
                  "amount_base", "base_currency", "rail", "external_id" },
    "ledger":   { "seq", "hash", "kind" },
    "issued_at", "workspace_id", "key_id", "format"
  },
  "signature": "base64( Ed25519( json_canónico(body) ) )",
  "field_digests": { "payment.amount": "sha256( json_canónico(valor) )", "…": "uno por campo" },
  "digests_signature": "base64( Ed25519( json_canónico(field_digests) ) )"
}
```

- `payment` sólo existe si la decisión fue pagar; la cuenta viaja como huella SHA-256 y últimos 4 dígitos.
  La huella no tiene sal: sirve para comprobar una cuenta que ya conoces, no para ocultarla (un número de cuenta
  corto se recupera probando combinaciones). Comparte el recibo como compartirías los datos del pago.
  `external_id` es el id de Stripe (`tr_…`) cuando el pago ya salió.
- `issued_at` es la hora del asiento de la decisión en el registro: la misma decisión da siempre el mismo recibo.
- JSON canónico: claves ordenadas, sin espacios, sin escapar acentos (`json.dumps(v, sort_keys=True,
  separators=(",", ":"), ensure_ascii=False)`). Todas las hojas del cuerpo son texto, enteros, booleanos o `null`.
- La segunda firma (`digests_signature`) es la que permite decir **qué campo** se alteró: si alguien cambia el monto,
  la firma del cuerpo falla pero la de los resúmenes sigue intacta, y el resumen de `payment.amount` ya no coincide.

## La clave

- Pública: `GET /api/v1/.well-known/custodio-receipt-key` → `key_id`, `public_key` (32 bytes en base64) y
  `public_key_pem`. `key_id` = `cust-` + los primeros 16 hex del SHA-256 de la clave pública.
- Privada: `CUSTODIO_RECEIPT_SIGNING_KEY` (PEM PKCS#8 o semilla de 32 bytes en base64 o hex). Si no está, se deriva con
  HKDF-SHA256 de `DATABASE_URL`: es el único secreto que todo despliegue ya tiene (lleva la contraseña de Neon) y su
  vida coincide con la de lo que el recibo señala, porque cada recibo nombra una posición del registro de esa base. Nunca
  se genera una clave al arrancar: un recibo de ayer tiene que verificar hoy. Con una base SQLite local la clave
  derivada sólo sirve para desarrollo, y el log lo avisa.

## Verificar

**En la web:** [`/verificar`](https://blinka-keeper.vercel.app/verificar) comprueba el recibo en el navegador (con la
clave pública) y en el servidor (`POST /api/v1/receipts/verify`), y dice «Válido: … la decisión fue «Pagar»» o
«Inválido: el campo monto fue alterado…». «Probar con un recibo alterado» toma un recibo de ejemplo firmado con la clave
real y le multiplica el monto.

**Con Python, sin instalar nada:** el paquete de cierre de mes (`evidence.zip`) trae `recibos/<factura>.json`,
`recibos/clave_publica.json` y `recibos/verificar_recibo.py` (Ed25519 del RFC 8032 con la biblioteca estándar):

```bash
curl -s https://blinka-keeper.vercel.app/api/v1/.well-known/custodio-receipt-key > clave_publica.json
python3 verificar_recibo.py recibo.json clave_publica.json
# VÁLIDO: firmado por Blinka Keeper; la decisión fue «pay»
# INVÁLIDO: se alteró payment.amount
```

**Con OpenSSL 3:** el mismo script deja los tres archivos que hacen falta.

```bash
python3 verificar_recibo.py recibo.json clave_publica.json --exportar openssl/
openssl pkeyutl -verify -pubin -inkey openssl/clave.pem -rawin -in openssl/cuerpo.json -sigfile openssl/firma.bin
# Signature Verified Successfully
```

## El guardián del pago

Todo riel (simulado, Stripe de prueba, Blinka) va envuelto en `GuardedRail`. La orden de pago lleva el recibo de su
decisión y el guardián la rechaza, sin llamar al riel, si el recibo falta, no verifica con la clave, es de otra factura u
otro espacio, es de una decisión que no fue pagar, o si el monto, la moneda, el beneficiario o la cuenta registrada no
son exactamente los de la orden. Los tests están en `apps/api/tests/payments/test_guard.py`.
