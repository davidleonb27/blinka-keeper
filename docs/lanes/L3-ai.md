# L3 · Claude en Blinka Keeper: reglas en español, narración, onboarding y red team

**Objetivo**: lo más vistoso de la demo, sin que el modelo decida nada.

## Archivos tuyos
`apps/api/custodio/ai/**`, `apps/api/tests/ai/**`.

## Qué implementar (firmas en `ai/__init__.py`; modelos y esfuerzos en `docs/DESIGN.md` §7)

1. `policy_compiler.py` · `compile_policy(text, current)`: Claude devuelve cambios a campos conocidos de `Policy`
   (y acuerdos por beneficiario) con la cita del usuario que los justifica; el código valida tipos, rangos y que el campo
   exista; lo que no mapea va a `unsupported`; ambigüedades a `questions`. Nunca relaja una regla que el texto no
   menciona. Casos: «nada sobre 3.000 dólares sin aprobación», «el arriendo son 2.500 fijos», «no pagues en reales»,
   «deja siempre 80 mil de colchón», «a Nube S.A.S. páguele hasta 9.000 al mes», negaciones y texto irrelevante.
2. `narrator.py` · `narrate(decision)`: texto claro para alguien sin contexto financiero. Validación: cada número del
   texto debe existir en la decisión (normalizando formato); si no, se descarta y se devuelve `decision.explanation`.
3. `profile.py` · `profile_company(name, website, answers)`: Claude Opus con la herramienta de servidor `web_fetch`
   (tipo vigente según la skill claude-api; sólo la URL que dio el usuario y páginas del mismo dominio) devuelve
   `CompanyProfile` con `evidence_urls` y un párrafo de reglas sugeridas. Sin sitio → sólo con las respuestas.
4. `suppliers.py` · `import_suppliers(data, filename, media_type)`: CSV/XLSX se leen con código; PDF de contrato o
   factura vieja con Claude (salida estructurada). Advertencias por filas incompletas o duplicadas.
5. `redteam.py` · `red_team(policy, state, rounds, judge)`: atacante adaptativo. Ronda n recibe la política (sin
   secretos), las técnicas ya probadas y los veredictos con sus razones; genera un `AttackSpec` nuevo. `judge` (lo da la
   API) corre el pipeline real. Emite `RedTeamEvent`s. Técnicas sembradas: cuenta cambiada, inyección visible y oculta,
   fraccionamiento, proveedor parecido (homógrafo), moneda ambigua, duplicado con otro número, monto justo bajo el tope,
   urgencia falsa de un directivo.

Antes de escribir código que llame a Claude, carga la skill `claude-api`. Todo pasa por `custodio.llm.structured`; si
necesitas un parámetro que no expone, pídelo en el PR.

## Tests (primero)

- Con doble de `llm.structured`: validación del compilador (campo inexistente → `unsupported`; valor negativo →
  rechazo; texto que no menciona una regla no la toca); narrador con número inventado → cae a `explanation`; red team
  emite la secuencia de eventos correcta y para en `rounds`.
- Salidas malas grabadas (fixtures JSON) que el sistema debe rechazar.
- Live: 12 frases del compilador con su resultado esperado (reporta aciertos/12 en el PR), 3 narraciones, 1 perfil
  real de un sitio público, 3 rondas de red team contra la política demo.

## Fuera de alcance
HTTP, persistencia, la UI.
