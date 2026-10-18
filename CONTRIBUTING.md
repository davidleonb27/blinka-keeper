# Cómo contribuir a Blinka Keeper

Gracias por querer mejorar Blinka Keeper. Es un agente de cuentas por pagar: un error aquí puede pagar algo que no se debía.
Por eso las reglas para contribuir son pocas pero firmes.

*English speakers: issues and pull requests in English are welcome. The rules below apply the same way.*

## Antes de empezar

- Lee [`docs/DESIGN.md`](docs/DESIGN.md): las invariantes de la sección 3 no se negocian.
- Si encontraste una forma de que Blinka Keeper pague algo indebido, **no abras un issue público**: sigue
  [`SECURITY.md`](SECURITY.md).
- Para cambios grandes, abre primero un issue y acuerden el enfoque.

## Preparar el entorno

Requisitos: Python 3.12 con [uv](https://docs.astral.sh/uv/), Node.js 24 y, si quieres probar el autoalojado, Docker.

```bash
git clone https://github.com/davidleonb27/blinka-keeper.git
cd custodio-blinka
cp .env.example .env                      # todas las variables son opcionales para desarrollar
cd apps/api && uv sync && cd ../..
cd apps/web && npm ci && cd ../..
```

No necesitas `ANTHROPIC_API_KEY` para desarrollar: los tests no llaman modelos (los que sí, están marcados
`@pytest.mark.live` y se omiten salvo con `CUSTODIO_LIVE_TESTS=1`).

## La compuerta

Hay un solo comando de calidad. Lo corre quien escribe, quien revisa y CI:

```bash
./scripts/check.sh
```

Hace ruff (lint y formato), mypy estricto y pytest en la API; ESLint, TypeScript, Vitest y `next build` en la web. Un PR
sólo se integra con la compuerta en verde. **Nunca la debilites**: no bajes reglas de ruff o mypy, no marques tests como
`skip` para pasar, no agregues `# type: ignore` sin explicar el porqué.

## Cómo se escribe el código

- **TDD visible.** Primero el test que falla (en su propio commit), después lo mínimo que lo pone verde, después la
  limpieza. Quien revisa debe poder ver el rojo en el historial.
- **Código limpio.** Funciones cortas, nombres que dicen qué hacen, sin código muerto, sin `Any` salvo en los bordes,
  errores con tipos propios, sin números mágicos (van en la política o en constantes con nombre). Comentarios sólo para
  el porqué.
- **Idioma.** Código, identificadores, tests y comentarios en inglés. Todo texto que ve una persona, en español neutro.
- **Honestidad.** Lo que no se midió se dice «NO MEDIDO». `null` no es cero. Nunca pegues claves ni secretos en código,
  logs, issues o PR.

## Convención de commits

Commits pequeños, en inglés, en imperativo y con el área como prefijo:

```
engine: add R13 bank holiday rule
api: answer 503 when the model is not configured
web: show the ledger head hash on the acta
docs: explain how to write a payment rail
test: pin the duplicate window at 30 days
```

Áreas habituales: `engine`, `extraction`, `ai`, `api`, `db`, `web`, `docs`, `ci`, `deploy`, `test`.

## Proponer una regla nueva

Las reglas R1–R12 viven en código (`apps/api/custodio/engine/rules.py`) y su catálogo en
`apps/api/custodio/contracts.py`. Una regla nueva cambia lo que Blinka Keeper paga, así que se discute antes de programarla:

1. Abre un issue con la plantilla **«Regla nueva»**: qué fraude o error detiene, un caso concreto que hoy se paga y no
   debería, el efecto que propones (`hold` si es claramente indebido, `escalate` si una persona debe mirarlo) y qué
   dato de la factura o de la política necesita.
2. Si se acepta, el PR trae, en este orden:
   - el test rojo del caso del issue en `tests/engine/test_rules.py` y, si aplica, un caso etiquetado en el dataset;
   - la regla en `rules.py`, con su razón en español y las cifras concretas, y su contrafactual («se habría pagado
     si…»);
   - el mismo control en el auditor independiente (`engine/audit.py`) **por un camino de código distinto**: si el motor
     y el auditor discrepan, gana el auditor;
   - las propiedades de `tests/engine/test_properties.py` en verde (ningún pago con una regla de retención fallando).
3. El motor sigue siendo puro: sin I/O, sin reloj, sin azar, sin modelo. Un texto del documento nunca cambia una regla.

## Proponer un riel de pago nuevo

Un riel mueve el dinero de un pago que Blinka Keeper **ya** aprobó; nunca decide. Abre un issue con la plantilla
**«Riel de pago nuevo»** y lee la guía en la web (`/docs/rieles`). Los rieles de prueba (sandbox) se aceptan; un riel
que mueva dinero real necesita revisión de seguridad aparte.

## Pull requests

- Una idea por PR, idealmente bajo 800 líneas.
- Usa la plantilla: qué cambió, cómo se verificó (comandos y conteos exactos, p. ej. `pytest: 84 passed`) y qué NO se
  verificó.
- Al contribuir aceptas que tu aporte entre al proyecto bajo la licencia MIT ([`LICENSE`](LICENSE)), la misma del resto
  del código.

## Conducta

Este proyecto sigue el [Código de Conducta](CODE_OF_CONDUCT.md) (Contributor Covenant 2.1).
