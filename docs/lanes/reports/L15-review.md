# Revisión de L15 · Reto en vivo (PR #13)

Rama `lane/L15-reto-vivo`, rebasada sobre `origin/main` (`bbb7eb0`, ya con L11). El rebase no tuvo conflictos: L15 sólo
toca `apps/web` y su informe.

## Veredicto: LISTO PARA MERGE

No encontré nada bloqueante. No hice cambios de código; sólo agrego este informe.

## Compuerta

`./scripts/check.sh` sobre la rama rebasada → `== gate passed`.

- API: ruff `All checks passed!`, `162 files already formatted`, mypy `Success: no issues found in 92 source files`,
  pytest `804 passed, 22 skipped`.
- Web: `check:api` sin diferencias, `eslint --max-warnings=0` limpio, typecheck limpio, vitest `18 passed` archivos /
  `103 passed` tests, `next build` correcto.
- `npm run e2e` → `2 passed` (`bogota` y `tokio-oscuro`).

## Lo que revisé

### Seguridad de la superficie pública

El carril no toca la API; la superficie pública es la de main. La comprobé contra la API real (`tests.e2e_app`):

- **Límite de tasa**: seis intentos seguidos desde la misma IP → `201 201 201 201 201 429`
  (`challenge_attempts_per_minute_per_ip = 5`). Además hay un tope global de 2000 intentos al día
  (`apps/api/custodio/services/rate_limits.py:32`) y los contadores viven en la base, compartidos entre instancias.
- **Tamaño de archivo**: un PDF de 5 MB → `413 payload_too_large` («El archivo supera el máximo de 4 MB»), cortado
  por `BodySizeLimit` antes de llegar a la ruta. El texto está acotado a 20 000 caracteres, el alias a 60 y la técnica
  a 120 (`apps/api/custodio/api/routes/challenge.py:16-30`).
- **Ningún dato de otros espacios en el contador**: `challenge_service.stats` sólo agrega `ChallengeAttemptRow`, y
  cada intento corre en un sandbox clonado de la empresa demo
  (`apps/api/custodio/services/challenge_service.py:41-79`). El salón de la fama devuelve sólo `id`, `alias`,
  `technique`, `decision`, `broke_through` y `at` de esos intentos.
- **Sondeo de stats**: el modo escenario pide `/challenge/stats` cada 3 s (`challenge-stage.tsx:13`); medí 3 lecturas
  en 9,5 s por pestaña y **0 lecturas en 7 s con la pestaña oculta** (react-query no sondea en segundo plano). Es una
  sola consulta agregada más un `LIMIT 10`; con un proyector y unos pocos `/reto` abiertos (5 s) la carga es
  despreciable. `GET /stats` no tiene límite de tasa propio, igual que en main; no lo cambia este carril.

### Dependencia del QR

No hay dependencia nueva: `package.json` y el lockfile no cambian. El QR es propio (`apps/web/src/lib/qr.ts`,
325 líneas, sin código de terceros): modo byte, corrección M, versiones 1 a 10, `QrTooLong` si no cabe. Lo decodifiqué
con un lector independiente (`jsqr@1.4.0`, instalado fuera del repo) desde la captura real en Chromium a 360 px
(328 px de lado) y a 1440 px (558 px): las dos devolvieron exactamente `http://127.0.0.1:3101/reto`.

La URL del QR es `window.location.origin` + `/reto` (`challenge-stage.tsx:19-25`): no hay ningún dominio fijo (ni de
preview ni de producción) en `components/challenge/` ni en `lib/qr.ts`. Servido desde
`custodio-blinka-green.vercel.app`, el QR apunta a `https://custodio-blinka-green.vercel.app/reto`; desde una preview,
a esa misma preview.

### Hidratación y consola

Pasada con Playwright y Chromium contra la API real y el build de producción, en dos perfiles: 360×780 móvil, oscuro,
`en-US`, `Asia/Tokyo`; y 1440×900 claro, `es-CO`, `America/Bogota`. En cada uno: un intento en `/reto` y luego
`/reto?escenario=1` durante ~17 s. **0 errores, 0 advertencias y 0 `pageerror`** en los dos. El origen público sale de
`useSyncExternalStore` con `null` en el servidor y un marcador del mismo tamaño, así que no hay desajuste de HTML.

### Usable a 360 px

`scrollWidth − clientWidth = 0` en `/reto` y en `/reto?escenario=1`. El QR ocupa el ancho útil, la URL se parte con
`break-all`, el contador «Pagos indebidos» y la rejilla 2×2 caben sin cortar texto. La barra de navegación desplaza
dentro de sí misma, como en el resto de la app.

### Corrección

- `attemptVerdict` (`apps/web/src/components/challenge/attempt-verdict.ts:12`) mira `broke_through` antes que el
  estado: un pago vetado nunca sale como «PAGADO LEGÍTIMAMENTE». El `switch` es exhaustivo sobre `DecisionStatus`
  (lo verifica el typecheck).
- El enlace al acta codifica el `invoice_id` (`attempt-verdict.ts:43`).
- Al enviar se borra el veredicto anterior (`challenge.tsx`, `send`), con su test.
- `page.tsx` lee `searchParams` dentro de `Suspense`; sólo `escenario=1` activa el modo.

### Tests

Prueban comportamiento visible (roles y nombres accesibles, href, sondeo real con temporizador), no detalles internos.
El test rojo del veredicto, el acta y el escenario va antes que la implementación en el historial
(`web: test the challenge verdict…`). El autor declara que el test del veredicto viejo se escribió junto con su arreglo.

### Autoría e idioma

Los cinco commits son de `Juan David Leon <271861486+davidleonb27@users.noreply.github.com>`, sin trailers ni
atribuciones. Código en inglés, texto de producto en español. Nada fuera del carril; `contracts.py` sin cambios.

## Observaciones no bloqueantes

1. **Límite por IP en la demo** (`apps/api/custodio/services/context.py:28`): 5 intentos por minuto por IP. Si el
   jurado sale por el mismo NAT del salón, todos comparten esos 5. Conviene subirlo para el día de la demo (archivo
   fuera de este carril).
2. **IP del cliente** (`apps/api/custodio/api/deps.py:57-60`, anterior a L15): se toma el primer valor de
   `X-Forwarded-For`. En Vercel la plataforma reescribe esa cabecera, pero en otro despliegue un atacante podría rotarla
   para saltarse el límite por IP; el tope diario global sigue acotando el costo.
3. **«Último intento en el muro»** (`attempt-verdict.ts:47`) es el más reciente de los 10 más creativos, no el último
   intento absoluto. La etiqueta lo dice («en el muro»), pero en una demo con muchos intentos puede quedarse quieto.
4. **«Frenados»** cuenta sólo `hold` (`challenge_service.py:72`), mientras el veredicto también llama FRENADO a un
   `rejected`. Es de la API, anterior a L15; hoy el reto no produce `rejected` en los e2e.

## Lo que no pude verificar

- El acta desde el enlace sigue sin cargar (404) hasta que entre L8b; lo declara el informe del autor.
- FRENADO, PAGADO LEGÍTIMAMENTE y PAGO INDEBIDO sólo en tests unitarios: con los dobles del e2e todo sale ESCALADO.
- No escaneé el QR con la cámara de un teléfono; sólo con el decodificador.
- No corrí tests live: el carril no usa modelos.
