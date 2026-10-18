# Blinka Keeper · web

Next.js (App Router) + TypeScript estricto + Tailwind + shadcn/ui.

```bash
npm ci
NEXT_PUBLIC_API_MODE=mock npm run dev   # sin backend: datos de ejemplo del prototipo
npm run dev                             # live: llama a /api/v1 relativo
npm run lint && npm run typecheck && npm run test && npm run build
npm run gen:api                         # regenera src/lib/api/schema.gen.ts desde el OpenAPI de FastAPI
npm run check:api                       # falla si schema.gen.ts no coincide con la API (lo corre la compuerta)
npm run e2e                             # recorrido completo en Chromium contra la API real (fuera de la compuerta)
npm run gen:mock                        # regenera los datos de ejemplo desde prototype/engine.js
```

## Contrato con la API

`src/lib/api/schema.gen.ts` se genera del OpenAPI de `apps/api` (`main:app`, `/api/v1/openapi.json`) con
openapi-typescript 7.13.0. `client.ts` toma de ahí cada petición y respuesta por ruta y método, `contracts.ts` son alias
de esos esquemas y el mock implementa la misma interfaz: cualquier desajuste entre web, mock y API rompe `tsc`.

## Recorrido e2e

`npm run e2e` levanta la API (`uvicorn tests.e2e_app:app` sobre un SQLite nuevo: cableado de producción con las
funciones que llaman al modelo cambiadas por dobles deterministas, así no necesita clave) y un `next build` +
`next start` que reenvía `/api/v1` a esa API. Luego recorre todas las páginas y el flujo demo en dos perfiles (Bogotá
en es-CO; Tokio en en-US, móvil, oscuro, sin animaciones y con datos previos en localStorage) y falla ante cualquier
error de consola, excepción (incluido el #418 de hidratación), respuesta HTTP ≥ 400 o pantalla de error. Necesita `uv`
y Chromium para Playwright 1.56.1 (`npx playwright install chromium` si la máquina no lo trae).
