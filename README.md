# Custodio

**El agente de cuentas por pagar que no se deja engañar.** El modelo lee, el código decide, la persona autoriza.

Hackathon 30X · Reto Blinka · Equipo DreamMakers.

- Diseño: [`docs/DESIGN.md`](docs/DESIGN.md)
- Carriles de trabajo: [`docs/lanes/`](docs/lanes/)
- Prototipo navegable original: [`prototype/`](prototype/)

## Desarrollo

```bash
./scripts/check.sh            # la compuerta única: lint, tipos, tests (api y web)
cd apps/api && uv run uvicorn main:app --reload
```

Variables de entorno: ver `docs/DESIGN.md` §11. Nunca se suben valores reales al repo.
