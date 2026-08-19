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

## Start with the I-ONE platform

Keep a stable `current` symlink pointing at the active release, then install the
included user service. Dify remains operationally independent from Bench, while
both stacks start automatically with the server:

```bash
ln -sfn /path/to/active/dify-release ~/services/ione-dify/current
install -Dm644 docker/systemd/ione-dify.service \
  ~/.config/systemd/user/ione-dify.service
systemctl --user daemon-reload
systemctl --user enable --now ione-dify.service
```

The Compose services use restart policies for process-level recovery. The
systemd unit provides a stable lifecycle entry point for startup, reload and
controlled shutdown; Dify is intentionally not placed inside a Bench container.
