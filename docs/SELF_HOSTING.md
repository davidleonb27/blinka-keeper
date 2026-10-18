# Autoalojar Custodio

Custodio es código abierto (licencia MIT). Puedes usar la demo pública o correrlo en tu propia infraestructura. Todas
las variables son opcionales: sin ninguna arranca con la empresa demo, el riel de pago simulado y sin modelo. La lista
completa, con qué hace cada una, está en [`.env.example`](../.env.example).

| Dónde | Qué levanta | Esfuerzo |
|---|---|---|
| [Tu máquina o un VPS con Docker](#docker-compose-un-comando) | Postgres 16, API y web | un comando |
| [Vercel + Neon](#vercel--neon) | web y API como servicios de un proyecto, Postgres en Neon | un botón |
| [Railway](#railway) | Postgres, API y web desde los Dockerfiles | unos clics |
| [Fly.io](#flyio) | API y web como dos apps, Postgres administrado | unos comandos |

## Docker Compose (un comando)

Requisitos: Docker con Compose v2.

```bash
git clone https://github.com/davidleonb27/blinka-keeper.git
cd custodio-blinka
cp .env.example .env        # opcional
docker compose up --build
```

- Web: <http://localhost:3000> · API: <http://localhost:8000/api/v1> · documentación de la API:
  <http://localhost:8000/api/v1/docs>.
- La API espera a que Postgres esté sano, aplica las migraciones (`python -m custodio.db.migrate`, con un candado de
  Postgres para que varias réplicas puedan arrancar a la vez) y sólo entonces recibe tráfico.
- Los datos quedan en el volumen `custodio-data`. `docker compose down` los conserva; `docker compose down -v` los
  borra.

Comprueba que todo responde:

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok","version":"0.1.0","anthropic":false}

# Crea un espacio con la empresa demo y pide una decisión al firewall
KEY=$(curl -s -X POST http://localhost:3000/api/v1/workspaces -H 'Content-Type: application/json' -d '{}' \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["api_key"])')
curl -s -X POST http://localhost:8000/api/v1/firewall/intents \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"agent": "mi-agente", "beneficiary_name": "Pulso Software Inc.", "bank_name": "Mercury",
       "account_number": "2214-1180", "amount": 840, "currency": "USD", "invoice_number": "PS-90001"}'
```

### Sin `ANTHROPIC_API_KEY`

Siguen funcionando el motor de 12 reglas, el auditor independiente, el registro encadenado, el firewall por API y MCP,
y la lectura de texto y de PDF con texto (por etiquetas `Campo: valor`, leídas por código y verificadas como si las
hubiera leído el modelo; lo que ninguna etiqueta dice queda sin leer y R1 lo manda a una persona). Lo que necesita al
modelo (imágenes y PDF escaneados, reglas escritas en español, perfil de la empresa, importar proveedores y el red team)
responde `503` con el código `model_not_configured` y el mensaje «requiere ANTHROPIC_API_KEY», sin decidir nada.

### En un VPS

1. Instala Docker y clona el repositorio como arriba.
2. En `.env`, cambia `POSTGRES_PASSWORD` y pon `CUSTODIO_PUBLIC_BASE_URL=https://tu-dominio`.
3. `docker compose up -d --build`.
4. Pon HTTPS delante del puerto 3000, por ejemplo con [Caddy](https://caddyserver.com/):

   ```
   tu-dominio {
       reverse_proxy localhost:3000
   }
   ```

   La web reenvía `/api/v1` a la API por la red interna del compose, así que basta con publicar el 3000. Cierra el
   8000 en el firewall del servidor si no quieres exponer la API directamente.
5. Para actualizar: `git pull && docker compose up -d --build`. Las migraciones corren solas.

### Detrás de un proxy con certificado propio

Si tu red intercepta HTTPS con una autoridad de certificación propia, pásala a la construcción como secreto opcional
`extra_ca` (ambos Dockerfiles lo usan si existe y lo ignoran si no):

```yaml
# compose.override.yml
services:
  api:
    build: { secrets: [extra_ca] }
  web:
    build: { secrets: [extra_ca] }
secrets:
  extra_ca:
    file: /ruta/a/tu-ca.crt
```

## Vercel + Neon

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fdavidleonb27%2Fcustodio-blinka&project-name=custodio&repository-name=custodio&stores=%5B%7B%22type%22%3A%22integration%22%2C%22integrationSlug%22%3A%22neon%22%2C%22productSlug%22%3A%22neon%22%2C%22protocol%22%3A%22storage%22%7D%5D)

El botón clona el repositorio en tu cuenta, crea la base de datos en Neon (integración del Marketplace de Vercel, que
inyecta `DATABASE_URL`) y despliega. [`vercel.json`](../vercel.json) define dos servicios en un proyecto: `web`
(Next.js) y `api` (FastAPI), y enruta `/api/v1/*` a la API. Las migraciones corren en la primera petición de cada
instancia. Después agrega en *Settings → Environment Variables* lo que quieras de `.env.example` (por ejemplo
`ANTHROPIC_API_KEY` y `CUSTODIO_PUBLIC_BASE_URL`) y vuelve a desplegar.

## Railway

1. Crea un proyecto y agrega una base de datos **PostgreSQL**.
2. Agrega un servicio desde este repositorio con *Root Directory* `apps/api` (Railway detecta el Dockerfile). Variables:
   `DATABASE_URL=${{Postgres.DATABASE_URL}}` y las que quieras de `.env.example`.
3. Agrega otro servicio desde el mismo repositorio con *Root Directory* `apps/web`. Variable:
   `API_INTERNAL_URL=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:8000` (Railway la pasa también como argumento de
   construcción, que es cuando Next.js la fija). Genera un dominio público para este servicio.

## Fly.io

```bash
# API
fly launch --no-deploy --name custodio-api --dockerfile apps/api/Dockerfile --internal-port 8000
fly postgres create --name custodio-db
fly postgres attach custodio-db --app custodio-api          # define DATABASE_URL
fly deploy --app custodio-api --dockerfile apps/api/Dockerfile apps/api

# Web
fly launch --no-deploy --name custodio-web --dockerfile apps/web/Dockerfile --internal-port 3000
fly deploy --app custodio-web --dockerfile apps/web/Dockerfile \
  --build-arg API_INTERNAL_URL=https://custodio-api.fly.dev apps/web
fly secrets set --app custodio-web API_INTERNAL_URL=https://custodio-api.fly.dev
```

La web llama a la API por su URL pública de Fly; pon `CUSTODIO_PUBLIC_BASE_URL=https://custodio-web.fly.dev` en la
API con `fly secrets set`.

## Qué se probó

`docker compose up --build` se probó de punta a punta (construcción, migraciones sobre Postgres 16, salud, web,
firewall y persistencia tras reiniciar). Los pasos de Vercel + Neon, Railway y Fly.io siguen la documentación de cada
plataforma pero no se ejecutaron desde este repositorio: si algo no coincide, abre un issue.
