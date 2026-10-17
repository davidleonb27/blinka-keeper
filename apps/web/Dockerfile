# Custodio web: Next.js built once and served with `next start` on port 3000, as a non-root user.
# Next.js fixes its rewrites at build time, so API_INTERNAL_URL (where the browser's /api/v1 calls are forwarded)
# is a build argument as well as a runtime variable. Build from the repository root with `docker compose build web`.
# Behind a proxy with its own certificate authority, pass it as the optional build secret `extra_ca`.
FROM node:24-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    npm ci --no-audit --no-fund --loglevel=error
COPY . .
ARG API_INTERNAL_URL=http://api:8000
ENV API_INTERNAL_URL=${API_INTERNAL_URL}
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    npm run build && npm prune --omit=dev --no-audit --no-fund --loglevel=error

FROM node:24-slim
WORKDIR /app
ARG API_INTERNAL_URL=http://api:8000
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    API_INTERNAL_URL=${API_INTERNAL_URL} \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/package.json /app/next.config.ts ./
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/.next ./.next
USER node
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000/').then(r => process.exit(r.ok ? 0 : 1), () => process.exit(1))"]
CMD ["npx", "--no-install", "next", "start", "--port", "3000"]
