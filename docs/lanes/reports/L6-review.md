# Revisión de L6 · Entrega (PR #5, `lane/L6-delivery`)

**Veredicto: LISTO PARA MERGE.** No encontré nada bloqueante. Encontré siete afirmaciones imprecisas en los documentos
(ninguna cambia una decisión de pago) y las corregí en commits separados.

## Compuerta

Antes de mis cambios (`2a12f0b`) y después (`a988ffe` + este informe), con `./scripts/check.sh`:

```
ruff check: All checks passed!
ruff format --check: 13 files already formatted
mypy: Success: no issues found in 11 source files
pytest: 60 passed   (de ellos, tests/delivery: 55 passed)
== gate passed   (exit 0)
```

No existe `apps/web` todavía, así que la parte web de la compuerta no corrió.

## Qué revisé y qué encontré

**Corrección y contenido.** Contrasté cada afirmación técnica con `contracts.py`, `DESIGN.md` y las ramas ya
entregadas de L1 y L4 (no fusionadas, leídas con `git show`).

- Verificado sin cambios: efectos de cada regla en las tablas (R4/R5/R8/R12 retienen; el resto escala), códigos HTTP de
  `COPY.md` (413, 415, 429, 503, 404, 409 coinciden con `custodio/api/errors.py` de L4), ruta MCP `/api/v1/mcp` y sus tres
  herramientas, campos obligatorios del `curl` del firewall (`PaymentIntent`), `Authorization: Bearer`.
- Cifras externas, abiertas en su fuente: FBI IC3 2025 (BEC 24.768 denuncias y US$ 3.046.598.558; 2024: 21.442 y
  US$ 2.770.151.146; "más de US$ 30 millones" con IA) y AFP del 14 de abril de 2026 (74 % BEC, 76 % fraude de pagos, 465
  encuestados): coinciden. Sin cifras inventadas; lo no medido dice NO MEDIDO.

**Invariantes de DESIGN §3.** Ningún texto cambia una decisión: los documentos no contradicen ninguno. Revisé que no
digan que se paga con una regla de retención fallida, que la aprobación humana rompa la reserva, que el modelo decida o
que el motor lea `expected`. `PITCH.md` (2:00) y `COPY.md` repiten correctamente que ni aprobando se rompe la reserva.

**Seguridad.** Sin secretos ni valores de claves en ningún archivo; el ejemplo usa `$CUSTODIO_API_KEY`. Sin Telegram ni
Gemini presentes como existentes (test + lectura manual).

**Tests.** Rojo antes que verde, comprobado ejecutando el historial: `bed64e3` da `44 failed, 4 passed`; `6dab0cf` da
`6 failed, 49 passed`. Los tests protegen propiedades reales (tiempos contiguos, palabras por segundo, cifras con fuente,
separación de 4 h, límite de X). Dos son sólo de presencia de texto (`test_dataset_doc_gives_the_reproduction_commands`,
secciones de `COPY.md`); es aceptable para documentos, y arriba comprobé a mano que los comandos funcionan.

**Código limpio.** El test es corto, tipado y con constantes con nombre; sin código muerto.

**Propiedad de archivos y autoría.** `contracts.py`, `llm.py`, `config.py`, `scripts/`, `.github/` sin cambios. Fuera de la
lista del carril entran `LICENSE` y `apps/api/tests/delivery/`: ambos declarados en el informe del autor, necesarios
(el README promete la licencia; el test protege los documentos) y sin cruce con otros carriles. Los 8 commits originales
y los míos: autor y committer `Juan David Leon`, sin `Co-Authored-By`, sin «Generated with», sin menciones a Claude ni IA.

### Hallazgos corregidos

| # | Archivo:línea (estado actual) | Hallazgo | Arreglo (commit) |
|---|---|---|---|
| 1 | `README.md:70`, `docs/PITCH.md:68` | Decían «tests de propiedades sobre miles de empresas aleatorias en cada commit». La CI corre propiedades de Hypothesis con 60 ejemplos; las 1.000 empresas son del script de estrés, que la CI no corre. Es la afirmación de seguridad del video. | `d4cc1ca`: separa lo que corre en cada commit de la prueba de estrés reproducible. |
| 2 | `docs/DATASET.md:36` | La tabla incluía «Moneda distinta a la pactada», que el dataset de L1 no tiene, y omitía «Suplantación de un proveedor conocido» (R3), que sí. | `1ea6669` |
| 3 | `docs/DATASET.md:15` | Decía que una persona puso las etiquetas antes de ver el motor; no hay nada que lo respalde. | `1ea6669`: dice cómo se escriben y deja el test que prueba que el motor no las lee. |
| 4 | `docs/DATASET.md:63` | «Con la misma semilla el resultado es el mismo»: el JSON incluye `seconds`, que varía. | `1ea6669`: sólo los conteos son idénticos. También agrega EUR a las monedas. |
| 5 | `docs/ARCHITECTURE.md:71` | Un pago vetado por el auditor «cuenta como pago indebido»; en L1 el motor vuelve a decidir con el veto y queda un `blocked_reason`. | `832fdf7` |
| 6 | `README.md:115` | La respuesta del firewall se describía con nombres que no son los del contrato (`IntentVerdict`). | `a988ffe`: `decision` (con `agent_verdict`), `ledger_hash`, `acta_url`. |
| 7 | `README.md:102` | «Sin claves, los tests con modelo se omiten»: se omiten salvo `CUSTODIO_LIVE_TESTS=1`, haya clave o no. | `a988ffe` |

### Observaciones no corregidas (no son de L6)

- `docs/DESIGN.md:38` repite «sobre miles de empresas aleatorias en cada commit» y `DESIGN.md:60,78,180` aún nombran
  Telegram (el §13 lo deja fuera). Es archivo del coordinador; conviene alinearlo.
- `README.md` manda a `cd apps/web && npm install`; `apps/web` aparece cuando se fusione L5.
- Los números del dataset (36 casos, 18 tipos de trampa) dependen de que L1 se fusione tal como está; si L1 cambia las
  trampas, hay que volver a mirar la tabla de `DATASET.md`.

## Verificaciones adicionales que sí hice

- Rama de L1 (`origin/lane/L1-engine`) en un worktree aparte: `uv run python scripts/stress.py --companies 1000 --seed 7`
  corrió en 35,1 s: 25.139 facturas, 8.136 pagos revisados por el auditor, `improper_payments: 0`, `auditor_vetoes: 0`,
  `reserve_breaches: 0`, `traps_paid_by_agent: {}`. `demo_cases()` devuelve 36 casos. Esto confirma que los comandos de
  `DATASET.md` funcionan; **no** lo copié a los documentos: esas cifras las publica el coordinador sobre la versión final.
- Los dos diagramas Mermaid (`README.md` y `docs/ARCHITECTURE.md`) se renderizan sin error con `mermaid-cli`.

## Qué NO pude verificar

- **Tests con modelo (`live`): NO MEDIDO.** No hay `ANTHROPIC_API_KEY` en este entorno; no corrí ninguno ni llamé a Claude.
- **Ninguna métrica de Custodio sobre la versión desplegada** (autonomía, exactitud, ataques, intentos): NO MEDIDO.
- **Funciones descritas de otros carriles que aún no están fusionadas** (Arena, reto público, botón «alterar una copia»,
  pantalla «Desarrolladores»): no existen en esta rama; leí L1 y L4 pero no L5 ni L3. El guion y el calendario de
  publicaciones dependen de que existan al grabar y publicar.
- **BioCatch** (+155 % y +42 %, 36 entidades): no lo abrí; sólo verifiqué FBI y AFP.
- Cómo se verá la web, el GIF y las capturas (no existen; `docs/img/LEEME.md` los lista).
- Los usuarios oficiales de 30X y Blinka en X y LinkedIn (el calendario no los inventa).
