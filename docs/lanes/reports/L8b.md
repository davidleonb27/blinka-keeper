# L8b · Hidratación (#418) y enlaces profundos al acta

Rama `lane/L8b-hydration`, desde `origin/main` en `d6fbeab` (merge de L8); `main` no avanzó mientras trabajé. Sin PR.

## Qué cambió

**Causa del #418 (medida, no supuesta).** No eran fechas ni números. Todo dato del espacio llega al navegador después
de cargar la página, y el HTML prerenderizado no contiene ninguna fecha, hora ni cifra formateada con `Intl`. Las
fechas ya se formatean con zona explícita (`America/Bogota`) en `lib/format.ts`. El fallo es de orden de llegada:
1. El armazón (layout y `AppNav`) hidrata primero y pide `GET /workspaces/current`.
2. Si el JavaScript propio de la página llega después de esa respuesta, la parte de la página que hidrata tarde (el
   límite de Suspense del panel) encuentra el resumen ya en el caché de React Query.
3. Esa parte lo pinta en el render de hidratación, contra un HTML del servidor que no tenía datos: «Minified React
   error #418» (`args[]=HTML`).

**Arreglo** (sin `suppressHydrationWarning`):
- `apps/web/src/lib/api/hooks.ts`: todas las consultas pasan por `useClientQuery`. Mientras el componente hidrata, lee
  una clave vacía y deshabilitada, así que su primer render es idéntico al del servidor. En el render siguiente lee la
  clave real y muestra al instante lo que ya estaba en caché. Es la opción de «renderizarlos sólo en el cliente»,
  aplicada en un único punto a todo dato del espacio.
- `apps/web/src/lib/hydration.ts`: `useHydrated()` (`useSyncExternalStore` con instantánea de servidor `false`),
  compartido con `theme-toggle.tsx`, que ya tenía una copia.
- Panel: `app/(app)/panel/page.tsx` ya no envuelve todo el `Dashboard` en `<Suspense>`. Sólo `ActaDrawer`, el único que
  lee la URL (`useSearchParams`), queda dentro de un `<Suspense>` en `dashboard.tsx`. Antes, el `<main>` del HTML
  estático de `/panel` era sólo `<!--$?--><template id="B:0"></template>`, un límite pendiente vacío, y todo el panel
  dependía de que ese límite se resolviera en el cliente. Ahora el HTML ya trae el encabezado y los bloques de carga
  del panel, y sólo el acta espera al navegador.

No toqué la portada, `/docs` ni las fuentes. Archivos de la web cambiados: `lib/api/hooks.ts`, `lib/hydration.ts`
(nuevo), `components/shell/theme-toggle.tsx`, `components/dashboard/dashboard.tsx`, `app/(app)/panel/page.tsx`.

## Cómo se verificó

**Reproducción primero.** Con sólo zona y locale (Chromium en `America/Bogota`/`es-CO`, servidores con `TZ=UTC`) no
se reproduce: el perfil `bogota` del e2e ya hacía eso y pasaba en `main`. Ninguna de mis cargas contra producción
sin retrasar chunks (Chromium headless shell y completo; CPU 4× y 8×; red con 300 ms de latencia) dio #418. El
#418 aparece cuando el chunk JS de la página llega tarde:
- **Producción**, con el chunk del panel retrasado 1,5 s o 4 s, el #418 sale en cada carga de `/panel` y de
  `/panel?acta=F-020` (4 de 4 cargas); `/registro`, 0 de 2.
- **Build local**, con 1,5 s de retraso: #418 en `/panel`, `/panel?acta=F-020` y `/acta/F-020`, tanto con cookie como
  en carga fresca.

**e2e nuevo** `apps/web/e2e/hydration.e2e.ts`. Ambos servidores corren con `TZ=UTC` (`playwright.config.ts`) y el
perfil `bogota` usa `America/Bogota`/`es-CO`. Para cada página, el chunk que contiene una frase que sólo esa página
renderiza se retrasa 1,5 s, como ocurre cuando el armazón ya está en caché y el código de la página llega último.
Partiendo de un espacio demo ya decidido, el test exige:
- cero errores de consola, excepciones o respuestas HTTP ≥ 400 en `/panel`, `/reglas`, `/arena` y `/registro`;
- que el HTML de `/panel?acta=<id>` ya traiga el panel en el `<main>`;
- que `/panel?acta=<id>` y `/acta/<id>`, con y sin retraso, abran el panel con el acta encima, con las 12 reglas, y
  pidan `GET /decisions` y `GET /decisions/<id>`.

Las corridas de `npm run e2e` (2 perfiles × 10 tests):
1. **Antes de cualquier arreglo** (`b81008f`): `6 failed, 12 passed (1.4m)`. Los 6 fallos son #418: `/panel` (2) y los
   enlaces profundos con el código llegando tarde (4), en ambos perfiles. `/reglas`, `/arena` y `/registro` pasaron.
2. **Con el arreglo de los hooks** (`4a0a351`) y el test del HTML ya agregado: `2 failed, 18 passed (1.3m)`. Sólo falló
   «el HTML del panel trae el panel» (el `<main>` vacío), en ambos perfiles.
3. **Final** (`7ec63e6`): `20 passed (1.3m)`, dos veces seguidas. El recorrido completo de L8 sigue verde dentro de esas
   corridas.

**Test unitario** `src/lib/api/hydration.test.tsx`. Hidrata con `hydrateRoot` el HTML de `renderToString` con el caché
del navegador ya lleno. Antes del arreglo, `onRecoverableError` se llamó 1 vez (rojo, commit `9575228`); después, 0
veces, y el nombre de la empresa aparece justo tras hidratar.

**`./scripts/check.sh`** → `== gate passed`:
- API: ruff «All checks passed!», «158 files already formatted», mypy «no issues found in 91 source files», pytest
  **765 passed, 22 skipped**.
- Web: esquema al día, lint y tsc OK, vitest **18 archivos, 89 tests passed**, build OK (todas las rutas `○` estáticas).
- El aviso de jsdom «HTMLCanvasElement.prototype.getContext» ya salía en `main` y no es un fallo.

## Qué NO se verificó

- **El estado exacto del enlace profundo con el `main` vacío** (sólo `GET /workspaces/current`, nunca `/decisions`) no
  lo reproduje. Lo intenté en carga fresca y con cookie, contra producción y local, con chunks retrasados (0 a 8 s, en
  orden aleatorio), API lenta (1 a 3 s), CPU 4× y 8×, red de 300 ms y una fuente que nunca termina de cargar
  (`readyState` en `interactive`). En todos los casos el panel montó y pidió `/decisions` y `/decisions/<id>`; cuando
  el código llegaba tarde, además salía #418.
  - Hipótesis no comprobada: en tu Chrome el panel entero vivía dentro del límite que fallaba al hidratar, y su
    recuperación lo dejaba vacío.
  - Las dos causas que sí medí quedaron fuera: ya no hay desajuste, y el panel no depende de ese límite (su HTML ya lo
    trae; sólo el acta espera).
  - Hay que confirmarlo en tu Chrome con el despliegue nuevo.
- **#418 en `/reglas`, `/arena` y `/registro`**: no lo reproduje, ni en producción ni en local, ni con chunks en orden
  aleatorio (8 órdenes × 3 páginas). En el HTML de esas páginas el contenido no está dentro de ningún límite de
  Suspense, así que hidrata de una vez. El arreglo cubre igual a esas páginas: todo dato pasa por `useClientQuery`, y
  el e2e las carga con el código llegando tarde.
- No desplegué ni probé en Vercel después del arreglo. No probé Firefox ni Safari, ni un Chrome real con extensiones.

## Otros hallazgos (no arreglados aquí)

- **«Hoy 17 oct» junto a «16 oct · 23:25».** No es hidratación sino una incoherencia de contenido. `today` del resumen
  es la fecha UTC del servidor (`ctx.now().date()` en `workspace_service.summary`, la misma que el motor usa para el
  mes de R11), mientras la web muestra las horas en Colombia. Entre las 19:00 y las 24:00 de Bogotá el chip dice el día
  siguiente. Propuesta: que la API calcule `today` en la zona de la empresa. Toca la semántica del cupo mensual (R11),
  así que no lo cambié sin decisión del dueño.
- **Cookie de un espacio que ya no existe.** Pasa, por ejemplo, tras reiniciar la base. `/panel` queda en «No
  encontramos eso en tu espacio de trabajo» sin salida: la web nunca crea uno nuevo. Medido en producción y en local.
  Propuesta: ante `workspace_not_found`, crear un espacio demo nuevo y reemplazar la cookie.
- Sigue pendiente lo de L8: sin clave de modelo, la API responde 500 en vez de 503 (`llm.py`).

## Contratos

Sin cambios en `contracts.py` ni en la API.

## Decisiones tomadas por mi cuenta

- La reproducción retrasa los chunks por contenido (una frase propia de cada página) y no por nombre de archivo, que
  cambia en cada build. Si L10 cambia esas frases, hay que actualizar `PAGES` en `hydration.e2e.ts`.
- Saqué `watch` del recorrido a `e2e/problems.ts` para compartirlo entre los dos archivos e2e.
- Las consultas, en vez de devolver un resultado «falso» durante la hidratación, usan una clave aparte y deshabilitada
  (`["hydrating", …]`). Así el tipo es el de React Query sin conversiones; esas entradas vacías se recolectan solas.
