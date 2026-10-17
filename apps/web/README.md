# Custodio · web

Next.js (App Router) + TypeScript estricto + Tailwind + shadcn/ui.

```bash
npm ci
NEXT_PUBLIC_API_MODE=mock npm run dev   # sin backend: datos de ejemplo del prototipo
npm run dev                             # live: llama a /api/v1 relativo
npm run lint && npm run typecheck && npm run test && npm run build
npm run gen:api                         # regenera src/lib/api/openapi.d.ts desde FastAPI
npm run gen:mock                        # regenera los datos de ejemplo desde prototype/engine.js
```
