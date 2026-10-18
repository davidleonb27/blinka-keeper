# L5 · Web: la experiencia que gana la demo

**Objetivo**: que un jurado entienda y se enamore en 60 segundos, desde el celular o el portátil.

## Archivos tuyos
`apps/web/**` completo (incluidos `package.json` y su lockfile).

## Decisiones ya tomadas

- Next.js (App Router, última estable), TypeScript `strict`, Tailwind, shadcn/ui, `motion` para animaciones,
  TanStack Query para datos, Recharts para gráficas, Vitest + Testing Library. npm.
- Scripts obligatorios en `package.json`: `dev`, `build`, `lint`, `typecheck` (`tsc --noEmit`), `test` (`vitest run`).
- Identidad visual: la del prototipo (`prototype/index.html`: tipografía, colores, tarjetas, drawer del acta). Mejórala,
  no la reinventes. Tema claro y oscuro. Móvil primero, sin scroll horizontal.
- Datos: el navegador llama a `/api/v1` relativo (mismo dominio en Vercel). Cliente tipado en `src/lib/api/` con tipos
  que reflejan `apps/api/custodio/contracts.py`; script `gen:api` que genera tipos desde
  `uv run --directory ../api python -c "import json; from main import app; print(json.dumps(app.openapi()))"` con
  `openapi-typescript`. Modo `NEXT_PUBLIC_API_MODE=mock` con datos de ejemplo (portados del dataset del prototipo) para
  trabajar sin backend; `live` por defecto en producción.
- Espacio de trabajo: al entrar, si no hay cookie `custodio_ws`, se crea con `POST /workspaces {mode:"demo"}`; la
  cabecera `X-Custodio-Workspace` va en cada llamada.
- Todo texto visible en español neutro. Montos con formato es-CO.

## Pantallas (`docs/DESIGN.md` §9, en este orden de prioridad)

1. Panel (pagado / retenido / pendiente) + drawer del acta con las 12 reglas, citas resaltadas, texto oculto destapado,
   contrafactual, aprobar/rechazar.
2. Onboarding tipo Typeform (una pregunta por pantalla, Enter avanza, progreso, transiciones con `motion`,
   accesible con teclado).
3. Inicio con métricas en vivo y los dos caminos (demo / mi empresa).
4. Reglas en español con diff y simulación.
5. Arena Claude contra Claude (consume SSE de `/redteam/runs`).
6. «Róbale a Blinka Keeper» (subir o escribir, resultado, contador global, muro).
7. Registro (cadena, verificar, alterar una copia).
8. Desarrolladores (API key, ejemplo curl del firewall, config MCP para Claude Desktop).

## Tests (primero)

Formateo de montos y fechas; cliente de API (cabecera de espacio, manejo de 429/503 con mensajes en español);
componentes clave (acta muestra las 12 reglas; onboarding avanza con Enter y valida); flujo de onboarding en modo mock.
Antes del PR: `npm run build` sin advertencias de tipos, Lighthouse móvil ≥ 90 en accesibilidad (reporta el número).

## Fuera de alcance
Lógica de reglas en el cliente: la web nunca decide, sólo muestra lo que devuelve la API.
