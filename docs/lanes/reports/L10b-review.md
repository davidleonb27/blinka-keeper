# Revisión de L10 / L10b · sitio de código abierto, /docs y Docker (PR #12)

**Veredicto: LISTO PARA MERGE**

Rama `lane/L10-open-source`, rebasada sobre `origin/main` en `bbb7eb0` (merge de L11, PR #11) y empujada con
`--force-with-lease`. Revisión hecha según `docs/lanes/REVIEW.md`, sobre el brief del carril y `docs/lanes/reports/L10.md`
(incluida la sección L10b).

## Rebase

- 30 commits reaplicados. Un conflicto, en `apps/api/tests/delivery/test_delivery_docs.py`: L11 agregó los tests de
  `docs/BLINKA.md`, del pitch y del enlace del README a los rieles, y L10 agregó el test de la cabecera bilingüe del
  README en el mismo lugar del archivo. Se conservaron los dos bloques completos; no hubo otros conflictos.
- Tras el rebase la compuerta pasa (ver abajo), así que los tests de L11 sobre el README (`](docs/BLINKA.md)`,
  `](docs/PAYMENTS.md#los-rieles)`) siguen en verde con el README nuevo de L10.

## Puntos pedidos

**(a) Licencia: cumple.** `LICENSE` es la MIT estándar con «Copyright (c) 2026 DreamMakers (Adriano Joao Souza Reyna,
Juan David Leon, Leober Ramos)», sin `NOTICE`. Coherentes con eso: `README.md:4` (insignia MIT), `README.md:12` y `:20`
(licencia en español e inglés), `README.md:177-181` (equipo y licencia a nombre de DreamMakers con los tres nombres),
`apps/web/package.json:5` (`"license": "MIT"`), `apps/api/pyproject.toml:5` (`license = "MIT"`). Frente a `main`, el
`package-lock.json` sólo cambia en la línea `license` de la raíz; las licencias de las dependencias quedan como las
publica npm. Ni `package.json` ni `pyproject.toml` declaran `author`/`authors`; no es una incoherencia, sólo una
ausencia.

**(b) Fuentes: cumple.** `apps/web/src/app/layout.tsx:2,8-9` carga sólo `Inter` y `Source_Serif_4` de
`next/font/google`; `globals.css:142-143` define `--font-sans: "Inter"` y `--font-serif: "Source Serif 4"`; la mono es
la pila del sistema. En Chromium, la fuente calculada de `body`/`p` es `Inter` y la de `h1` es `"Source Serif 4"` en
las cuatro páginas revisadas.

`git grep -i -E "geist|bricolage|apache"` en todo el repositorio, excluidos los lockfiles (en `package-lock.json` hay 48
coincidencias, todas de licencias `Apache-2.0` de terceros, como deben quedar):

- **Arreglado:** `prototype/index.html` todavía cargaba Bricolage Grotesque, Geist y Geist Mono de Google Fonts y los
  usaba en `--f-display`, `--f-body` y `--f-mono`. Ahora carga Inter y Source Serif 4 con la misma asignación que la web
  (serif para títulos, Inter para texto, mono del sistema). Commit `prototype: load Inter and Source Serif 4 like the
  web app`. El prototipo no se despliega; sólo `engine.js` se usa (para `gen:mock`).
- **Quedan, a propósito:**
  - `apps/web/src/app/typography.test.ts:39` y `apps/api/tests/delivery/test_delivery_docs.py:287`: son las guardias
    que **prohíben** esos nombres; tienen que nombrarlos.
  - `docs/lanes/reports/L10.md` (líneas 12, 92, 122, 154, 181, 186, 216) y `docs/lanes/reports/L5.md:12`: registro
    histórico de lo que se usó y se quitó. Reescribirlo borraría la trazabilidad.

**(c) Docker compose: levanta.** Docker 29.8.2. `docker compose up --build -d --wait` dejó `postgres`, `api` y `web` en
`healthy`. Con `curl`:
`GET :8000/api/v1/health` → `{"status":"ok","version":"0.1.0","anthropic":false,"payment_rail":"simulated"}`;
`GET :3000/`, `/docs`, `/docs/inicio-rapido`, `/docs/rieles`, `/desarrolladores`, `/panel` y `/api/v1/health` (la web
reenvía a la API por la red del compose) → 200. Como en la corrida del autor, este entorno exige la CA de su proxy para
descargar paquetes durante la construcción, así que se usó un archivo de override **fuera del repositorio** con
`network: host`, los argumentos de proxy y el secreto `extra_ca` que ya aceptan ambos Dockerfiles. Sin ese archivo la
construcción falla aquí en `uv sync` por TLS, que es lo esperado en esta red y no un defecto del compose.

**(d) Chromium con Playwright: cumple.** Playwright 1.56.1 con el Chromium ya instalado, contra el compose
(`localhost:3000`), a 360 × 800 y 1280 × 800, en `/`, `/docs`, `/docs/inicio-rapido` y `/desarrolladores`:

| Página | Estado | Errores/avisos de consola, `pageerror`, peticiones fallidas | `scrollWidth` a 360 px | h1 |
| --- | --- | --- | --- | --- |
| `/` | 200 | 0 | 360 | El agente de cuentas por pagar de código abierto |
| `/docs` | 200 | 0 | 360 | Introducción |
| `/docs/inicio-rapido` | 200 | 0 | 360 | Inicio rápido |
| `/desarrolladores` | 200 | 0 | 360 | Desarrolladores |

Ningún elemento se sale del ancho de la ventana fuera de contenedores con desplazamiento propio. En las capturas a
360 px: la portada muestra el título, los dos botones a todo el ancho y el bloque de código con «Copiar»; `/docs`
muestra la navegación de secciones como una fila desplazable bajo la cabecera, sin solaparse con el texto;
`/desarrolladores` muestra la llave enmascarada, «Mostrar» y el estado de la API sin cortes.

## Hallazgos

1. **Arreglado · `prototype/index.html:9,38-40`.** Fuentes anteriores en el prototipo (ver (b)).
2. **Arreglado · integración con L11.** Tras el rebase, L11 ya ofrece el riel `blinka_simulated`
   (`apps/api/custodio/payments/choice.py`, `docs/PAYMENTS.md:46`), pero las páginas de L10 sólo listaban `simulated` y
   `stripe_test`. Se agregó en `apps/web/src/app/docs/rieles/page.tsx` (fila nueva de la tabla de rieles; la fila «el
   de tu empresa» queda para Blinka en producción), en `apps/web/src/app/docs/configuracion/page.tsx` (descripción de
   `CUSTODIO_PAYMENT_RAIL`) y en `.env.example`. Commit `docs: list the blinka_simulated rail from L11 in the rails page,
   the configuration page and .env.example`.
3. **Sin hallazgos bloqueantes** en el resto:
   - Corrección e invariantes: el lector por etiquetas sin clave (`custodio/extraction/labels.py`) sólo extrae; sus
     valores pasan por `verified_field` como los del modelo y lo que no se lee queda vacío y lo escala R1. Un número de
     cuenta distinto en el documento sigue llevando a `hold` por R4/R5; ningún texto del documento decide.
   - Seguridad: imágenes sin secretos horneados, API como `custodio` y web como `node`; las estrellas de GitHub se piden
     en el servidor con tiempo límite; `STRIPE_SECRET_KEY` y `ANTHROPIC_API_KEY` sólo por entorno.
   - Tests: los commits `test:` rojos preceden a sus cambios en el historial; las guardias de licencia y tipografía
     prueban comportamiento real (fallan si vuelve el nombre prohibido).
   - Propiedad de archivos: los toques a `llm.py`, `pyproject.toml`, `uv.lock`, `.github/` y `vercel.json` están
     declarados en «Contratos» del informe de L10 y los pide el carril; `contracts.py`, `config.py` y `scripts/` no
     cambian.
   - Idioma y autoría: código en inglés, texto de producto en español; los 33 commits de la rama son de
     `Juan David Leon <271861486+davidleonb27@users.noreply.github.com>` y ninguno lleva trailers ni atribuciones.

## Compuerta final

```
$ ./scripts/check.sh
== api: lint, format, types, tests
All checks passed!
167 files already formatted
Success: no issues found in 94 source files
843 passed, 22 skipped in 69.49s (0:01:09)
== web: API schema, lint, types, tests, build
 Test Files  21 passed (21)
      Tests  119 passed (119)
✓ Generating static pages using 3 workers (21/21)
== gate passed
```

## Lo que no se verificó

- La construcción de las imágenes **sin** el secreto `extra_ca` (como en CI) no se pudo probar aquí: la red de este
  entorno exige la CA del proxy. El job `images` de GitHub Actions lo cubre.
- Safari y Firefox; sólo Chromium headless. No se corrió axe ni un lector de pantalla.
- `npm run e2e` (el recorrido completo de la demo) no se volvió a correr tras el rebase; sí los 119 tests de la web y
  la navegación de las cuatro páginas pedidas contra el compose.
- El botón «Deploy with Vercel» y las instrucciones de Railway/Fly.io no se probaron.
- Tests `live`: este entorno no tiene `ANTHROPIC_API_KEY`. NO MEDIDO.
