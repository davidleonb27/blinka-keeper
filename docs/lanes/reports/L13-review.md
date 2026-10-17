# Revisión de L13 · Autonomía ganada y planificador de pagos (PR #16)

Rama `claude/lane-l13-autonomy-scheduler-vphgdt`, revisada sobre 18c7a00 (ya contiene `origin/main` c546f4f).
Seguí `docs/lanes/REVIEW.md`, `docs/lanes/reports/L13.md` y `docs/DESIGN.md` §3.

## Veredicto: LISTO PARA MERGE

No encontré ningún camino por el que la autonomía ganada pague algo que una regla de retención frena, se salte
R10 a R15 o rompa la reserva. Los hallazgos de abajo no bloquean. Dejo tres para que el dueño decida.

## Compuerta

- Antes de mis cambios: `./scripts/check.sh` → `== gate passed`: ruff `All checks passed!`, mypy sin errores,
  `pytest: 1083 passed, 22 skipped`, web `vitest: 25 files, 147 passed`, `next build` correcto.
- Después de mis cambios: `== gate passed`, `pytest: 1085 passed, 22 skipped`, web `147 passed`.

## Qué revisé y cómo

**La autonomía ganada sólo mueve R9.** El tope ganado entra únicamente por `RuleContext.trust` en `approval()`
(`apps/api/custodio/engine/rules.py`). R10 (límite por pago), R11, R12 (reserva), R13, R14 y R15 no lo leen.
`terms_for` y `_bounded` (`engine/trust.py`) mantienen el tope dentro de `[piso, techo]`. El techo es
`per_payment_limit`, o `approval_threshold` si `hard_ceiling`. El tope se vuelve a plegar desde el ledger con la
política vigente en cada decisión, así que si después se baja un límite, el tope baja con él. El auditor aplica el
mismo tope (`engine/audit.py:210`) y sigue comprobando por su cuenta el límite por pago, el presupuesto y la reserva.

**Prueba adversarial (fuera del repo).** Le di a cada proveedor un tope de 10¹² y corrí el lote demo y 200 empresas
sintéticas (semilla 7) con aprobaciones aleatorias. Resultado: 0 pagos indebidos según el auditor. Ningún pago
autónomo con una regla HOLD o ESCALATE fallida. Ningún pago con una regla HOLD fallida, ni siquiera con aprobación.
Sólo cambiaron de estado las trampas de R9. Convertí la parte del lote demo en un test (ver «Qué arreglé»).

**R13, R14 y R15 revocan la confianza.** Están en `INCIDENT_RULES`. R14 sin lista cargada escala el pago pero no
revoca, y eso es correcto: no dice nada del proveedor. Hay tests de las tres en `tests/engine/test_trust.py`.

**Sin pagos dobles y sin pagos antes de la aprobación.**
- `_waiting` (`services/schedule_service.py:194`) sólo toma decisiones en `PAID` con `execution = null` y un asiento
  `scheduled_for`. Una pendiente de aprobación nunca entra.
- `payment_service.execute` devuelve la ejecución que ya existe si la factura está liquidada, con la misma clave de
  idempotencia. Por eso un `run-due` repetido o concurrente no vuelve a llamar al riel.
- Las intenciones del firewall nunca se programan.
- Un pago vetado por el auditor nunca llega a `pay`.

**«Simular 30 días».**
- Sólo corre en el espacio demo y una sola vez: un asiento `simulation` lo marca.
- Siempre usa el riel simulado. El test levanta un riel Stripe que falla si alguien lo llama.
- `run_due(only=…)` deja intactos los pagos reales programados.
- El mes sale de `random.Random(1330)` y sólo depende de la fecha de inicio. Agregué un test que lo simula en dos
  espacios demo nuevos y compara el resultado completo (sin los hashes): es idéntico.

**Dorado y estrés.** `tests/dataset/test_golden.py` y `tests/engine/test_stress.py` siguen verdes: accuracy 1,0,
0 pagos indebidos, 0 vetos, 0 saltos de reserva y 0 trampas pagadas por el agente. Sin historial, el lote demo decide
exactamente igual que antes (`test_trust_hook.py`).

**UI en Chromium (Playwright, 360×780, sin `playwright install`).** Escribí un recorrido temporal contra la API real
y el build de producción: entrar a la demo, decidir, `/autonomia`, «Simular 30 días», `/calendario`, «Pagar lo que
vence hoy» y `/registro`. Resultado: 1 passed, cero errores de consola, cero excepciones, cero respuestas ≥ 400 y
`scrollWidth ≤ clientWidth` en las cuatro páginas. No dejé el archivo en el repo. Las vistas se leen bien a 360 px.
La página de autonomía es larga (una tarjeta por proveedor), pero se usa sin problema.

## Hallazgos

1. **No bloquea; lo decide el dueño.** Un pago aprobado por el agente con un tope ganado y programado a futuro se
   ejecuta en su día aunque el proveedor pierda la confianza entretanto (por ejemplo, otra factura suya con R4).
   Esto pasa en `services/schedule_service.py:118` (`run_due`): no vuelve a mirar el tope vigente ni la política.
   No rompe ningún invariante de §3: esa factura pasó todas sus reglas y el auditor la aprobó. Pero es el único caso
   en que la autonomía ganada mueve dinero después de una revocación. La mejora sugerida es que `run_due` devuelva a
   aprobación humana un `paid_auto` con `amount_base` sobre el tope vigente. Eso necesita un estado o flujo nuevo,
   así que no lo cambié en esta revisión.
2. **No bloquea.** El auditor recibe los topes de `CompanyState.trust`, que calcula el mismo servicio que alimenta
   al motor; no los recalcula del ledger por un camino propio. El riesgo queda acotado: el auditor comprueba aparte
   el límite por pago y la reserva, y los topes salen de un pliegue acotado del ledger encadenado.
3. **No bloquea; lo decide el dueño.** El carril cambió `contracts.py` y `config.py`, y `COMMON.md` exige
   aprobación para eso. Todos los campos nuevos son opcionales o tienen valor por defecto, y el informe los justifica.
   No hay un brief `docs/lanes/L13-*.md` en el repo para confirmarlo.
4. **Menor.** `simulation_service.py:70` sube `opening_balance` del espacio demo para siempre: es el ingreso supuesto,
   y queda anotado en el asiento `simulation`. Es aceptable porque sólo pasa en la demo.
5. **Menor, de UI.** A 360 px la navegación del panel corta «Calendario». Es un desplazamiento horizontal interno de
   la barra, no de la página, y sigue siendo usable.

## Qué arreglé

- `engine, api: test that an earned cap never lifts a hold and that the simulated month replays identically`:
  - `tests/engine/test_trust_hook.py`: con un tope de 10¹² para todos, el lote demo da 0 pagos indebidos. Ningún pago
    autónomo tiene una regla fallida. Sólo pasa a pagado lo que antes sólo escalaba R9, y lo que escalaba R10 nunca
    se paga solo.
  - `tests/api/test_trust.py`: la simulación es idéntica en dos espacios demo distintos.

No cambié código de producción.

## Qué NO verifiqué

- Stripe real en modo prueba. Tampoco el e2e completo de 26 pasos (sólo mi recorrido de 360 px en el proyecto
  `bogota`).
- Si alguna factura del mes simulado queda programada después del día 30. Si queda, un `run-due` real posterior la
  pagaría por el riel del despliegue. NO MEDIDO.
- Carreras reales entre dos `run-due` simultáneos contra Postgres. Me apoyé en la idempotencia de
  `payment_service.execute`.
