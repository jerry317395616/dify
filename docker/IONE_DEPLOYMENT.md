# I-ONE deployment

This deployment keeps Dify independent from Frappe while allowing trusted Dify
services to reach the private Qwen network. Frappe users access Dify through the
`ione_agent` server-side integration; the Dify console remains available to AI
administrators.

## Build from this fork

Run these commands from the repository root and replace `local` with an immutable
commit tag in production:

```bash
docker build -f api/Dockerfile -t ione/dify-api:local .
docker build -f web/Dockerfile -t ione/dify-web:local .
docker build -f dify-agent/Dockerfile -t ione/dify-agent-backend:local .
```

## Configure

From `docker/`:

```bash
cp .env.example .env
cp envs/ione.env.example ione.env
```

Set production secrets only in `.env`. Set the public Dify URL and immutable
image tags in `ione.env`. The external network configured by
`IONE_QWEN_NETWORK` must already exist; do not publish the Qwen container port.

## Start

```bash
docker compose \
  --env-file .env \
  --env-file ione.env \
  -f docker-compose.yaml \
  -f docker-compose.ione.yaml \
  up -d
```

Do not expose Dify app keys in Frappe JavaScript. Store them in Frappe site
configuration and call Dify only through `ione_agent` server methods.
