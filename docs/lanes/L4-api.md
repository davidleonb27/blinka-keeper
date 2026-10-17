# L4 · API, persistencia, aprobaciones, firewall, MCP y reto público

**Objetivo**: un solo carril de escritura. Pantalla, Telegram, firewall, MCP y reto público pasan por los mismos
servicios, con las mismas guardias, y todo queda en el ledger.

## Archivos tuyos
`apps/api/main.py`, `apps/api/custodio/api/**`, `apps/api/custodio/db/**`, `apps/api/custodio/services/**`,
`apps/api/alembic/**`, `apps/api/alembic.ini`, `apps/api/tests/api/**`, `apps/api/scripts/` (salvo `stress.py`).

## Decisiones ya tomadas

- SQLAlchemy 2 síncrono + psycopg 3. `DATABASE_URL` de Neon (pooled) en producción; SQLite en tests y local.
  `NullPool` cuando `CUSTODIO_ENV=prod`. Tipos portables (JSON, LargeBinary, Numeric(18,2)).
- Documentos en Postgres (`LargeBinary`, ≤ 4 MB). No usamos Blob.
- Alembic con migraciones versionadas. En producción, la primera petición de cada instancia corre `upgrade head` bajo
  `pg_advisory_lock` (en SQLite, directo).
- Tablas: `workspaces` (api_key sólo como sha256), `policies` (versionadas), `documents`, `invoices` (extracción JSON,
  estado), `decisions`, `approvals`, `approval_tokens` (un uso, para Telegram), `ledger_entries` (por espacio, `seq`
  único), `challenge_attempts`, `redteam_runs`, `rate_counters`.
- Capa `services/`: `workspace_service`, `invoice_service` (leer → decidir → auditar → ledger), `policy_service`
  (compilar → simular → aplicar), `approval_service`, `firewall_service`, `challenge_service`, `redteam_service`.
  Las rutas sólo validan, llaman al servicio y serializan. El motor, la lectura y `ai` se usan sólo por sus funciones
  públicas.
- Espacio por visitante: `POST /workspaces {mode: "demo"|"blank"}` siembra con `custodio.dataset`. Cabecera
  `X-Custodio-Workspace` obligatoria en rutas de espacio; 404 uniforme si no existe (no revela si existe en otro lado).
- Firewall y MCP: `Authorization: Bearer <api_key>`; un `PaymentIntent` se convierte en `extract_text` + `decide_all`
  con exactamente las mismas reglas que una factura subida. MCP con el SDK `mcp` (FastMCP, `stateless_http=True`,
  `json_response=True`) montado en `/api/v1/mcp`, herramientas `submit_payment_intent`, `get_decision`, `get_policy`.
- Telegram: `POST /telegram/webhook`; al quedar una decisión pendiente se envía el acta resumida al aprobador con
  botones cuyo `callback_data` es un token de un uso. Script `scripts/set_telegram_webhook.py --url ...`.
- Red team por SSE (`text/event-stream`) con `judge` = renderizar → leer → decidir; tope de rondas 12.
- Reto público: `POST /challenge/attempts` (texto o archivo) corre el pipeline completo en un espacio efímero clonado
  de la demo; `broke_through` sólo si el auditor confirma un pago indebido. Triaje con `model_cheap`. Límite por IP.
- Límites: contador por IP y por espacio en ventana de 1 min para rutas con modelos (`429` con mensaje en español);
  cuerpo ≤ 4 MB (`413`).
- Errores: `LLMError` → 503 con mensaje honesto («no pudimos leerla; queda para revisión humana»), nunca un 500 mudo.
- Mientras L1, L2 y L3 no se fusionen, usa dobles en tus tests detrás de sus firmas públicas.

## Tests (primero)

Por ruta: éxito, validación, aislamiento entre espacios (un espacio no ve ni aprueba lo de otro), mismo resultado por
pantalla, firewall y MCP para la misma factura, aprobación por token de un uso (segundo uso falla), ledger verificable
tras cada flujo, límites 429/413. Migraciones: `upgrade head` en SQLite vacío.

## Fuera de alcance
Reglas, lectura de documentos, prompts, UI.
