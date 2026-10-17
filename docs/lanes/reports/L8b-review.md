# Revisión de L8b · Hidratación (#418) y enlaces profundos al acta

Rama `lane/L8b-hydration` (PR #15). Revisión hecha por una sesión distinta de la que escribió el carril.

## Veredicto: LISTO PARA MERGE

## Rebase

La rama salía de `d6fbeab` (merge de L8). La rebasé sobre `origin/main` en `bbb7eb0` (merge de L11) sin conflictos:
L11 sólo tocó `components/acta/payment-execution.tsx`, `lib/presentation.ts` y los tipos de la API, ninguno de los
archivos del carril. Empujada con `--force-with-lease`. La compuerta pasó sobre la rama rebasada antes de mis cambios:
API 804 passed, 22 skipped; web 18 archivos, 90 tests; build con todas las rutas `○` estáticas.

## Revisión

- **Corrección.** El arreglo ataca la causa medida: `useClientQuery` (`apps/web/src/lib/api/hooks.ts:36`) hace que el
  primer render de cualquier consulta lea una clave vacía y deshabilitada, idéntica al HTML del servidor, y lea la
  real justo después de hidratar. `useHydrated` (`apps/web/src/lib/hydration.ts:9`) usa `useSyncExternalStore` con
  instantánea de servidor `false`, el patrón que React reconcilia solo tras hidratar; en navegación del lado del
  cliente devuelve `true` desde el primer render, así que no añade parpadeo. Todas las consultas del web pasan por
  ahí (no queda ningún `useQuery` directo). El `<Suspense>` quedó sólo alrededor de `ActaDrawer`
  (`components/dashboard/dashboard.tsx:103`), el único que lee `useSearchParams`, y el build lo confirma (sin error de
  «useSearchParams should be wrapped in a suspense boundary»).
- **Invariantes (DESIGN §3).** No toca motor, reglas, reserva ni pagos. Sólo cambia cuándo se pinta un dato.
- **Seguridad.** Sin secretos nuevos. El reemplazo de espacio que agregué sólo actúa ante el código
  `workspace_not_found` de la API y crea un espacio `demo` nuevo, el mismo camino que la primera visita; nunca reusa
  ni adivina un id.
- **Tests.** El rojo aparece antes en el historial (`b81008f` e2e, `9575228` unitario) y el unitario prueba de verdad
  la hidratación (`hydrateRoot` sobre `renderToString` con el caché lleno, contando `onRecoverableError`). El e2e
  retrasa el chunk propio de cada página, que es la condición que reproduce el #418.
- **Código limpio y propiedad.** Todo dentro de `apps/web`. Sin cambios en `contracts.py`, la API ni `scripts/`. Sin
  atribuciones en commits.

## Hallazgos abiertos del reporte: decisión

1. **Cookie de un espacio que ya no existe: bug real y pequeño, ARREGLADO.** Tras reiniciar la base, `/panel` quedaba
   para siempre en «No encontramos eso en tu espacio de trabajo». La API ya manda `code: "workspace_not_found"` en el
   cuerpo, pero el web sólo leía `detail`.
   - `lib/api/errors.ts`: `WorkspaceGoneError` (subclase de `NotFoundError`) cuando el 404 trae ese código. Un 404 de
     otra cosa (p. ej. `decision_not_found` de un acta que no existe) sigue siendo `NotFoundError` y no toca el
     espacio.
   - `lib/api/live-client.ts`: lee `detail` y `code`; una llamada que falla con `WorkspaceGoneError` pide
     `replaceWorkspace(stale)` y se repite **una sola vez** en el espacio nuevo (sin bucle).
   - `lib/api/workspace.ts`: `renewWorkspace` crea un demo y reescribe la cookie, salvo que otra llamada ya la haya
     reemplazado.
   - `lib/api/session.ts`: las consultas paralelas del panel comparten una sola creación (`once`), así que tres 404
     simultáneos crean un único espacio.
   - Tests: rojo en `b5befc0` (4 fallos), verde en `963fa96`; e2e nuevo «a cookie naming a workspace the API no longer
     has is replaced by a new demo» (exige exactamente un `POST /workspaces`, cookie distinta y el panel con
     «Facturas por decidir»).
2. **«Hoy» en fecha UTC del servidor frente a horas en Bogotá: real, pero NO es pequeño ni de este carril; queda
   abierto, no bloquea.** `today` sale de `ctx.now().date()` (`services/workspace_service.py:112`), y la misma fecha
   UTC la usan el motor (mes de R11, vencimientos en `services/records.py:158,178`), los pagos
   (`services/payment_service.py:114`), el alta de espacios en blanco y el prompt del modelo (`llm.py:104`). Cambiar
   sólo el chip haría que el panel dijera un día y el motor decidiera con otro; cambiarlo en la API es decidir la zona
   horaria de la empresa para todo el motor, lo que toca la semántica del cupo mensual (R11) y archivos fuera del
   carril (`llm.py`). Es anterior a L8b y no tiene que ver con la hidratación. Requiere decisión del dueño: propongo
   un carril de API que añada la zona de la empresa al espacio y derive de ella toda «fecha de hoy».

## Qué arreglé (commits sobre la rama)

- `b5befc0` web: test rojo del espacio borrado (cliente y `renewWorkspace`).
- `963fa96` web: reemplazar el espacio que la API ya no tiene y repetir la llamada.
- `b0a0458` e2e: el e2e de hidratación ahora cubre también `/` y `/reto`, y el espacio borrado. La
  aserción «el HTML del panel trae el panel» usa la frase del panel en vez de `PAGES[0]`, que ahora es la portada.

## Verificación en Chromium (Playwright, sin `playwright install`)

`npm run e2e` (servidores con `TZ=UTC`; perfiles `bogota` y `tokio-oscuro`): **26 passed (1.5m)**. Cada carga exige
cero errores de consola, cero excepciones (el #418 incluido) y ninguna respuesta HTTP ≥ 400, con el código propio de
la página llegando 1,5 s tarde, en `/`, `/reto`, `/panel`, `/reglas`, `/arena` y `/registro`; y `/panel?acta=<id>` y
`/acta/<id>`, con y sin retraso, abren el panel con el acta y sus 12 reglas sin errores. El recorrido completo de L8
también pasó en ambos perfiles.

## Compuerta final

`./scripts/check.sh` → `== gate passed`: ruff «All checks passed!», «162 files already formatted», mypy «no issues
found in 92 source files», pytest **804 passed, 22 skipped**; web: esquema al día, lint y tsc OK, vitest **18
archivos, 95 tests passed**, build OK (todas las rutas estáticas).

## Lo que no pude verificar

- No desplegué en Vercel ni probé el Chrome real del dueño, con sus extensiones; el estado exacto del enlace profundo
  con el `<main>` vacío sigue sin reproducirse (ver `L8b.md`). Hay que confirmarlo con el despliegue nuevo.
- No corrí el e2e del espacio borrado contra la versión sin arreglo; su versión unitaria sí estuvo en rojo antes.
- Firefox y Safari, no probados.
