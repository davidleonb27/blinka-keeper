# Revisión de un PR (la hace una sesión distinta de la que lo escribió)

1. `git fetch && git checkout <rama>`; lee el brief del carril y `docs/lanes/reports/L<n>.md`.
2. Corre `./scripts/check.sh` y anota el resultado exacto.
3. Revisa, en este orden:
   - **Corrección**: ¿hace lo que pide el brief? ¿los bordes (topes exactos, ventanas, monedas, vacíos, `null`)?
   - **Invariantes** de `docs/DESIGN.md` §3. Cualquier camino donde se pague con una regla de retención fallida, se
     rompa la reserva o un texto del documento cambie una decisión es bloqueante.
   - **Seguridad**: secretos fuera de código y logs; aislamiento entre espacios; cada superficie nueva (firewall, MCP,
     Telegram, reto) conserva las guardias de la vía principal; entradas validadas; límites de tamaño y tasa.
   - **Tests**: ¿prueban comportamiento real o son tautológicos? ¿el test rojo aparece antes en el historial?
     ¿cubren las trampas?
   - **Código limpio**: funciones cortas, nombres claros, sin código muerto, sin `Any` innecesario, errores tipados.
   - **Propiedad de archivos y contratos**: nada fuera del carril; `contracts.py` sin cambios no aprobados.
   - **Idioma y autoría**: código en inglés, texto de producto en español; sin atribuciones a Claude/IA en commits o PR.
4. Arregla tú mismo lo que encuentres, en commits separados sobre la misma rama (mismo `git config` de
   `docs/lanes/COMMON.md`), y vuelve a correr la compuerta.
5. Informe final: veredicto (`LISTO PARA MERGE` / `BLOQUEADO`), hallazgos con `archivo:línea`, qué arreglaste, resultado
   final de la compuerta y lo que no pudiste verificar.
