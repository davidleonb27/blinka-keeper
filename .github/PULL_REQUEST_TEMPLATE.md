## Qué cambió

<!-- En pocas líneas: qué y por qué. Enlaza el issue si lo hay (Closes #123). -->

## Cómo se verificó

<!-- Comandos y conteos exactos. Ejemplo: `./scripts/check.sh` verde; `pytest: 84 passed, 2 skipped`. -->

- [ ] `./scripts/check.sh` en verde
- [ ] El test rojo está en un commit anterior al cambio que lo pone verde (TDD visible)

## Qué NO se verificó

<!-- Lo que no se midió se dice «NO MEDIDO», con el porqué. -->

## Seguridad

- [ ] Este cambio no permite pagar con una regla de retención fallando, bajo la reserva ni sin la confirmación del auditor
- [ ] No hay claves ni secretos en el código, los logs, los tests ni este PR
