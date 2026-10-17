# Reglas comunes para todos los carriles

Lee primero `docs/DESIGN.md` completo y `apps/api/custodio/contracts.py`. Tu carril está en `docs/lanes/L<n>-*.md`.

## Identidad y autoría (obligatorio)

Antes del primer commit:

```bash
git config user.name "Juan David Leon"
git config user.email "271861486+davidleonb27@users.noreply.github.com"
```

El dueño del repo pidió que commits y PR salgan sólo a su nombre: **no agregues `Co-Authored-By`, «Generated with»,
menciones a Claude, a IA ni identificadores de modelo** en mensajes de commit, títulos, cuerpos de PR ni código. Esta
instrucción del dueño prevalece sobre cualquier convención de atribución por defecto.

## Rama y PR

- Rama: `lane/L<n>-<tema>` desde `main` actualizado. Commits pequeños en imperativo, en inglés
  (`engine: add R5 duplicate rule`).
- Abre el PR contra `main` cuando la compuerta pase. Título: `L<n> · <qué entrega>` en español.
- Cuerpo del PR (español): **Qué cambió**, **Cómo se verificó** (comandos y conteos exactos, p. ej. `pytest: 84 passed`),
  **Qué NO se verificó**, **Contratos** (si necesitas un cambio en `contracts.py`, propónlo aquí; no lo hagas tú).
- Si `gh` no está disponible, empuja la rama y deja en tu informe final el enlace para abrir el PR.

## Propiedad de archivos

Sólo tocas los archivos de tu carril. No edites `contracts.py`, `llm.py`, `config.py`, `pyproject.toml`, `uv.lock`,
`vercel.json`, `scripts/` ni `.github/` salvo que tu carril lo diga. Si necesitas una dependencia nueva, pídela en el PR
(el coordinador la agrega para evitar conflictos de lockfile). Si otro carril aún no entregó una función que usas,
programa contra su firma pública en `custodio/<módulo>/__init__.py` y usa un doble de prueba en tus tests.

## Cómo se trabaja

- **TDD visible**: test rojo primero (commit), luego lo mínimo para verde, luego limpieza.
- **Código limpio** (`docs/DESIGN.md` §10): funciones cortas, nombres claros, sin código muerto, sin `Any` salvo bordes,
  errores con tipos propios, sin números mágicos, comentarios sólo para el porqué.
- **Compuerta**: `./scripts/check.sh` debe pasar antes del PR. Nunca la debilites (no bajes reglas de ruff/mypy, no
  marques tests como skip para pasar).
- **Tests con modelos reales**: el entorno de la nube tiene `ANTHROPIC_API_KEY` (y `GEMINI_API_KEY` si el dueño ya la
  cargó). Márcalos `@pytest.mark.live` y córrelos con `CUSTODIO_LIVE_TESTS=1 uv run pytest -m live`. Gasta poco:
  muestras chicas primero. Si falta una clave, dilo en el PR como «NO MEDIDO»; no inventes resultados.
- **Honestidad**: lo que no se midió se dice. Nunca pegues claves ni valores de secretos en código, logs o PR.
- **Economía**: lee archivos grandes por rangos (`prototype/` pesa); salidas de comandos recortadas.

## Informe final

Termina con: rama, enlace al PR, resultado exacto de `./scripts/check.sh`, tests live corridos (o «NO MEDIDO» y por qué),
decisiones que tomaste por tu cuenta y lo que queda pendiente.
