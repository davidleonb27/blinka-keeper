# Revisión del PR #3 · L3 (`lane/L3-ai`)

## Veredicto: **LISTO PARA MERGE**

Con dos avisos para el dueño:

1. **`red_team` lo escribió esta revisión.** La entrega original no lo traía (seguía el stub). Lo implementé siguiendo
   los tests rojos originales del autor. Por eso esa parte no tuvo una revisión independiente: conviene que otra
   sesión mire `apps/api/custodio/ai/redteam.py` antes de la demo.
2. **`apps/api/custodio/llm.py` está fuera del carril.** Según `docs/lanes/reports/L3.md`, el dueño autorizó el
   cambio. Desde aquí no puedo comprobarlo. El cambio está bien hecho y tiene tests (ver H7). Si esa autorización no
   existió, este punto bloquea el merge.

Revisé la rama en `1d20f9a`, rebaseada sobre `origin/main` (`c76cf02`, es ancestro). Agregué 6 commits, todos sobre
`lane/L3-ai`.

## Compuerta

| Momento | Resultado exacto de `./scripts/check.sh` |
|---|---|
| Al recibir la rama (`1d20f9a`) | `== gate passed`. ruff `All checks passed!`, formato `27 files already formatted`, mypy `Success: no issues found in 17 source files`, pytest `83 passed, 16 skipped in 3.61s` |
| Tras la revisión (`8649bc6`) | `== gate passed`. ruff `All checks passed!`, formato `29 files already formatted`, mypy `Success: no issues found in 18 source files`, pytest `105 passed, 17 skipped in 1.60s` |

Los 17 omitidos son los tests `@pytest.mark.live`, que en esta corrida no se ejecutaron.

## Hallazgos

### Bloqueantes (arreglados)

- **H1. `red_team` no estaba implementado.** `apps/api/custodio/ai/__init__.py` lanzaba `NotImplementedError`. El
  brief de L3 lo pide (punto 5) y la demo depende de él (Arena, DESIGN §2.2 y §9.6). El autor había borrado sus
  propios tests rojos (`22bdec6:apps/api/tests/ai/test_redteam.py`).
  → **Arreglado**: tests restaurados en `1e021b4` (rojo: `ModuleNotFoundError: custodio.ai.redteam`) e
  implementación en `b2d1c78` (verde). Lo que hace `apps/api/custodio/ai/redteam.py`:
  - `red_team` (`:102`) rechaza menos de 1 o más de `MAX_ROUNDS = 10` rondas (`:32`, `:109`).
  - Emite `round_started → attack_generated → verdict → round_finished` por ronda y un `summary` al final.
  - Un `LLMError`, un `anthropic.APIError` o un ataque inválido se convierten en un evento `error` y la corrida
    sigue (`:116`).
  - `_checked` (`:139`) descarta reglas que no existen, normaliza `r5` a `R5`, rechaza una factura vacía o de más
    de 6.000 caracteres y convierte un `hidden_text` vacío en `None`.
  - `caught` es `False` sólo si la decisión quedó pagada (`:164`). Una escalada cuenta como atrapada: decide una
    persona.
  - El atacante ve `policy_view` (sin cuentas ni contactos), el nombre de la empresa, la fecha y los últimos 20
    pagos, pero **no el saldo** (`_company_view`, `:187`). También ve cada intento anterior con su técnica, su
    estado y las razones de las reglas que fallaron.
- **H2. Las razones del veredicto podían enseñarle al atacante la cuenta registrada.** El brief pide pasar «los
  veredictos con sus razones». Si una razón de R4 trae la cuenta registrada, el atacante la aprende y puede ganar R4
  en la ronda siguiente.
  → **Arreglado**: `redact_accounts` (`redteam.py:169`) tapa cada cuenta registrada con `[cuenta registrada]`, con o
  sin separadores (`123-456-789 01`, `1234.5678.901`). Un número pegado no la esconde. Tests:
  `test_registered_accounts_in_verdict_reasons_never_reach_the_attacker` y
  `test_redaction_finds_the_account_next_to_other_numbers` (3 casos, `1ceea33`).

### Importantes (arreglados)

- **H3. El compilador aceptaba ventanas en días que la cita no dice.** En `apps/api/custodio/ai/policy_compiler.py`,
  `_set_days` sólo revisaba el rango. Con la cita «revisa duplicados de los últimos 30 días», el modelo podía
  devolver `days=1`, y eso afloja R5 con un valor que el usuario nunca escribió. Choca con «nunca relaja una regla
  que el texto no menciona» y con el criterio que el mismo módulo ya aplicaba a los montos.
  → **Arreglado** (`:282`, `_days_in` en `:290`, `_PERIOD_DAYS` en `:82`): los días deben estar en la cita, en
  número o en palabras («30 días», «una semana» = 7, «dos semanas» = 14, «quincena» = 15, «mes» = 30). Si no, el
  cambio va a `unsupported`. Test: `test_a_window_needs_its_days_in_the_quote` (5 casos, rojo en `f9da79f`, verde en
  `a7f3b97`). La regla 2 del prompt y la docstring del módulo lo dicen ahora.
- **H4. Un error de red o de la API rompía la narración.** `apps/api/custodio/ai/narrator.py` sólo atrapaba
  `llm.LLMError`. `structured()` deja pasar `anthropic.APIConnectionError`, `RateLimitError`, etc., así que un corte
  de red rompía el acta en vez de caer a `decision.explanation`, como pide el brief.
  → **Arreglado** (`narrator.py:51`). Test: `test_an_api_error_falls_back_instead_of_breaking_the_acta`.
- **H5. Un XLSX mal formado daba un error 500 en vez del error tipado.** En `apps/api/custodio/ai/suppliers.py`, si
  una hoja no tenía relación en `workbook.xml.rels`, `next(...)` lanzaba `StopIteration`. Si apuntaba a un string
  compartido inexistente, saltaba `IndexError` fuera del `try`.
  → **Arreglado** (`suppliers.py:200`, `:223`): ambos casos lanzan `UnreadableSupplierFile`. Test:
  `test_a_broken_workbook_is_unreadable_not_a_crash` (2 casos).

### Sin arreglar (menores o fuera de alcance; quedan anotados)

- **H6. El sentido de un cambio de monedas no se verifica con código.** En `policy_compiler.py:297–307`, para
  «no pagues en reales», el modelo podría devolver `operation="add"` con BRL, y eso afloja R8. La cita es literal
  pero el código no puede confirmar el sentido. Lo mitiga que la persona revisa el diff antes de aplicarlo
  (`PolicyProposal`). Lo dejo así: verificar negaciones con código sería frágil.
- **H7. `llm.py` (fuera del carril, autorizado según el autor).** La continuación de `pause_turn` acumula los
  bloques del asistente y los reenvía como último mensaje (`llm.py:167`), tal como indica la guía de herramientas de
  servidor. Revisé que `to_dict()` de `ParsedBetaTextBlock` no incluye `parsed_output` (SDK `anthropic 1.15.0`), así
  que el reenvío no lleva campos de más. Tiene 5 tests con cliente guionado (`tests/test_llm.py`); el test rojo
  `cbf54d8` va antes del verde `6618045`. Queda **sin verificar en vivo** (ver abajo).
- **H8. La validación de números del narrador tiene dos huecos.** En `narrator.py:74` y `:69`, los ids de regla
  (`R1`…`R12`) y los largos de listas hacen que cualquier número del 1 al 12 pase siempre. Además, no se comprueba
  que una cifra vaya con su moneda («12.500 COP» pasaría si 12.500 existe en USD). Riesgo bajo: el acta
  determinista sigue al lado.
- **H9. A la importación de proveedores le faltan advertencias.** No avisa de dos proveedores con la misma cuenta
  bancaria (una señal de fraude clásica). Tampoco avisa de un acuerdo en una moneda distinta de la del proveedor
  (`suppliers.py:336`); en ese caso R6 escalará después. Sugerencia para un siguiente PR.
- **H10. El perfil propone reglas a partir del texto del sitio.** `profile.py:134`: una página con inyección podría
  sesgar `suggested_rules_text`. Está mitigado, porque ese texto se compila con la verificación de citas y la persona
  lo revisa, pero conviene mostrarlo en la UI como sugerencia editable.
- **H11. DESIGN §13 sigue pendiente fuera del carril.** Quedan `gemini_model` y `gemini_configured` en
  `apps/api/custodio/config.py:31,45`, y `google-genai` en `apps/api/pyproject.toml:15`. No son de L3: le tocan al
  coordinador. L3 no usa Gemini ni Telegram.
- **H12. `red_team` no atrapa errores del juez.** Si `judge` lanza una excepción (`redteam.py:120`), corta la
  corrida. Lo dejé así a propósito: el juez es de la API (L4), que debe convertir un fallo del pipeline en un evento
  SSE o en un error HTTP.

### Lo que revisé y está bien

- **Invariantes de DESIGN §3.** Ningún camino de L3 decide un pago ni cambia la política sin pasar por la propuesta y
  la revisión de una persona. El modelo nunca ve cuentas ni contactos (`views.policy_view`, con tests en el
  compilador y en el red team). No hay secretos en código, logs ni prompts.
- **Compilador.** Campo desconocido → `unsupported`. Cita inventada → descartada. Monto que la cita no dice →
  descartado. Valores negativos o fuera de rango → `questions`. Dos valores para una regla → pregunta, y no se aplica
  ninguno. `version` sube sólo si hay cambios.
- **Perfil.** `web_fetch_20260209` es el tipo vigente para Opus 5.5 según la skill `claude-api`. Usa
  `allowed_domains` con el dominio del sitio (cubre subdominios), `max_uses=5` y rechaza IPs y `localhost`. Sólo
  conserva como evidencia las URLs que `web_fetch` leyó de verdad.
- **Proveedores.** XLSX con `DOCTYPE`/`ENTITY` rechazado y partes de más de 20 MB rechazadas. El PDF pasa por la
  misma validación de filas que las hojas de cálculo.
- **Tests.** Prueban comportamiento real con un doble que valida el esquema. Los 7 fixtures de salidas malas se
  rechazan o se neutralizan. En el historial, el test rojo va antes que la implementación en ambos ciclos del autor
  y en los míos.
- **Idioma y autoría.** Código en inglés y texto de producto en español. Los 13 commits de la rama (contando este informe) son de
  `Juan David Leon <271861486+davidleonb27@users.noreply.github.com>`, sin `Co-Authored-By`, sin «Generated with» y
  sin menciones de atribución. `contracts.py` no cambió.

## Commits de la revisión

| Commit | Qué |
|---|---|
| `f9da79f` | tests rojos: error de API en la narración, ventanas sin días en la cita, XLSX roto |
| `a7f3b97` | arreglos H3, H4 y H5 |
| `1e021b4` | tests rojos del red team (restaurados) + prueba de cuentas tapadas + `make_state` + test en vivo |
| `b2d1c78` | `custodio/ai/redteam.py` y su export en `custodio/ai/__init__.py` |
| `1ceea33` | test de tapado de cuentas junto a otros números |
| `8649bc6` | `docs/lanes/reports/L3.md`: se corrige lo que quedó falso (red team y conteos) |

## Lo que NO pude verificar

- **Tests en vivo: NO MEDIDO.** En este entorno `ANTHROPIC_API_KEY` y `ANTHROPIC_AUTH_TOKEN` están vacías, no hay CLI
  `ant` ni perfil en `~/.config/anthropic`. No hay resultado para:
  - compilador: aciertos sobre 12 frases;
  - 3 narraciones;
  - perfil de `https://www.juanvaldez.com`;
  - 3 rondas del red team.

  Para medirlos: `cd apps/api && CUSTODIO_LIVE_TESTS=1 uv run pytest -m live -s tests/ai`.
- **El prompt del atacante contra Opus 5.5 real.** No sé si el modelo responde o se niega a generar las facturas de
  prueba. Si se niega, `red_team` emite eventos `error` (cubierto con un doble), pero la Arena quedaría vacía.
- **`pause_turn` y `fetched_urls` contra la API real.** En particular, no sé cómo se combina la salida estructurada
  con texto intermedio en un turno de `web_fetch`.
- **El red team con el pipeline real (L1 + L2).** No están en `main`. El test en vivo usa un juez sustituto que
  sólo mira R2 a R4.
