# Política de seguridad

Custodio decide pagos. Tomamos en serio cualquier forma de romperlo y agradecemos a quien la reporte con cuidado.

*English: report vulnerabilities privately through GitHub Security Advisories (link below). Do not open a public
issue. Any path that leads Custodio to pay something it should not is in scope.*

## Cómo reportar

**No abras un issue público ni un PR.** Repórtalo en privado con GitHub Security Advisories:

1. Entra a <https://github.com/davidleonb27/blinka-keeper/security/advisories/new>.
2. Describe qué hiciste, qué esperabas y qué pasó. Incluye los pasos mínimos para reproducirlo (la factura, el texto o
   la intención de pago exactos) y la versión o el commit.
3. Si lo probaste en la demo pública, di la hora aproximada y el ID de la decisión o del intento.

Respondemos el recibo en un plazo de 3 días hábiles y te contamos el plan de corrección. Te damos crédito en el aviso
publicado, salvo que prefieras no aparecer.

## Alcance

Está dentro del alcance, en particular:

- **Cualquier camino que pague algo indebido**: que una factura o intención de pago termine en `paid_auto` o
  `paid_human` cuando una regla de retención falla, cuando el pago deja el saldo bajo la reserva, cuando la cuenta no
  es la registrada, cuando ya se pagó (duplicado) o cuando el auditor independiente no lo confirma. Da igual la entrada:
  panel, PDF, imagen, texto, firewall por API, MCP, reto público, red team o un riel de pago.
- Que un texto del documento (visible u oculto) cambie una regla, apruebe algo o evite una persona.
- Alterar el registro encadenado sin que `GET /api/v1/ledger/verify` lo detecte.
- Leer o escribir en el espacio de trabajo de otra persona, o usar una API key ajena.
- Exponer secretos (`ANTHROPIC_API_KEY`, `STRIPE_SECRET_KEY`, `DATABASE_URL`) en respuestas, logs o errores.
- Saltarse los límites de gasto en modelos o de tamaño de archivos de forma que afecte a otros.

Fuera del alcance: ataques de denegación de servicio por volumen, ingeniería social contra mantenedores, fallas de
servicios de terceros (Vercel, Neon, Anthropic, Stripe) que no dependen de Custodio y reportes sin un caso
reproducible.

## Reto público

«Róbale a Custodio» invita a intentar que pague algo indebido en la demo. Intentarlo ahí es bienvenido. Si lo logras,
repórtalo por el canal privado de arriba antes de publicarlo.

## Versiones soportadas

Sólo la rama `main` y la demo desplegada desde ella reciben correcciones de seguridad.
