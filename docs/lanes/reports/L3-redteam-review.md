# Revisión independiente · `red_team` de L3 (`apps/api/custodio/ai/redteam.py`)

## Veredicto: **LISTO PARA MERGE**

Esto vale para la rama `lane/L3-redteam-review` con los arreglos de abajo. `red_team` cumple el brief: Claude
propone los ataques y el motor determinista, a través de `judge`, da el veredicto. Ningún camino de este módulo
decide un pago, cambia la política ni deja que el texto del ataque mueva el marcador. Encontré seis fallas y las
arreglé todas, cada una con su test rojo primero. Lo que queda abierto son puntos menores (H7 a H10) y lo que no se
puede verificar sin clave ni sin L2 y L4 en `main`.

Revisé `origin/main` en `8052f47`. La rama sale de ahí y agrega 12 commits de código y tests, más este informe.

## Compuerta (`./scripts/check.sh`)

| Momento | Resultado exacto |
|---|---|
| Al empezar (`8052f47`) | `== gate passed`. ruff `All checks passed!`, formato `59 files already formatted`, mypy `Success: no issues found in 36 source files`, pytest `409 passed, 17 skipped in 30.98s` |
| Tras la revisión (`41ee25e`) | `== gate passed`. ruff `All checks passed!`, formato `59 files already formatted`, mypy `Success: no issues found in 36 source files`, pytest `424 passed, 17 skipped in 24.16s` |

Los 17 omitidos son los tests `@pytest.mark.live`. Hay 15 tests nuevos, todos en `apps/api/tests/ai/test_redteam.py`:
la suite del red team pasa de 14 a 29. Ninguno usa red: el modelo es el doble `FakeLLM` y el juez es un `Judge`
guionado.

## Lo que está bien (verificado leyendo el código y los tests)

- **El juez es el motor, nunca el modelo.** `caught` sale sólo de `decision.status` (`redteam.py:203` en la rama).
  `DraftAttack` no tiene ningún campo de veredicto. El texto del ataque sólo llega a `judge`. `target_rules` se
  filtra contra `RULES` y `round` lo pone el código. Ni la política ni el estado se modifican. Una escalada
  (`pending_approval`) cuenta como atrapada porque decide una persona, como en DESIGN §1.
- **El atacante no ve secretos.** Ve `policy_view` (sin `account_number`, `approver_contact`, `telegram_chat_id` ni
  `email`) y los últimos 20 pagos sin cuenta. Las razones de R4 del motor sí traen la cuenta registrada
  (`engine/rules.py:259`), y `redact_accounts` la tapa antes de mostrársela. Ver H6 para un hueco que tenía.
- **Tope de rondas**: de 1 a `MAX_ROUNDS = 10`. **Tope de gasto**: el diario de `llm.py`, que se revisa antes de
  cada petición. Ver H3 y H8.
- **Historial TDD previo**: el test rojo `1e021b4` va antes que la implementación `b2d1c78`.

## Hallazgos

Las líneas citadas son las de `main` (`8052f47`).

### Arreglados (cada uno con test rojo y luego verde)

- **H1. Las rondas inválidas se detectaban tarde.** Pasaba en `redteam.py:109`. `red_team` era un generador, así
  que `rounds=50` no lanzaba nada al llamarlo, sino al pedir el primer evento. Para L4 eso significa que la respuesta
  SSE ya abrió con 200 y luego se rompe, en vez de responder 422.
  → Ahora `red_team` valida y devuelve el generador interno `_rounds`.
  Test: `test_a_bad_number_of_rounds_fails_on_the_call_not_mid_stream` (rojo `3d00499`, verde `f84a37d`).
- **H2. Una corrida sin ningún ataque juzgado se reportaba como «todo atrapado».** Pasaba en `redteam.py:211-219`.
  Si todas las rondas fallaban, el resumen salía con `caught=True` y el texto «atrapó 0 de 0». Eso choca con
  DESIGN §3: lo que no se midió se dice «NO MEDIDO», y `null` no es cero.
  → Ahora el resumen sale con `caught=None` y el texto «Ningún ataque llegó al juez: NO MEDIDO.». También dice
  cuántas rondas quedaron sin veredicto.
  Test: `test_a_run_where_no_attack_reached_the_judge_is_not_measured_not_caught` (rojo `f00fe28`, verde `d78ad94`).
- **H3. Con el presupuesto agotado, la corrida seguía pidiendo ataques.** Pasaba en `redteam.py:112-117`. Tras un
  `LLMBudgetExceeded`, cada ronda siguiente volvía a llamar al modelo y volvía a fallar igual. Con 10 rondas eran
  10 eventos de error.
  → Ahora la corrida se detiene: emite el `error`, el `round_finished` y el resumen («Corrida detenida en la ronda
  2 de 4.»), y `summary.round` es la última ronda jugada.
  Test: `test_an_exhausted_budget_stops_the_run_instead_of_retrying_every_round`.
- **H4. Los errores de la API llegaban crudos y en inglés.** Pasaba en `redteam.py:117`. El mensaje era
  `f"...: {error}"`, y con un `anthropic.APIError` mostraba «Connection error.» o el cuerpo de la respuesta de la
  API. El texto de producto tiene que estar en español.
  → `_said()` deja intactos nuestros errores tipados, que ya están en español, y reemplaza los de la API por «la
  API de Claude falló (APIConnectionError).».
  Tests:
  - `test_every_typed_model_failure_is_an_error_event` (4 casos: `LLMRefused`, `LLMTruncated`, `LLMError` y
    `APIConnectionError`; antes sólo se probaba `LLMRefused`);
  - `test_an_api_failure_is_told_in_spanish_without_the_raw_error`.

  H3 y H4 van en un mismo par de commits: rojo `75e6fa6`, verde `e9cd3c6`.
- **H5. Los errores del modelo dentro del juez cortaban la corrida.** Pasaba en `redteam.py:120` (era el H12 de
  `L3-review.md`, que se dejó así a propósito). El juez corre el pipeline real, y L2 lee la factura con Claude, así
  que el juez puede lanzar los mismos `LLMRefused`, `LLMTruncated` y `LLMBudgetExceeded`. El generador moría a
  mitad del stream y se perdía el resumen.
  → Ahora sólo los errores tipados del modelo se vuelven un evento `error` con el ataque adjunto. El texto dice
  «no cuenta como atrapado»: el intento no entra en el marcador ni como atrapado ni como pagado. Si es
  `LLMBudgetExceeded`, también se detiene la corrida. Cualquier otra excepción es un bug y sigue propagándose.
  Tests (rojo `83be62f`, verde `0a37a9c`):
  - `test_a_model_failure_inside_the_judge_is_an_error_and_never_counts_as_caught`;
  - `test_a_spent_budget_inside_the_judge_also_stops_the_run`;
  - `test_a_bug_in_the_judge_is_not_swallowed`.
- **H6. Huecos de tamaño y de tapado.**
  - **`hidden_text` no tenía tope.** Pasaba en `redteam.py:153`. La factura visible tiene un tope de 6.000
    caracteres, pero el texto oculto llegaba al pipeline sin límite, y ahí se renderiza y se lee con el modelo.
    → Ahora tiene el mismo tope, y el prompt lo dice.
    Test: `test_hidden_text_has_the_same_size_cap_as_the_visible_invoice` (rojo `6989a2e`, verde `d5ad55d`).
  - **Una cuenta registrada con letras no se tapaba.** Pasaba en `redteam.py:172`. `redact_accounts` sólo miraba
    los dígitos, pero el motor compara las cuentas por letras y dígitos (`engine/text.py:44`). Una cuenta tipo IBAN
    (`ES91 2100 0418 45AB 0005`) aparecía tal cual en la razón de R4, y el atacante la aprendía.
    → Ahora el patrón usa letras y dígitos, sin distinguir mayúsculas.
    Test: `test_redaction_also_covers_accounts_with_letters` (3 casos; rojo `a4243b5`, verde `41ee25e`).

### Sin arreglar (menores; quedan anotados)

- **H7. El saldo se filtra por la razón de R12.** `_company_view` (`redteam.py:188`) oculta el saldo a propósito,
  pero una razón de R12 que falla dice «dejaría el saldo en X, debajo de la reserva de Y» (`engine/rules.py:561`), y
  de ahí sale el saldo. No permite saltarse ninguna regla: R12 retiene igual. Sólo contradice la intención de la
  docstring. Para cerrarlo habría que redactar cifras de las razones, y no vale la complejidad.
- **H8. No hay un tope de gasto por corrida.** Sólo existen el tope diario global (`llm.py`, 25 USD por defecto) y
  el de 10 rondas. Una corrida es como mucho 10 llamadas de Opus con esfuerzo `high` y `max_tokens=16000`. Con los
  precios de `llm._PRICES`, la salida cuesta hasta unos 3,2 USD más la entrada. La API (L4) debe limitar las corridas
  por IP y por espacio, como pide DESIGN §8.
- **H9. «Nunca repitas una técnica» sólo lo pide el prompt.** El código no lo exige. No afecta la seguridad, y el
  test en vivo lo comprueba.
- **H10. El marcador cuenta como pago indebido cualquier pago.** Si el atacante escribe una factura legítima y se
  paga, el marcador la cuenta como indebida. Es conservador, y está bien para un red team, pero conviene saberlo al
  leer el número.

Además, `technique` y `rationale` no tienen tope propio: su largo lo limita `max_tokens`, y la UI debe escaparlos.
Un `TypeError` del SDK por falta de credenciales no se convierte en evento. Es un error de configuración y debe
fallar fuerte.

## Commits de esta revisión

| Commit | Qué |
|---|---|
| `3d00499` → `f84a37d` | rojo → verde, H1 |
| `f00fe28` → `d78ad94` | rojo → verde, H2 |
| `75e6fa6` → `e9cd3c6` | rojo → verde, H3 y H4 |
| `83be62f` → `0a37a9c` | rojo → verde, H5 |
| `6989a2e` → `d5ad55d` | rojo → verde, H6 (`hidden_text`) |
| `a4243b5` → `41ee25e` | rojo → verde, H6 (cuentas con letras) |

Cada arreglo tiene su commit rojo antes del verde. Vi fallar cada test rojo antes de escribir el arreglo.

Todos los commits son de `Juan David Leon <271861486+davidleonb27@users.noreply.github.com>` y no tienen trailers.
No toqué ningún archivo fuera de `apps/api/custodio/ai/**` y `apps/api/tests/ai/**`, salvo este informe.
`contracts.py` no cambió.

## Lo que NO pude verificar

- **Tests en vivo: NO MEDIDO.** `ANTHROPIC_API_KEY` está vacía en este entorno. No hay resultado para las 3 rondas del
  red team contra Opus real (`test_live_red_team_three_rounds_adapt`). Tampoco sé si el modelo acepta el prompt del
  atacante o se niega. Si se niega, ahora cada ronda emite un `error` y el resumen sale «NO MEDIDO» en vez de «todo
  atrapado». Para medirlo: `cd apps/api && CUSTODIO_LIVE_TESTS=1 uv run pytest -m live -s tests/ai/test_live_ai.py -k red_team`.
- **El red team con el pipeline real.** L2 sigue siendo un stub en `main` (`custodio/extraction/__init__.py` lanza
  `NotImplementedError`), así que no hay un juez real que probar. Que una inyección en el documento no cambie la
  decisión depende de L1 y L2, no de este módulo.
- **El consumo desde la API.** L4 no está en `main`: no hay ruta `POST /redteam/runs` que use `red_team`. No pude
  comprobar el manejo del SSE ni el límite por IP y por espacio (H8).
