# Revisión L2 · Lectura de facturas (PR #2, rama `lane/L2-extraction`)

Revisión hecha por una sesión distinta de la que escribió el carril, siguiendo `docs/lanes/REVIEW.md`.

## Veredicto: **LISTO PARA MERGE**

Con los arreglos de abajo ya en la rama. La rama no compilaba la compuerta al recibirla, y había dos fallas de
fondo: valores truncados pasaban como verificados, y cuatro formas de esconder texto llegaban al modelo como texto
visible. Las cuatro quedaron arregladas, con tests rojos primero. Los tests live siguen **NO MEDIDO**: no hay
`ANTHROPIC_API_KEY` en este entorno, y `docs/lanes/COMMON.md` permite entregar así si se declara.

## Compuerta

| Momento | Comando | Resultado exacto |
|---|---|---|
| Al recibir la rama (`5004ab6`) | `./scripts/check.sh` | **falló** (exit 1) en `ruff check`: `Found 2 errors`, I001 (imports desordenados) en `tests/extraction/doubles.py:1` y `tests/extraction/test_vision.py:1`. No llegó a format, mypy ni pytest. El informe del autor decía `gate passed` |
| Final, en la punta de la rama | `./scripts/check.sh` | `gate passed`: ruff `All checks passed!`, `38 files already formatted`, mypy `Success: no issues found in 25 source files`, `pytest: 193 passed, 2 skipped` (los 2 omitidos son los tests live) |
| Final, rebaseada en una copia aparte sobre `origin/main` actual (`8052f47`, con L1, L3 y L6) | `./scripts/check.sh` | `gate passed`: `85 files already formatted`, mypy sin errores en 50 archivos, `pytest: 597 passed, 19 skipped`. El rebase entra sin conflictos. Por eso **no** reescribí la historia de la rama ni hice push forzado |

## Hallazgos

### Bloqueantes (arreglados)

1. **La compuerta estaba rota.** En `tests/extraction/doubles.py:4` y `tests/extraction/test_vision.py:4`, el import
   de `custodio.extraction.vision` iba en un bloque aparte, así que ruff I001 falla. El informe del autor
   (`docs/lanes/reports/L2.md:3`) decía «gate passed», y eso no era cierto en la punta entregada.
   → `2f6b616`.

2. **Códigos y cuentas truncados pasaban como verificados (invariante R1 de §3).** En `custodio/extraction/verify.py:109`
   (`_same_characters`) y `:118` (`_same_digits`), los separadores entre caracteres eran libres, pero el borde final
   sólo miraba el carácter siguiente. Por eso la cuenta `12345678` se verificaba contra «Cuenta 1234 5678 9», y
   `45678901` contra «123-456789-01». Un NIT sin dígito de verificación (`900.123.456`) también pasaba contra
   «NIT 900.123.456-7», y `FE-1234` contra «FE-1234-B». Además, `_same_text` (`:105`) aceptaba un pedazo de una
   palabra: «Andina» se daba por verificado contra «Andinas Ltda». En los tres casos el código decía
   `verified=true` para un valor que no es el que dice el documento.
   → test rojo `c384e5c`, arreglo `4f29f75`. El código tiene que ser completo: después de quitar los separadores, no
   puede seguir ningún carácter del mismo código, ni antes ni después. El texto se compara por palabras completas.

3. **Había texto que una persona no ve pero que llegaba a `visible_text` y al modelo** (DESIGN §6 y el brief: «Ningún
   texto escondido pasa sin verse»). Lo reproduje con PDFs hechos a mano. Ninguno de estos casos generaba un
   hallazgo, y el texto escondido entraba al texto visible:
   - modo de render 3 (texto invisible, la técnica más común). El autor lo había declarado como no cubierto;
   - texto blanco sobre una imagen blanca. `pdf.py` no juzgaba el color sobre imágenes;
   - texto fuera del CropBox pero dentro del MediaBox. En `custodio/extraction/pdf.py:106` se usaba `page.bbox` (el
     MediaBox), no la caja de recorte que muestra el visor;
   - glifos aplastados con escala horizontal de 0,5 %.

   → test rojo `b044354`, arreglo `e65cadb`. Ahora la posición se juzga contra el CropBox. También se agregó una
   última verificación por trazo: la página se dibuja con y sin su texto (`PdfWriter.remove_text` de pypdf y el
   render de pdfplumber, a 100 ppp). Un carácter que no está en blanco y que en su caja no cambia ningún píxel más
   de 0,08 por canal se marca como oculto (`invisible_color`, con un detalle propio en español). Esto cubre de una
   vez el modo 3, los recortes, la transparencia total, el color de la imagen de fondo y los glifos aplastados. Para
   evitar falsos positivos hay un test con texto legible sobre imágenes claras y oscuras: cero hallazgos. La factura
   limpia sigue con cero hallazgos, y las 7 técnicas del renderizador se siguen detectando con su tipo. Cuesta unos
   40 ms por página.

### Importantes (arreglados)

4. **No había tope de páginas en los PDF con texto** (`custodio/extraction/pdf.py:78`). Un PDF de cientos de páginas
   se leía entero y todo su texto iba al modelo. Con el punto 3, además, cada página se dibuja dos veces. →
   test rojo `bfec514`, arreglo `8b3e0c9`. Ahora `MAX_PDF_PAGES = 20` lanza `UnsupportedDocument` antes de dibujar
   nada. Los escaneos mantienen su tope de 5.

### Observaciones (no arregladas; no bloquean)

5. `custodio/extraction/pdf.py:194`: en páginas rotadas 90° o 270°, pdfminer da como `size` el ancho del carácter.
   Por eso las letras angostas («i», «l») de la letra pequeña salen como `tiny_font`. El error ya existía antes de
   la revisión (lo comprobé sin mis cambios) y va hacia el lado seguro: la factura escala por R2.
6. `custodio/extraction/structure.py:96`: si el documento trae `</document>`, cierra antes de tiempo el delimitador
   del turno del usuario. El riesgo es bajo, porque el modelo no decide y las inyecciones típicas generan el hallazgo
   `instruction`. Se arregla con un delimitador aleatorio o escapando la etiqueta.
7. `custodio/extraction/vision.py:24`: el prompt pide transcribir también el texto «faint, small or partially
   covered». En imágenes, entonces, el texto tenue entra al texto fuente y puede respaldar citas. Sirve para que el
   patrón de instrucciones lo vea, pero no hay detección por píxeles en imágenes (el autor lo declaró).
8. `custodio/extraction/amounts.py:17`: el espacio normal no agrupa miles. En «Total 4 200 000», `amounts_in` ve
   `4`, `200` y `0`, así que un valor `200.00` se daría por verificado contra esa cita. Haría falta que el modelo
   devolviera ese valor. El caso común (`4200000.00`) da `verified=false`, que es el lado seguro.
9. `custodio/extraction/verify.py:141`: un monto se verifica si **algún** número de la cita parsea igual, y eso
   incluye un subtotal citado junto al total. Es inherente al diseño de §6.
10. `custodio/extraction/pdf.py:120` y `:129`: si pypdfium2 no puede dibujar un PDF que pdfminer sí leyó, el error
    `PdfiumError` sale sin tipo propio. Para atraparlo hay que importar `pypdfium2`, una dependencia transitiva de
    pdfplumber sin tipos. Eso exige tocar `pyproject.toml`, que es del coordinador. Lo dejo propuesto.
11. Propiedad de archivos: el carril tocó `apps/api/pyproject.toml` y `apps/api/uv.lock` (quitó `google-genai`). Está
    fuera de sus archivos, pero lo pide DESIGN §13 y está declarado en **Contratos** del informe. Quedan restos de
    Gemini para el coordinador y L4: el marcador `live` de `apps/api/pyproject.toml:49` dice «Claude or Gemini», y
    `Settings.gemini_model` y `gemini_configured` siguen en `config.py`, igual que `gemini` en `/health`.
12. `custodio/extraction/__init__.py:52`: `extract_text` no limita el largo del texto. Le toca a L4 poner el tope en la
    entrada HTTP, igual que los 4 MB de documentos.
13. El diff pasa las ~800 líneas que sugiere el diseño. El autor lo declaró.

## Lo que revisé y quedó bien

- **TDD**: corrí `pytest tests/extraction` en cada commit del autor. Cada commit «add failing tests» está rojo (2 o 4
  errores de colección, o `2 failed`), y el commit de implementación que le sigue está verde: `b46d1a2`→`6214766`
  (99 passed), `c35b3e3`→`bbb3c8f` (132), `ab4444b`→`8556a48` (163), `8ebb12a`→`f30e77f` (173), `939e006`→`ad4af46`
  (177). Mis cuatro arreglos siguen el mismo orden. Cada test rojo lo comprobé contra el código sin arreglar.
- **Invariantes de §3**: hasta donde lo puede verificar L2, ningún texto del documento decide nada. Sólo `verify.py`
  pone `verified`, el prompt de sistema es estable y trata el documento como dato, y el texto dirigido al agente
  genera un hallazgo `instruction`, sea visible u oculto. Los escaneos nunca salen como bloque `document`, así que la
  capa de texto oculta no llega al modelo. No hay secretos en el código ni en los logs.
- **Integración con L1** (en la copia rebaseada): los 36 `demo_specs()` se renderizan (13 PDF, 18 email, 3 WhatsApp,
  2 foto). En los 13 PDF, `read_pdf` da hallazgos exactamente donde el spec trae `hidden_text`, y cero en los demás.
- **Contratos**: no hay cambios en `contracts.py`, `llm.py` ni `config.py`. El resto de los archivos tocados son del
  carril.
- **Autoría e idioma**: los 13 commits del autor y los míos van a nombre de Juan David Leon, sin trailers, sin firma
  y sin menciones a herramientas. El código está en inglés y el texto de producto en español. El entorno firma los
  commits con una llave propia por defecto. Igual que el autor, desactivé `commit.gpgsign` en el `git config` local.

## Qué arreglé (commits sobre `lane/L2-extraction`)

| Commit | Qué |
|---|---|
| `2f6b616` | ordena imports (compuerta) |
| `c384e5c` | tests rojos: cuentas, identificadores y nombres truncados |
| `4f29f75` | `verify.py`: códigos completos y palabras completas |
| `b044354` | tests rojos: modo de render 3, CropBox, blanco sobre imagen, glifos aplastados; y texto legible sobre imágenes |
| `e65cadb` | `pdf.py`: verificación por trazo y caja de recorte |
| `bfec514` | test rojo: PDF de más de 20 páginas |
| `8b3e0c9` | `pdf.py`: `MAX_PDF_PAGES` |
| `4b238cf` | `docs/lanes/reports/L2.md`: conteos y cobertura actualizados para que el cuerpo del PR no quede desactualizado |

## Lo que NO pude verificar

- **Tests live: NO MEDIDO.** En el entorno sólo existe `ANTHROPIC_BASE_URL`; no hay `ANTHROPIC_API_KEY`. No hay cifras
  de exactitud por campo ni de transcripción con visión. Tampoco pude confirmar que el esquema `Transcription` lo
  acepte la API real.
- PDFs reales de terceros, incluidos escaneos con capa OCR invisible. Con el arreglo del punto 3, esa capa genera un
  hallazgo `invisible_color` y la factura escala. Es el lado seguro, pero no lo medí con documentos reales.
- El camino de `PdfiumError` (observación 10): no tengo un PDF que pdfminer lea y pdfium no.
- El tiempo con PDFs grandes de verdad. Sólo medí unos 40 ms por página en los PDF de prueba; el tope de 20 páginas
  acota el peor caso.
- Texto invisible dibujado exactamente encima de texto visible. Su caja sí cambia de píxeles, así que la
  verificación por trazo no lo ve. Lo dejé declarado en `L2.md`.
