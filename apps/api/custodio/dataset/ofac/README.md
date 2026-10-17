# Copia de la lista OFAC SDN

`sdn.json` es la copia de la lista SDN del Tesoro de EE. UU. contra la que R14 («Sin coincidencia en lista de
sanciones») revisa cada proveedor, su nombre registrado y sus alias.

- **Fuente:** <https://www.treasury.gov/ofac/downloads/> (`sdn.csv`, `alt.csv`, `add.csv`), lista pública.
- **Copia actual:** publicada por OFAC el 15 de octubre de 2026 (`published_on`, tomado de la cabecera
  `Last-Modified`), descargada el 17 de octubre de 2026 (`downloaded_on`), 19.457 entradas.
- **Formato:** JSON compacto con una entrada por línea: `uid`, `name`, `aliases`, `countries`, `programs`, `type`.

## Cómo actualizarla

```bash
cd apps/api
uv run python scripts/update_ofac.py   # baja los tres CSV y reescribe sdn.json
uv run pytest -q tests/dataset tests/engine/test_sanctions.py
git add custodio/dataset/ofac/sdn.json && git commit -m "dataset: refresh the OFAC SDN copy"
```

La fecha de la copia en uso sale en `GET /api/v1/health` (`sanctions_list_date`) y en el acta de cada decisión.
Una coincidencia nunca bloquea sola: R14 escala y una persona descarta o confirma.

Los tests no usan esta copia para probar coincidencias: usan `tests/fixtures/sanctions/fictitious_sdn.json`, una lista
ficticia. Ningún caso de la demo pública lleva el nombre de una persona o entidad sancionada.
