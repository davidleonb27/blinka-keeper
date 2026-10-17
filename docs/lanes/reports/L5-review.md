# Revisión del PR #6 · L5 Web (`lane/L5-web`)

Revisión hecha por una sesión distinta de la que escribió el carril, siguiendo `docs/lanes/REVIEW.md`.

## Veredicto: LISTO PARA MERGE

Con los arreglos de esta revisión ya empujados en la rama. Tal como llegó estaba **BLOQUEADO**: la compuerta fallaba
en un checkout limpio y el CI del PR (`gate`, sobre `2a5e10f`) estaba en rojo por esa misma razón.

Durante la revisión el autor rebasó la rama sobre `main` (`8052f47`) y agregó tres commits (`4b2d91c`, `faccb55`,
`2a5e10f`). Comprobé con `git range-diff` que los 23 commits rebasados son idénticos a los que revisé, revisé los tres
nuevos y reapliqué mis commits encima, sin reescribir nada ajeno (push en avance rápido).

## Compuerta

**Antes de los arreglos** (`bb006cd`, la versión previa al rebase del autor; checkout limpio, sin `.next/`):

- api: `ruff` «All checks passed!», `ruff format` 41 archivos ya formateados, `mypy` sin hallazgos en 29 archivos,
  `pytest: 254 passed`.
- web: `npm ci` bien, `eslint --max-warnings=0` sin hallazgos, **`tsc --noEmit` falla (exit 2)**:
  `src/app/(app)/layout.tsx(3,49)` y `src/app/layout.tsx(26,50)`: `error TS2304: Cannot find name 'LayoutProps'`.
  Ni tests ni build llegan a correr. El job `gate` del PR #6 en GitHub (sobre `2a5e10f`) falló con el mismo error
  después de `pytest: 501 passed, 19 skipped` (CI corre sobre la referencia de merge del PR).

**Después de los arreglos**, sobre la rama final (base `2a5e10f`, ya rebasada en `main` `8052f47`; checkout limpio,
`./scripts/check.sh` → `== gate passed`, exit 0):

- api: `ruff` «All checks passed!», 59 archivos ya formateados, `mypy` sin hallazgos en 36 archivos,
  `pytest: 409 passed, 17 skipped` (los skipped son tests `live`).
- web: `npm ci` bien; `eslint --max-warnings=0` sin hallazgos; `next typegen && tsc --noEmit` sin errores;
  `vitest: 12 files, 62 passed`; `next build` compilado sin advertencias, 10 rutas estáticas.

Antes del rebase del autor también corrí la compuerta sobre `bb006cd` + mis arreglos (`254 passed`; web
`10 files, 59 passed`) y sobre su merge con `main` (`409 passed, 17 skipped`; web `59 passed`): las dos pasaron.

## Hallazgos

### Bloqueantes (arreglados)

1. **La compuerta no pasaba en checkout limpio** — `apps/web/package.json:10` (`"typecheck": "tsc --noEmit"`).
   `LayoutProps` es un tipo global que Next 16 genera en `.next/types` al correr `next dev`/`next build`; en CI y en
   cualquier clon nuevo `tsc` corre antes del build y no lo encuentra. El informe del carril (`docs/lanes/reports/L5.md:64-67`)
   dice «gate passed» y «`tsc --noEmit` sin errores» porque en la máquina del autor ya existía `.next/`. Arreglo: `"typecheck": "next typegen && tsc --noEmit"`.
   Rojo reproducido (borrando `.next/` y `next-env.d.ts`) y luego verde.

2. **El onboarding podía descartar en silencio las reglas que la persona escribió** —
   `apps/web/src/components/onboarding/state.ts:131` y `apps/web/src/components/onboarding/rules-step.tsx:20-29`.
   El paso de reglas sólo validaba que hubiera texto. La compilación arranca 600 ms después de escribir; si la persona
   pulsaba Enter antes, avanzaba sin propuesta y `onboardingRequest` armaba la política con `draftPolicy`, sin sus
   reglas («Nada sobre 3.000 USD sin que lo apruebe Ana» se perdía). Lo mismo con una propuesta vieja: una respuesta
   de un texto anterior que llegaba tarde, o volver a cambiar la moneda o la reserva, dejaba guardada una propuesta que
   no correspondía. Arreglo: la propuesta se guarda con la clave de lo que se compiló (`compileKey` = texto + borrador)
   y el paso sólo avanza si la clave coincide con las respuestas actuales; si no, dice «Custodio todavía está
   compilando tus reglas.». Test rojo primero.

### Menores (arreglados)

3. **Fechas de timestamps en día UTC, gráfica en día de Colombia** — `apps/web/src/lib/format.ts:62`.
   `formatDate` cortaba los 10 primeros caracteres del ISO; la lista del panel, el acta y la simulación de la primera
   semana mostraban el día UTC, mientras que `decisionsByDay` agrupa por día en `America/Bogota`. Una factura que llega
   a las 21:00 en Colombia aparecía con fecha del día siguiente y en la barra del día anterior. El dataset de ejemplo
   (todo a las 14:xx UTC) no lo mostraba. Arreglo: un timestamp se fecha por su día en Colombia; una fecha sola se lee
   tal cual. Test rojo primero.

4. **El muro del reto afirmaba «Ninguno cobró» sin mirar los datos** —
   `apps/web/src/components/challenge/challenge.tsx:160`. Era texto fijo: si la API devolvía un intento con
   `broke_through: true`, la página lo negaba (choca con «sólo cifras medidas» y con «la web sólo muestra lo que
   devuelve la API»). Arreglo: la frase se deriva de los intentos y los que pasaron llevan la marca «Pasó».
   Test rojo primero.

5. **Si el contador global fallaba, desaparecía sin decir nada** — `apps/web/src/components/challenge/challenge.tsx:156`.
   Arreglo: se muestra `ErrorState` con el mensaje en español y «Reintentar». Test rojo primero.

### Observaciones (no se cambian)

- Commits nuevos del autor (`4b2d91c` rojo → `faccb55` verde): redirección `/acta/:id` → `/panel?acta=:id` para el
  `acta_url` del firewall, estado de `/health` en Desarrolladores con `Health` reducido a `status`, `version` y
  `anthropic` (así deja de depender de `gemini`), y aprobadores del dataset con correo en vez de Telegram. Correctos y
  con test rojo antes. Detalle menor: `developers-page.tsx` (`ApiStatus`) pinta en verde también un `status` distinto
  de `"ok"` («API: …»); hoy la API sólo responde `"ok"`.

- `apps/web/src/components/arena/arena-state.ts:36`: un `verdict` con `caught: null` se cuenta como pago indebido.
  Es el lado conservador y hoy no ocurre: `custodio/ai/redteam.py` en `main` siempre manda `caught` booleano.
- `apps/web/src/components/acta/acta.tsx:55`: si la política no tiene aprobadores, el selector queda vacío y los botones
  deshabilitados sin explicar por qué. El onboarding exige al menos uno, así que sólo pasaría con una política
  cargada por otra vía.
- `apps/web/src/components/onboarding/finish-steps.tsx:28`: si `completeOnboarding` falla, no hay botón de reintentar
  en el mismo paso (se reintenta con «Volver» y avanzar de nuevo). Se muestra el error, nada se pierde.
- `apps/web/src/lib/api/workspace.ts:34-35`: la cookie del espacio la escribe JS (no es `HttpOnly`) y la API key vive
  en `localStorage`. Aceptable para la demo; la página de desarrolladores la oculta por defecto y lo dice.
- La dependencia `cn` (`package.json:17`) parece un nombre genérico, pero es el paquete de shadcn
  (`github.com/shadcn-ui/cn`, el propio `shadcn` depende de él); sin scripts de instalación. Correcta.
- `openapi.d.ts` aún trae `gemini` en `Health` porque la API de `main` todavía lo expone; la web ya no lo lee ni lo
  muestra, y desaparece con `npm run gen:api` cuando la base quite `gemini_configured` (DESIGN §13).

## Revisión por criterio

- **Corrección**: el brief se cumple (8 pantallas + acta, cliente tipado, modo mock, cookie `custodio_ws`, cabecera
  `X-Custodio-Workspace`, 429/503 en español, `gen:api`). Fallas de borde encontradas: hallazgos 2 a 5.
- **Invariantes DESIGN §3**: la web no decide; el mock respeta R12 al aprobar (`blocked_reason`) y la alteración del
  registro es sobre una copia. «`null` no es cero» se respeta en métricas («NO MEDIDO») y montos («—»); el texto fijo
  del muro era la excepción (hallazgo 4). Ningún secreto en código; la llave de ejemplo es ficticia.
- **Seguridad**: sin `dangerouslySetInnerHTML` ni `innerHTML`; el documento y el texto oculto se pintan escapados por
  React. Rutas relativas a `/api/v1`, `encodeURIComponent` en ids, `credentials: "same-origin"`. Sin `.env`
  versionados.
- **Tests**: prueban comportamiento (cliente con `fetch` doble, flujo completo del onboarding, acta con 12 reglas,
  reducer de la arena). El rojo aparece antes del verde en el historial (tras el rebase: `4accbd0`, `e662fda`, `1d8ab85`, `0813e3e`,
  `6780641`, `a821eee`, `4b2d91c`). Faltaba cubrir las trampas de los hallazgos 2 a 5; ahora están.
- **Código limpio**: funciones cortas, sin `any`, sin `@ts-ignore`, sin `eslint-disable`, sin `console`, constantes con
  nombre, errores tipados (`ApiError` y subclases).
- **Propiedad de archivos y contratos**: sólo `apps/web/**` y `docs/lanes/reports/L5.md`. `contracts.py` sin cambios;
  `contracts.ts` lo refleja campo por campo (lo comparé). Las envolturas que la web necesita quedan propuestas a L4 en
  el informe del carril.
- **Idioma y autoría**: código en inglés, textos en español; los 26 commits del autor y los 6 de esta revisión salen a nombre de
  Juan David Leon, sin trailers ni atribuciones.

## Qué arreglé (commits sobre `lane/L5-web`)

- `87ff54a` web: generate Next route types before tsc so typecheck passes on a clean checkout
- `ccdb158` web: add failing tests for uncompiled rules, Colombia-day dates and the challenge wall
- `56cb5dc` web: date timestamps by their day in Colombia so list, acta and chart agree
- `c82557e` web: wait for the compiled proposal of the current rules before leaving the rules step
- `8d0af15` web: derive the challenge wall note from the attempts and show a failed counter read
- este informe

## Qué NO pude verificar

- **Tests con modelos reales: NO MEDIDO.** No hay `ANTHROPIC_API_KEY` en este entorno; además la web no llama modelos
  ni tiene tests `live`.
- **Lighthouse y axe: no los volví a medir.** El 100 de accesibilidad en las 8 páginas es la medición del autor sobre
  su build final, antes de mis arreglos (que agregan un mensaje de validación, un `ErrorState` y la marca «Pasó»:
  piezas que ya existían en otras pantallas).
- El modo live contra las rutas de L4: todavía no existen en `main`, salvo `/health`.
- El SSE del red team contra un servidor FastAPI real, y el firewall y MCP de punta a punta.
- El despliegue en Vercel, dispositivos reales y Safari/iOS.
- El CI de GitHub con estos commits: no se abrió ni se tocó el PR; corrí la misma compuerta en local sobre la rama
  final, que ya contiene `main`.
